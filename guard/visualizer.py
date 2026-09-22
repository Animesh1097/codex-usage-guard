from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any


DATA_ROOT = Path.home() / ".codex-usage-guard-data"
TASKS_ROOT = DATA_ROOT / "tasks"
VISUALIZER_LOG = DATA_ROOT / "visualizer.log"


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
    aliases = {
        "route": "plan",
        "execute": "work",
        "judge": "plan",
    }
    phase = aliases.get(phase, phase)
    if phase in {"analyze", "plan", "work", "verify", "complete", "failed"}:
        return phase

    status = str(state.get("status") or "")
    if status == "completed":
        return "complete"
    if status in {"blocked", "abandoned", "failed"}:
        return "failed"

    execution = state.get("execution") or {}
    exec_status = execution.get("status")
    if exec_status in {"failed", "model-mismatch", "reasoning-mismatch", "budget-blocked"}:
        return "failed"
    return "analyze"


def activity_from_state(state: dict[str, Any] | None) -> str:
    if not state:
        return "idle"
    visual = state.get("visual") or {}
    return str(visual.get("activity") or "idle")


def task_kind_from_state(state: dict[str, Any] | None) -> str:
    if not state:
        return "general"
    plan = state.get("plan") or {}
    return str(plan.get("task_kind") or "general")


def task_palette(kind: str) -> tuple[str, str, str]:
    kind = kind.lower()
    if kind == "ui":
        return ("#c882ff", "#7844b8", "#f0dcff")
    if kind == "debugging":
        return ("#ffad5c", "#b76b2e", "#ffe4c7")
    if kind == "database":
        return ("#53d7c2", "#278f82", "#d5fff8")
    if kind == "security":
        return ("#ff6f78", "#b33f47", "#ffd8db")
    if kind == "deployment":
        return ("#ffd166", "#b38b2f", "#fff2bd")
    if kind == "docs":
        return ("#78a9ff", "#4674c3", "#dce9ff")
    return ("#65d6a5", "#328e6c", "#d9fff0")


def _safe_tk() -> tuple[Any, Any] | tuple[None, None]:
    try:
        import tkinter as tk
        from tkinter import ttk
        return tk, ttk
    except Exception:
        return None, None


def visualizer_enabled() -> bool:
    if os.environ.get("CODEX_USAGE_GUARD_DISABLE_VISUAL") == "1":
        return False
    return os.environ.get("CODEX_USAGE_GUARD_VISUAL") == "1"


def desktop_available() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def can_open_window() -> bool:
    tk, _ = _safe_tk()
    return tk is not None and desktop_available()


def visualizer_command(task_id: str, *, install_root: Path | None = None) -> list[str] | None:
    install_root = install_root or Path(__file__).resolve().parents[1]
    override = os.environ.get("CODEX_USAGE_GUARD_VISUALIZER")
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return [str(path), "--task-id", task_id]

    names = ["usage-guard-visualizer.exe", "usage-guard-visualizer"] if os.name == "nt" else ["usage-guard-visualizer"]
    for name in names:
        path = install_root / "bin" / name
        if path.is_file():
            return [str(path), "--task-id", task_id]

    if can_open_window():
        return [sys.executable, "-m", "guard.visualizer", "--task-id", task_id]
    return None


def spawn_visualizer(task_id: str, *, install_root: Path | None = None) -> bool:
    if not visualizer_enabled():
        return False
    if not desktop_available():
        return False

    install_root = install_root or Path(__file__).resolve().parents[1]
    command = visualizer_command(task_id, install_root=install_root)
    if command is None:
        return False
    kwargs: dict[str, Any] = {
        "cwd": str(install_root),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": os.name != "nt",
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        )
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(command, **kwargs)
        return True
    except OSError:
        return False


