from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DATA_ROOT = Path.home() / ".codex-usage-guard-data"
TASKS_ROOT = DATA_ROOT / "tasks"


def task_path(task_id: str) -> Path:
    return TASKS_ROOT / f"{task_id}.json"


def load_task(task_id: str) -> dict[str, Any] | None:
    path = task_path(task_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def phase_from_state(state: dict[str, Any] | None) -> str:
    if not state:
        return "analyze"
    visual = state.get("visual") or {}
    phase = str(visual.get("phase") or "").lower()
    if phase in {"analyze", "judge", "route", "execute", "verify", "complete", "failed"}:
        return phase
    execution = state.get("execution") or {}
    status = execution.get("status")
    if status in {"verified", "parent-match"}:
        return "complete"
    if status in {"failed", "model-mismatch", "reasoning-mismatch", "budget-blocked", "unverified", "unverified-no-thread"}:
        return "failed"
    return "analyze"


def activity_from_state(state: dict[str, Any] | None) -> str:
    if not state:
        return "idle"
    visual = state.get("visual") or {}
    return str(visual.get("activity") or "idle")


def selected_model(state: dict[str, Any] | None) -> str:
    if not state:
        return ""
    execution = state.get("execution") or {}
    plan = state.get("plan") or {}
    return str(
        execution.get("effective_model")
        or execution.get("requested_model")
        or plan.get("preferred_model")
        or ""
    )


def model_palette(model: str) -> tuple[str, str, str]:
    model = model.lower()
    if "luna" in model:
        return ("#78a9ff", "#4f7edb", "#dce9ff")
    if "terra" in model:
        return ("#4fd1a1", "#2a9d77", "#d8fff1")
    return ("#f6c85f", "#c99527", "#fff1bf")


def _safe_tk() -> tuple[Any, Any] | tuple[None, None]:
    try:
        import tkinter as tk
        from tkinter import ttk
        return tk, ttk
    except Exception:
        return None, None


def can_open_window() -> bool:
    if os.name == "nt":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def spawn_visualizer(task_id: str, *, install_root: Path | None = None) -> bool:
    if os.environ.get("CODEX_USAGE_GUARD_DISABLE_VISUAL") == "1":
        return False
    if not can_open_window():
        return False
    install_root = install_root or Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "guard.visualizer", "--task-id", task_id]
    kwargs: dict[str, Any] = {
        "cwd": str(install_root),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": os.name != "nt",
    }
    if os.name == "nt":
        creationflags = 0
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(command, **kwargs)
        return True
    except OSError:
        return False


