from __future__ import annotations

import re

from .repo import RepoProfile


def _has(text: str, word: str) -> bool:
    if " " in word:
        return word in text
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def recommend_skill_refs(task: str, profile: RepoProfile, task_kind: str) -> list[str]:
    """Choose at most two on-demand craft references for the current task."""
    text = " ".join(task.lower().split())
    refs: list[str] = []

    ui_words = (
        "ui", "ux", "frontend", "layout", "responsive", "dashboard", "form",
        "landing page", "component", "css", "tailwind", "accessibility",
    )
    architecture_words = (
        "architecture", "system design", "schema", "database", "api", "service",
        "queue", "cache", "migration", "scalability", "multi-tenant",
    )
    browser_words = (
        "browser", "visual", "screenshot", "e2e", "qa", "interaction",
        "responsive", "layout", "form", "frontend",
    )

    if task_kind == "ui" or any(_has(text, word) for word in ui_words):
        refs.append("references/ui-ux.md")

    if task_kind in {"database", "security", "refactor"} or any(
        _has(text, word) for word in architecture_words
    ):
        refs.append("references/system-design.md")

    if (
        task_kind == "ui"
        and any(_has(text, word) for word in browser_words)
        and "references/browser-verification.md" not in refs
    ):
        refs.append("references/browser-verification.md")

    if not refs and profile.tracked_files >= 1500:
        refs.append("references/system-design.md")

    return refs[:2]
