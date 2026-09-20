from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from typing import Any, TextIO


SPINNER = ("◐", "◓", "◑", "◒")
STAGES = ("analyze", "plan", "work", "verify")
ALIASES = {"judge": "plan", "route": "plan", "execute": "work"}


def _bar(used: int, limit: int, width: int = 8) -> str:
    if limit <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, used / limit))
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _stage_line(active: str, frame: int) -> str:
    active = ALIASES.get(active, active)
    if active not in STAGES:
        active = "analyze"
    idx = STAGES.index(active)
    parts: list[str] = []
    for i, _ in enumerate(STAGES):
        if i < idx:
            parts.append("●")
        elif i == idx:
            parts.append(SPINNER[frame % len(SPINNER)])
        else:
            parts.append("○")
    return "━━".join(parts)


def _status_symbol(status: str | None) -> str:
    if status in {"completed", "verified", "parent-match"}:
        return "✓"
    if status in {"failed", "blocked", "abandoned", "budget-blocked"}:
        return "×"
    return "◌"


def render_hud(
    *,
    phase: str,
    frame: int = 0,
    coordinator_model: str | None = None,
    requested_model: str | None = None,
    reasoning: str | None = None,
    action_used: int = 0,
    action_limit: int = 0,
    model_turns_used: int = 0,
    model_turns_limit: int = 0,
    tokens: int | None = None,
    status: str | None = None,
    judge_used: bool = False,
) -> str:
    del coordinator_model, requested_model, reasoning, judge_used
    token_text = f"{tokens:,}" if isinstance(tokens, int) else "—"
    flow = _stage_line(phase, frame)
    lines = [
        "╭──────────────────────────────╮",
        f"│  {flow:<27}│",
        f"│  actions {_bar(action_used, action_limit)} {action_used:>2}/{action_limit:<2}      │",
        f"│  turns   {_bar(model_turns_used, model_turns_limit)} {model_turns_used:>2}/{model_turns_limit:<2}      │",
        f"│  tokens  {token_text:<12}       {_status_symbol(status):>2} │",
        "╰──────────────────────────────╯",
    ]
    return "\n".join(lines)


@dataclass
class HUDState:
    phase: str = "analyze"
    coordinator_model: str | None = None
    requested_model: str | None = None
    reasoning: str | None = None
    action_used: int = 0
    action_limit: int = 0
    model_turns_used: int = 0
    model_turns_limit: int = 0
    tokens: int | None = None
    status: str | None = None
    judge_used: bool = False


class AnimatedHUD:
    def __init__(
        self,
        state: HUDState,
        *,
        stream: TextIO | None = None,
        enabled: bool | None = None,
        interval: float = 0.12,
    ) -> None:
        self.state = state
        self.stream = stream or sys.stderr
        self.enabled = self.stream.isatty() if enabled is None else enabled
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lines = 6

    def _draw(self, frame: int) -> None:
        text = render_hud(
            phase=self.state.phase,
            frame=frame,
            action_used=self.state.action_used,
            action_limit=self.state.action_limit,
            model_turns_used=self.state.model_turns_used,
            model_turns_limit=self.state.model_turns_limit,
            tokens=self.state.tokens,
            status=self.state.status,
        )
        if frame:
            self.stream.write(f"\x1b[{self._lines}A")
        self.stream.write(text + "\n")
        self.stream.flush()

    def _loop(self) -> None:
        frame = 0
        self.stream.write("\x1b[?25l")
        self.stream.flush()
        try:
            while not self._stop.is_set():
                self._draw(frame)
                frame += 1
                self._stop.wait(self.interval)
        finally:
            self.stream.write("\x1b[?25h")
            self.stream.flush()

    def start(self) -> None:
        if not self.enabled:
            return
        self._thread = threading.Thread(target=self._loop, name="usage-guard-hud", daemon=True)
        self._thread.start()

    def stop(self, *, final_status: str | None = None, tokens: int | None = None) -> None:
        if final_status is not None:
            self.state.status = final_status
        if tokens is not None:
            self.state.tokens = tokens
        if not self.enabled:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval * 4))
        self._draw(1)


def visual_snapshot(state: dict[str, Any], *, phase: str | None = None) -> str:
    plan = state.get("plan", {})
    counters = state.get("counters", {})
    visual = state.get("visual") or {}
    usage = state.get("usage") or {}
    finish = usage.get("finish") or {}
    delta = usage.get("delta") or {}
    token_value = delta.get("tokens_delta")
    if not isinstance(token_value, int):
        token_value = finish.get("tokens_total")
    if not isinstance(token_value, int):
        token_value = None

    current_phase = phase or str(visual.get("phase") or "analyze")
    current_phase = ALIASES.get(current_phase, current_phase)

    return render_hud(
        phase=current_phase,
        action_used=int(counters.get("actions", 0)),
        action_limit=int(plan.get("max_actions", 0)),
        model_turns_used=int(counters.get("model_turns", 0)),
        model_turns_limit=int(plan.get("max_model_turns", 0)),
        tokens=token_value,
        status=str(state.get("status") or "active"),
    )
