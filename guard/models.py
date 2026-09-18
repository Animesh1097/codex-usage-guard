from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GuardPlan:
    task: str
    task_kind: str
    complexity: int
    risk: int
    strategy: str
    agent_profile: str
    preferred_model: str
    reasoning_effort: str
    context_budget_tokens: int
    max_model_turns: int
    max_retries: int
    max_parallel_agents: int
    predicted_steps: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["predicted_steps"] = list(self.predicted_steps)
        data["reasons"] = list(self.reasons)
        return data


@dataclass(frozen=True)
class NextAction:
    action: str
    reason: str
    stop: bool = False
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
