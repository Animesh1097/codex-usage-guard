from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, TextIO


SPINNER = ("◐", "◓", "◑", "◒")
STAGES = ("analyze", "judge", "route", "execute", "verify")
STAGE_SYMBOLS = {
    "analyze": "◆",
    "judge": "◇",
    "route": "↗",
    "execute": "⚙",
    "verify": "✓",
}


def _short_model(model: object) -> str:
    text = str(model or "?")
    return (
        text.replace("gpt-5.6-", "")
        .replace("gpt-5.6", "5.6")
        .replace("gpt-", "")
    )


def _bar(used: int, limit: int, width: int = 8) -> str:
    if limit <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, used / limit))
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _stage_line(active: str, done: set[str], skipped: set[str], frame: int) -> str:
    parts: list[str] = []
    for stage in STAGES:
        if stage in skipped:
            symbol = "·"
        elif stage in done:
            symbol = "●"
        elif stage == active:
            symbol = SPINNER[frame % len(SPINNER)]
        else:
            symbol = "○"
        parts.append(symbol)
    return "━━".join(parts)


def _status_symbol(status: str | None) -> str:
    if status in {"verified", "parent-match", "completed"}:
        return "✓"
    if status in {
        "failed",
        "model-mismatch",
        "reasoning-mismatch",
        "unverified",
        "unverified-no-thread",
        "budget-blocked",
        "blocked",
    }:
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
    phase = phase if phase in STAGES else "analyze"
    idx = STAGES.index(phase)
    done = set(STAGES[:idx])
    skipped: set[str] = set()
    if not judge_used:
        skipped.add("judge")

    flow = _stage_line(phase, done, skipped, frame)
    left = _short_model(coordinator_model)
    right = _short_model(requested_model)
    arrow = "──►" if left != right else "──"
    reason = (reasoning or "?").lower()
    token_text = f"{tokens:,}" if isinstance(tokens, int) else "—"

    lines = [
        "╭──────────────────────────────╮",
        f"│  {flow:<27}│",
        f"│  {left:<8} {arrow} {right:<8} {reason[:1].upper():>2} │",
        f"│  {_bar(action_used, action_limit)} {action_used:>2}/{action_limit:<2}  ◇ {_bar(model_turns_used, model_turns_limit, 5)} │",
        f"│  ◒ {token_text:<10}            {_status_symbol(status):>2} │",
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
            coordinator_model=self.state.coordinator_model,
            requested_model=self.state.requested_model,
            reasoning=self.state.reasoning,
            action_used=self.state.action_used,
            action_limit=self.state.action_limit,
            model_turns_used=self.state.model_turns_used,
            model_turns_limit=self.state.model_turns_limit,
            tokens=self.state.tokens,
            status=self.state.status,
            judge_used=self.state.judge_used,
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


def visual_snapshot(state: dict[str, Any], *, phase: str = "verify") -> str:
    plan = state.get("plan", {})
    counters = state.get("counters", {})
    execution = state.get("execution") or {}
    limits = {
        "actions": int(plan.get("max_actions", 0)),
        "model_turns": int(plan.get("max_model_turns", 0)),
    }
    worker_usage = execution.get("worker_usage") or {}
    tokens = worker_usage.get("tokens_total")
    coordinator = execution.get("coordinator_model")
    requested = execution.get("requested_model") or plan.get("preferred_model")
    reasoning = execution.get("effective_reasoning") or execution.get("requested_reasoning") or plan.get("reasoning_effort")
    return render_hud(
        phase=phase,
        coordinator_model=coordinator,
        requested_model=requested,
        reasoning=reasoning,
        action_used=int(counters.get("actions", 0)),
        action_limit=limits["actions"],
        model_turns_used=int(counters.get("model_turns", 0)),
        model_turns_limit=limits["model_turns"],
        tokens=tokens if isinstance(tokens, int) else None,
        status=execution.get("status") or state.get("status"),
        judge_used=bool(state.get("judgement")),
    )