class PixelFactory:
    WIDTH = 640
    HEIGHT = 390
    PHASES = ("analyze", "plan", "work", "verify")

    def __init__(self, task_id: str, *, topmost: bool = True, auto_close_seconds: float = 3.5) -> None:
        tk, _ = _safe_tk()
        if tk is None:
            raise RuntimeError("tkinter is unavailable")
        self.tk = tk
        self.task_id = task_id
        self.auto_close_seconds = auto_close_seconds
        self.root = tk.Tk()
        self.root.title("Codex Usage Guard")
        self.root.configure(bg="#0d1420")
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
            bg="#0d1420",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.frame = 0
        self.last_state: dict[str, Any] | None = None
        self.terminal_since: float | None = None
        self.random = random.Random(23)
        self.confetti = [
            (
                self.random.randint(70, self.WIDTH - 70),
                self.random.randint(-110, 30),
                self.random.choice(("#69d2ff", "#ffd166", "#80e3a5", "#ff8db1", "#ffffff")),
                self.random.randint(1, 4),
            )
            for _ in range(58)
        ]

        self._position_window()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _position_window(self) -> None:
        self.root.update_idletasks()
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = max(12, screen_w - self.WIDTH - 28)
            y = max(12, screen_h - self.HEIGHT - 72)
            self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        except Exception:
            pass

    def _rect(self, x1: int, y1: int, x2: int, y2: int, fill: str, outline: str = "", width: int = 1) -> None:
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)

    def _background(self) -> None:
        self._rect(0, 0, self.WIDTH, self.HEIGHT, "#0f1825")
        self._rect(0, 0, self.WIDTH, 58, "#111d2b")
        self._rect(0, 58, self.WIDTH, self.HEIGHT, "#172334")

        # Factory floor with restrained perspective/grid texture.
        tile = 36
        for x in range(0, self.WIDTH, tile):
            self.canvas.create_line(x, 58, x, self.HEIGHT, fill="#223249")
        for y in range(58, self.HEIGHT, tile):
            self.canvas.create_line(0, y, self.WIDTH, y, fill="#223249")
        for x in range(0, self.WIDTH, tile * 2):
            for y in range(58, self.HEIGHT, tile * 2):
                self._rect(x + 2, y + 2, x + tile - 2, y + tile - 2, "#1a293b")

        # Ambient wall lights.
        for x in (24, 94, 546, 616):
            self._rect(x - 6, 74, x + 6, 88, "#273b51", "#0b1119", 2)
            self._rect(x - 3, 77, x + 3, 85, "#7d91a8")

    def _progress_rail(self, phase: str, accent: str) -> None:
        effective = "verify" if phase == "complete" else phase
        idx = self.PHASES.index(effective) if effective in self.PHASES else 0
        xs = (220, 286, 352, 418)
        self.canvas.create_line(xs[0], 29, xs[-1], 29, fill="#31465d", width=4)
        for i, x in enumerate(xs):
            if i < idx:
                fill = accent
                radius = 7
            elif i == idx:
                pulse = 2 + int(2 * (1 + math.sin(self.frame / 4)))
                fill = accent
                radius = 7 + pulse
            else:
                fill = "#33475e"
                radius = 7
            self.canvas.create_oval(x - radius, 29 - radius, x + radius, 29 + radius, fill=fill, outline="#0b1119", width=2)

    def _status_beacon(self, phase: str, accent: str) -> None:
        if phase == "failed":
            color = "#ff6673"
        elif phase == "complete":
            color = "#65e391"
        else:
            color = accent
        glow = 3 + int(2 * (1 + math.sin(self.frame / 3)))
        self.canvas.create_oval(28 - glow, 28 - glow, 44 + glow, 44 + glow, outline=color, width=2)
        self.canvas.create_oval(30, 30, 42, 42, fill=color, outline="#0b1119", width=2)

    def _pipe(self, points: list[int]) -> None:
        self.canvas.create_line(*points, fill="#0c1119", width=14, joinstyle="miter")
        self.canvas.create_line(*points, fill="#344257", width=8, joinstyle="miter")
        for i in range(0, len(points) - 2, 2):
            x, y = points[i], points[i + 1]
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#53657d", outline="#0c1119")

    def _worker(self, x: int, y: int, *, facing: int = 1, carry: bool = False, accent: str = "#ff9d42") -> None:
        bob = int(2 * math.sin(self.frame / 3 + x))
        y += bob
        skin = "#f2bd81"
        shirt = "#3b86c7"
        pants = "#214b72"
        self._rect(x + 6, y, x + 21, y + 7, accent, "#10151d", 2)
        self._rect(x + 4, y + 7, x + 23, y + 14, skin, "#10151d", 2)
        self._rect(x + 7, y + 14, x + 20, y + 30, shirt, "#10151d", 2)
        arm_y = y + 17
        if carry:
            dx = 8 if facing > 0 else -8
            self._rect(x + 11 + dx, arm_y, x + 19 + dx, arm_y + 6, skin, "#10151d", 1)
        else:
            self._rect(x + 1, arm_y, x + 7, arm_y + 9, skin, "#10151d", 1)
            self._rect(x + 20, arm_y, x + 26, arm_y + 9, skin, "#10151d", 1)
        self._rect(x + 6, y + 30, x + 12, y + 41, pants, "#10151d", 1)
        self._rect(x + 15, y + 30, x + 21, y + 41, pants, "#10151d", 1)

    def _task_block(self, x: float, y: float, accent: str, *, glow: bool = True) -> None:
        size = 17
        if glow:
            radius = 25 + int(3 * math.sin(self.frame / 3))
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline=accent, width=1)
        self._rect(int(x - size), int(y - size), int(x + size), int(y + size), "#e2f1ff", "#0b1119", 2)
        self.canvas.create_polygon(
            x - size,
            y - size,
            x,
            y - size - 8,
            x + size,
            y - size,
            x,
            y - size + 8,
            fill=accent,
            outline="#0b1119",
        )
        self._rect(int(x - 7), int(y - 5), int(x + 7), int(y + 8), accent, "#0b1119", 1)

    def _analyze_station(self, active: bool, accent: str) -> None:
        x, y = 58, 112
        self._rect(x, y, x + 110, y + 80, "#24364a", "#0b1119", 3)
        self._rect(x + 12, y + 11, x + 98, y + 54, "#0e1721", "#0b1119", 2)
        beam = accent if active else "#4d6178"
        sweep = (self.frame * 4) % 70
        if active:
            self.canvas.create_line(x + 18 + sweep, y + 16, x + 18 + sweep, y + 49, fill=beam, width=3)
        for i in range(4):
            self._rect(x + 18 + i * 17, y + 62, x + 29 + i * 17, y + 68, beam if active and i == (self.frame // 5) % 4 else "#5a6d82")

    def _plan_station(self, active: bool, accent: str) -> None:
        x, y = 198, 90
        self._rect(x, y, x + 118, y + 100, "#233348", "#0b1119", 3)
        self._rect(x + 12, y + 12, x + 106, y + 73, "#102034", "#0b1119", 2)
        nodes = [(x + 30, y + 30), (x + 58, y + 48), (x + 84, y + 28), (x + 83, y + 61)]
        for a, b in ((0, 1), (1, 2), (1, 3)):
            self.canvas.create_line(*nodes[a], *nodes[b], fill=accent if active else "#536980", width=2)
        for i, (nx, ny) in enumerate(nodes):
            pulse = 2 if active and i == (self.frame // 7) % len(nodes) else 0
            self.canvas.create_oval(nx - 5 - pulse, ny - 5 - pulse, nx + 5 + pulse, ny + 5 + pulse, fill=accent if active else "#607389", outline="#0b1119")
        self._rect(x + 26, y + 80, x + 92, y + 88, accent if active else "#506278")

    def _work_station(self, active: bool, accent: str) -> None:
        x, y = 342, 102
        self._rect(x, y, x + 120, y + 88, "#26374a", "#0b1119", 3)
        self._rect(x + 10, y + 10, x + 110, y + 34, "#0e1822", "#0b1119", 2)
        for i in range(5):
            h = 5 + (((self.frame + i * 3) % 12) if active else 2)
            self._rect(x + 20 + i * 16, y + 29 - h, x + 28 + i * 16, y + 29, accent if active else "#506278")
        gear_color = accent if active else "#52677e"
        cx, cy = x + 38, y + 61
        radius = 15
        for i in range(8):
            angle = self.frame / 6 + i * math.pi / 4
            gx = cx + int(math.cos(angle) * radius)
            gy = cy + int(math.sin(angle) * radius)
            self._rect(gx - 3, gy - 3, gx + 3, gy + 3, gear_color)
        self.canvas.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill="#172433", outline=gear_color, width=3)
        self._rect(x + 70, y + 52, x + 104, y + 67, "#172433", "#0b1119", 2)
        self._rect(x + 73, y + 55, x + 101, y + 64, gear_color)

    def _verify_station(self, active: bool, success: bool, accent: str) -> None:
        x, y = 505, 102
        color = "#65e391" if success else (accent if active else "#52657c")
        self._rect(x, y, x + 18, y + 92, "#263647", "#0b1119", 3)
        self._rect(x + 70, y, x + 88, y + 92, "#263647", "#0b1119", 3)
        self.canvas.create_line(x + 18, y + 12, x + 70, y + 12, fill=color, width=4)
        self.canvas.create_line(x + 18, y + 82, x + 70, y + 82, fill="#394d63", width=4)
        if active or success:
            scan_y = y + 24 + ((self.frame * 4) % 46)
            self.canvas.create_line(x + 23, scan_y, x + 65, scan_y, fill=color, width=3)
            self.canvas.create_line(x + 27, scan_y + 4, x + 61, scan_y + 4, fill=color, width=1)

    def _conveyor(self, active: bool, accent: str) -> None:
        x1, y1, x2, y2 = 88, 218, 566, 258
        self._rect(x1, y1, x2, y2, "#101820", "#0b1119", 3)
        step = 25
        offset = (self.frame * 3) % step if active else 0
        for x in range(x1 - step, x2 + step, step):
            px = x + offset
            self.canvas.create_line(px, y1 + 4, px + 10, y2 - 4, fill="#405269", width=4)
        self.canvas.create_line(x1, y1 - 6, x2, y1 - 6, fill=accent if active else "#405269", width=2)

    def _task_position(self, phase: str) -> tuple[float, float]:
        if phase == "analyze":
            return 112 + 8 * math.sin(self.frame / 5), 172
        if phase == "plan":
            return 258 + 7 * math.sin(self.frame / 4), 199
        if phase == "work":
            return 382 + ((self.frame * 2) % 60), 238
        return 548, 176

    def _workers(self, phase: str, accent: str) -> None:
        positions = {
            "analyze": ((82, 270), (156, 278), (392, 292)),
            "plan": ((218, 275), (295, 278), (430, 292)),
            "work": ((342, 286), (415, 275), (492, 294)),
            "verify": ((470, 286), (535, 276), (585, 294)),
            "complete": ((220, 286), (306, 280), (405, 286)),
            "failed": ((224, 288), (324, 286), (424, 288)),
        }
        for i, (x, y) in enumerate(positions.get(phase, positions["analyze"])):
            self._worker(
                x,
                y,
                facing=-1 if i == 2 else 1,
                carry=phase in {"plan", "work"} and i == 1,
                accent="#f0a24b" if i != 2 else "#65b6f5",
            )

    def _activity_particles(self, phase: str, activity: str, accent: str) -> None:
        if phase == "work":
            for i in range(10):
                x = 354 + (i * 21 + self.frame * 5) % 112
                y = 86 + ((i * 13 + self.frame * 3) % 62)
                self._rect(x, y, x + 3, y + 3, accent)
        if activity in {"verification", "file_change", "command_execution", "work"}:
            for i in range(8):
                angle = (self.frame + i * 5) * 0.38
                x = 407 + int(math.cos(angle) * (17 + i))
                y = 181 + int(math.sin(angle) * (10 + i // 2))
                self._rect(x, y, x + 2, y + 2, "#ffd46a")

    def _complete_overlay(self, success: bool) -> None:
        color = "#5fe092" if success else "#ff6f7a"
        self._rect(180, 90, 460, 250, "#0e1722", "#0b1119", 4)
        self._rect(193, 103, 447, 237, "#172636", color, 3)
        if success:
            self._rect(294, 126, 346, 177, "#f1c64d", "#0b1119", 3)
            self._rect(311, 177, 329, 198, "#d49f28", "#0b1119", 2)
            self._rect(286, 198, 354, 209, "#f1c64d", "#0b1119", 2)
            self.canvas.create_arc(272, 130, 300, 164, start=90, extent=180, style="arc", outline="#f1c64d", width=6)
            self.canvas.create_arc(340, 130, 368, 164, start=-90, extent=180, style="arc", outline="#f1c64d", width=6)
            self.canvas.create_line(304, 149, 317, 163, 339, 137, fill="#ffffff", width=6)
        else:
            self.canvas.create_line(278, 128, 362, 208, fill=color, width=10)
            self.canvas.create_line(362, 128, 278, 208, fill=color, width=10)

    def _confetti(self) -> None:
        for i, (x, y0, color, speed) in enumerate(self.confetti):
            y = (y0 + self.frame * speed * 2) % (self.HEIGHT + 100) - 40
            drift = int(9 * math.sin((self.frame + i) / 4))
            self._rect(x + drift, y, x + drift + 4, y + 8, color)

    def draw(self, state: dict[str, Any] | None) -> None:
        self.canvas.delete("all")
        self._background()

        phase = phase_from_state(state)
        activity = activity_from_state(state)
        kind = task_kind_from_state(state)
        accent, accent_dark, accent_soft = task_palette(kind)

        self._status_beacon(phase, accent)
        self._progress_rail(phase, accent)
        self._pipe([0, 92, 48, 92, 48, 116, 96, 116])
        self._pipe([640, 92, 600, 92, 600, 118, 576, 118])

        self._analyze_station(phase == "analyze", accent)
        self._plan_station(phase == "plan", accent)
        self._work_station(phase == "work", accent)
        self._verify_station(phase == "verify", phase == "complete", accent)
        self._conveyor(phase in {"plan", "work", "verify"}, accent)
        self._workers(phase, accent)

        if phase not in {"complete", "failed"}:
            cx, cy = self._task_position(phase)
            self._task_block(cx, cy, accent)

        self._activity_particles(phase, activity, accent)

        if phase == "complete":
            self._complete_overlay(True)
            self._confetti()
        elif phase == "failed":
            self._complete_overlay(False)

    def _record_visual_error(self, exc: BaseException) -> None:
        try:
            VISUALIZER_LOG.parent.mkdir(parents=True, exist_ok=True)
            with VISUALIZER_LOG.open("a", encoding="utf-8") as handle:
                handle.write(f"task={self.task_id}\n")
                handle.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                handle.write("\n")
        except OSError:
            pass

    def _draw_failure_fallback(self) -> None:
        try:
            self.canvas.delete("all")
            self._rect(0, 0, self.WIDTH, self.HEIGHT, "#172334")
            self._rect(198, 92, 442, 258, "#101820", "#ff6f7a", 4)
            self.canvas.create_line(252, 132, 388, 218, fill="#ff6f7a", width=10)
            self.canvas.create_line(388, 132, 252, 218, fill="#ff6f7a", width=10)
        except Exception:
            pass

    def tick(self) -> None:
        state = load_task(self.task_id)
        if state is not None:
            self.last_state = state
        phase = phase_from_state(self.last_state)
        try:
            self.draw(self.last_state)
        except Exception as exc:
            self._record_visual_error(exc)
            self._draw_failure_fallback()
            phase = "failed"

        self.frame += 1
        if phase in {"complete", "failed"}:
            if self.terminal_since is None:
                self.terminal_since = time.monotonic()
            elif time.monotonic() - self.terminal_since >= self.auto_close_seconds:
                self.root.destroy()
                return
        else:
            self.terminal_since = None

        self.root.after(85, self.tick)

    def run(self) -> None:
        self.root.after(0, self.tick)
        self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live pixel-art task visualizer for Codex Usage Guard")
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