class PixelFactory:
    WIDTH = 560
    HEIGHT = 330

    def __init__(self, task_id: str, *, topmost: bool = True, auto_close_seconds: float = 3.5) -> None:
        tk, _ = _safe_tk()
        if tk is None:
            raise RuntimeError("tkinter is unavailable")
        self.tk = tk
        self.task_id = task_id
        self.auto_close_seconds = auto_close_seconds
        self.root = tk.Tk()
        self.root.title("Codex Usage Guard")
        self.root.configure(bg="#111722")
        self.root.resizable(False, False)
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        try:
            self.root.attributes("-topmost", bool(topmost))
        except Exception:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#111722",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.frame = 0
        self.last_state: dict[str, Any] | None = None
        self.terminal_since: float | None = None
        self.random = random.Random(17)
        self.confetti = [
            (
                self.random.randint(120, 520),
                self.random.randint(-80, 20),
                self.random.choice(("#69d2ff", "#f7d267", "#80e3a5", "#ff8db1", "#ffffff")),
                self.random.randint(1, 4),
            )
            for _ in range(46)
        ]

        self._position_window()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _position_window(self) -> None:
        self.root.update_idletasks()
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = max(10, screen_w - self.WIDTH - 28)
            y = max(10, screen_h - self.HEIGHT - 72)
            self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        except Exception:
            pass

    def _rect(self, x1: int, y1: int, x2: int, y2: int, fill: str, outline: str = "", width: int = 1) -> None:
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)

    def _floor(self) -> None:
        self._rect(0, 0, self.WIDTH, self.HEIGHT, "#192332")
        tile = 32
        for x in range(0, self.WIDTH, tile):
            self.canvas.create_line(x, 0, x, self.HEIGHT, fill="#243245")
        for y in range(0, self.HEIGHT, tile):
            self.canvas.create_line(0, y, self.WIDTH, y, fill="#243245")
        for x in range(0, self.WIDTH, tile * 2):
            for y in range(0, self.HEIGHT, tile * 2):
                self._rect(x + 2, y + 2, x + tile - 2, y + tile - 2, "#1c2838")

    def _pipe(self, points: list[int]) -> None:
        self.canvas.create_line(*points, fill="#0c1119", width=14, jointstyle="miter")
        self.canvas.create_line(*points, fill="#344257", width=8, jointstyle="miter")
        for i in range(0, len(points) - 2, 2):
            x, y = points[i], points[i + 1]
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#53657d", outline="#0c1119")

    def _machine(self, x: int, y: int, accent: str, active: bool = False) -> None:
        glow = accent if active else "#385064"
        self._rect(x, y, x + 82, y + 66, "#2c394a", "#0c1119", 3)
        self._rect(x + 8, y + 8, x + 74, y + 28, "#13202d", "#0c1119", 2)
        for i in range(4):
            h = 5 + ((self.frame + i * 3) % 9 if active else 2)
            self._rect(x + 16 + i * 12, y + 23 - h, x + 22 + i * 12, y + 23, glow)
        self._rect(x + 12, y + 38, x + 25, y + 51, "#111820", "#0c1119", 2)
        self._rect(x + 30, y + 39, x + 65, y + 48, "#45566b", "#0c1119", 2)
        self._rect(x + 30, y + 53, x + 54, y + 58, accent if active else "#6a7887")

    def _scanner(self, x: int, y: int, accent: str, active: bool = False) -> None:
        self._rect(x, y, x + 66, y + 60, "#253548", "#0b1119", 3)
        self._rect(x + 8, y + 8, x + 58, y + 42, "#0f1822", "#0b1119", 2)
        pulse = 3 + int(3 * (1 + math.sin(self.frame / 4)))
        self.canvas.create_oval(
            x + 24 - pulse,
            y + 19 - pulse,
            x + 42 + pulse,
            y + 37 + pulse,
            outline=accent if active else "#50627a",
            width=3,
        )
        self._rect(x + 16, y + 49, x + 50, y + 54, accent if active else "#53657a")

    def _worker(self, x: int, y: int, *, facing: int = 1, carry: bool = False, accent: str = "#ff9d42") -> None:
        bob = int(2 * math.sin(self.frame / 3 + x))
        y += bob
        skin = "#f3bf83"
        shirt = "#3c88c8"
        pants = "#234e78"
        self._rect(x + 6, y, x + 21, y + 7, accent, "#10151d", 2)
        self._rect(x + 4, y + 7, x + 23, y + 14, skin, "#10151d", 2)
        self._rect(x + 7, y + 14, x + 20, y + 30, shirt, "#10151d", 2)
        arm_y = y + 17
        if carry:
            self._rect(x + (20 if facing > 0 else -2), arm_y, x + (28 if facing > 0 else 6), arm_y + 6, skin, "#10151d", 1)
        else:
            self._rect(x + 1, arm_y, x + 7, arm_y + 9, skin, "#10151d", 1)
            self._rect(x + 20, arm_y, x + 26, arm_y + 9, skin, "#10151d", 1)
        self._rect(x + 6, y + 30, x + 12, y + 41, pants, "#10151d", 1)
        self._rect(x + 15, y + 30, x + 21, y + 41, pants, "#10151d", 1)

    def _cube(self, x: float, y: float, accent: str, *, glow: bool = True) -> None:
        size = 16
        if glow:
            radius = 22 + int(2 * math.sin(self.frame / 3))
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="",
                outline=accent,
                width=1,
            )
        self._rect(int(x - size), int(y - size), int(x + size), int(y + size), "#d9f0ff", "#0c1119", 2)
        self.canvas.create_polygon(
            x - size, y - size,
            x, y - size - 7,
            x + size, y - size,
            x, y - size + 7,
            fill=accent,
            outline="#0c1119",
        )
        self._rect(int(x - 6), int(y - 5), int(x + 6), int(y + 7), accent, "#0c1119", 1)

    def _conveyor(self, x1: int, y1: int, x2: int, y2: int, active: bool) -> None:
        self._rect(x1, y1, x2, y2, "#121920", "#0b1119", 3)
        step = 22
        offset = (self.frame * 3) % step if active else 0
        for x in range(x1 - step, x2 + step, step):
            px = x + offset
            self.canvas.create_line(px, y1 + 4, px + 9, y2 - 4, fill="#405269", width=4)

    def _route_gate(self, x: int, y: int, accent: str, active: bool) -> None:
        self._rect(x, y, x + 46, y + 76, "#202c3b", "#0b1119", 3)
        self._rect(x + 9, y + 10, x + 37, y + 28, "#0f1822", "#0b1119", 2)
        light = accent if active else "#47596d"
        for i in range(3):
            self.canvas.create_oval(x + 12 + i * 9, y + 15, x + 18 + i * 9, y + 21, fill=light, outline="")
        self._rect(x + 18, y + 34, x + 28, y + 67, light if active else "#38475b")

    def _verify_gate(self, x: int, y: int, active: bool, success: bool) -> None:
        color = "#63e68f" if success else ("#76b9ff" if active else "#46566b")
        self._rect(x, y, x + 18, y + 82, "#263647", "#0b1119", 3)
        self._rect(x + 52, y, x + 70, y + 82, "#263647", "#0b1119", 3)
        self.canvas.create_line(x + 18, y + 12, x + 52, y + 12, fill=color, width=4)
        if active or success:
            scan_y = y + 22 + ((self.frame * 4) % 44)
            self.canvas.create_line(x + 20, scan_y, x + 50, scan_y, fill=color, width=3)

    def _status_lights(self, model: str, status: str) -> None:
        primary, _, _ = model_palette(model)
        positions = [(34, 24), (58, 24), (82, 24)]
        active_idx = 0 if "luna" in model.lower() else 1 if "terra" in model.lower() else 2
        for i, (x, y) in enumerate(positions):
            fill = primary if i == active_idx else "#334459"
            self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7, fill=fill, outline="#0b1119", width=2)
        status_color = "#63e68f" if status in {"complete", "verified", "parent-match"} else "#ff6e7a" if status == "failed" else "#f0c96a"
        self._rect(104, 16, 122, 32, status_color, "#0b1119", 2)

    def _task_progress(self, phase: str, accent: str) -> tuple[float, float]:
        # No fake percentage: the cube occupies the real phase's station and loops locally while work continues.
        if phase == "analyze":
            return 105 + 8 * math.sin(self.frame / 5), 126
        if phase == "judge":
            return 182 + 6 * math.sin(self.frame / 4), 126
        if phase == "route":
            return 260 + 5 * math.sin(self.frame / 3), 150
        if phase == "execute":
            return 350 + ((self.frame * 2) % 72), 190
        if phase in {"verify", "complete", "failed"}:
            return 482, 176
        return 110, 126

    def _activity_particles(self, phase: str, activity: str, accent: str) -> None:
        if phase == "execute":
            for i in range(8):
                x = 335 + (i * 19 + self.frame * 5) % 120
                y = 112 + ((i * 13 + self.frame * 3) % 54)
                self._rect(x, y, x + 3, y + 3, accent)
        if activity in {"command_execution", "mcp_tool_call", "file_change"}:
            for i in range(7):
                angle = (self.frame + i * 5) * 0.45
                x = 392 + int(math.cos(angle) * (16 + i))
                y = 96 + int(math.sin(angle) * (10 + i // 2))
                self._rect(x, y, x + 2, y + 2, "#ffd46a")

    def _complete_overlay(self, success: bool) -> None:
        color = "#56d98a" if success else "#ff6f7a"
        self._rect(154, 98, 406, 218, "#101820", "#0b1119", 4)
        self._rect(165, 109, 395, 207, "#1c2a38", color, 3)
        if success:
            # trophy silhouette
            self._rect(260, 126, 300, 165, "#f1c64d", "#0b1119", 3)
            self._rect(272, 165, 288, 180, "#d49f28", "#0b1119", 2)
            self._rect(258, 180, 302, 189, "#f1c64d", "#0b1119", 2)
            self.canvas.create_arc(244, 128, 266, 154, start=90, extent=180, style="arc", outline="#f1c64d", width=5)
            self.canvas.create_arc(294, 128, 316, 154, start=-90, extent=180, style="arc", outline="#f1c64d", width=5)
            self.canvas.create_line(269, 144, 279, 154, 294, 134, fill="#ffffff", width=5)
        else:
            self.canvas.create_line(256, 132, 304, 180, fill=color, width=8)
            self.canvas.create_line(304, 132, 256, 180, fill=color, width=8)

    def _confetti(self) -> None:
        for i, (x, y0, color, speed) in enumerate(self.confetti):
            y = (y0 + self.frame * speed * 2) % (self.HEIGHT + 80) - 30
            drift = int(8 * math.sin((self.frame + i) / 4))
            self._rect(x + drift, y, x + drift + 4, y + 7, color)

    def draw(self, state: dict[str, Any] | None) -> None:
        self.canvas.delete("all")
        self._floor()
        phase = phase_from_state(state)
        activity = activity_from_state(state)
        model = selected_model(state)
        accent, accent_dark, accent_soft = model_palette(model)
        status = "failed" if phase == "failed" else "complete" if phase == "complete" else str((state or {}).get("execution", {}).get("status") or "active")

        self._pipe([0, 68, 52, 68, 52, 110, 142, 110])
        self._pipe([560, 62, 500, 62, 500, 106, 448, 106])

        # static environment
        self._machine(20, 232, "#5f738a", False)
        self._machine(458, 228, accent, phase in {"execute", "verify"})
        self._scanner(78, 82, accent, phase == "analyze")
        self._route_gate(232, 82, accent, phase == "route")
        self._machine(338, 74, accent, phase == "execute")
        self._verify_gate(462, 128, phase == "verify", phase == "complete")
        self._conveyor(128, 166, 472, 208, phase in {"route", "execute", "verify"})

        # workers move around phase-relevant stations
        positions = {
            "analyze": ((105, 126), (154, 226), (398, 230)),
            "judge": ((160, 126), (210, 222), (400, 230)),
            "route": ((236, 128), (285, 220), (405, 228)),
            "execute": ((342, 124), (410, 150), (430, 230)),
            "verify": ((460, 126), (430, 220), (500, 222)),
            "complete": ((245, 232), (314, 230), (425, 230)),
            "failed": ((232, 230), (318, 230), (424, 230)),
        }
        for i, (x, y) in enumerate(positions.get(phase, positions["analyze"])):
            carry = phase in {"route", "execute"} and i == 1
            self._worker(x, y, facing=1 if i != 2 else -1, carry=carry, accent="#f29b43" if i != 2 else "#56a7e8")

        cx, cy = self._task_progress(phase, accent)
        if phase not in {"complete", "failed"}:
            self._cube(cx, cy, accent)

        self._activity_particles(phase, activity, accent)
        self._status_lights(model, status)

        # Minimal visual gauges: five stage blocks, no prose log.
        stage_order = ["analyze", "judge", "route", "execute", "verify"]
        effective_phase = "verify" if phase == "complete" else phase
        active_index = stage_order.index(effective_phase) if effective_phase in stage_order else 0
        for i in range(5):
            x = 176 + i * 42
            fill = accent if i <= active_index else "#334459"
            if i == 1 and not bool((state or {}).get("judgement")):
                fill = "#263445"
            self._rect(x, 24, x + 26, 32, fill, "#0b1119", 1)

        if phase == "complete":
            self._complete_overlay(True)
            self._confetti()
        elif phase == "failed":
            self._complete_overlay(False)

    def tick(self) -> None:
        state = load_task(self.task_id)
        if state is not None:
            self.last_state = state
        phase = phase_from_state(self.last_state)
        self.draw(self.last_state)
        self.frame += 1

        if phase in {"complete", "failed"}:
            if self.terminal_since is None:
                self.terminal_since = time.monotonic()
            elif time.monotonic() - self.terminal_since >= self.auto_close_seconds:
                self.root.destroy()
                return
        else:
            self.terminal_since = None

        self.root.after(90, self.tick)

    def run(self) -> None:
        self.root.after(0, self.tick)
        self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pixel-art live task visualizer for Codex Usage Guard")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--no-topmost", action="store_true")
    parser.add_argument("--auto-close-seconds", type=float, default=3.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not can_open_window():
        return 0
    try:
        app = PixelFactory(
            args.task_id,
            topmost=not args.no_topmost,
            auto_close_seconds=max(0.0, args.auto_close_seconds),
        )
    except Exception:
        return 0
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
