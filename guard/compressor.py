from __future__ import annotations

import math
import re
from collections.abc import Iterable


CRITICAL = re.compile(
    r"(error|fail(?:ed|ure)?|exception|assert|traceback|expected|received|warn(?:ing)?|fatal|panic|timeout|denied)",
    re.IGNORECASE,
)
SUMMARY = re.compile(r"(tests?\b|passed|failed|skipped|duration|time|build|compiled|lint)", re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Cheap local estimate. It is telemetry, not OpenAI billing data."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _dedupe(lines: Iterable[str]) -> list[str]:
    out: list[str] = []
    previous: str | None = None
    repeats = 0
    for line in lines:
        if line == previous:
            repeats += 1
            continue
        if repeats:
            out.append(f"[previous line repeated {repeats}x]")
            repeats = 0
        out.append(line)
        previous = line
    if repeats:
        out.append(f"[previous line repeated {repeats}x]")
    return out


def _windowed(lines: list[str], interesting: set[int], radius: int = 2) -> list[str]:
    keep: set[int] = set()
    for idx in interesting:
        keep.update(range(max(0, idx - radius), min(len(lines), idx + radius + 1)))
    return [lines[idx] for idx in sorted(keep)]


def compress_test_output(text: str, max_lines: int = 220) -> str:
    lines = text.splitlines()
    if len(lines) <= 80:
        return text
    interesting = {i for i, line in enumerate(lines) if CRITICAL.search(line)}
    for i in range(max(0, len(lines) - 60), len(lines)):
        if SUMMARY.search(lines[i]):
            interesting.add(i)
    compact = _windowed(lines, interesting, radius=2)
    if not compact:
        compact = lines[-60:]
    compact = _dedupe(compact)
    if len(compact) > max_lines:
        compact = compact[: max_lines - 1] + ["[output truncated by Codex Usage Guard]"]
    return "\n".join(compact)


def compress_git_diff(text: str, max_lines: int = 260) -> str:
    lines = text.splitlines()
    if len(lines) <= 120:
        return text
    keep: list[str] = []
    for line in lines:
        if (
            line.startswith("diff --git")
            or line.startswith("index ")
            or line.startswith("--- ")
            or line.startswith("+++ ")
            or line.startswith("@@")
            or line.startswith("+")
            or line.startswith("-")
        ):
            keep.append(line)
    keep = _dedupe(keep)
    if len(keep) > max_lines:
        keep = keep[: max_lines - 1] + ["[diff truncated by Codex Usage Guard]"]
    return "\n".join(keep)


def compress_log(text: str, max_lines: int = 180) -> str:
    lines = text.splitlines()
    if len(lines) <= 80:
        return text
    interesting = {i for i, line in enumerate(lines) if CRITICAL.search(line)}
    compact = _windowed(lines, interesting, radius=2)
    compact += lines[-20:]
    compact = _dedupe(compact)
    if len(compact) > max_lines:
        compact = compact[: max_lines - 1] + ["[log truncated by Codex Usage Guard]"]
    return "\n".join(compact)


def compress_generic(text: str, max_lines: int = 180) -> str:
    lines = _dedupe(text.splitlines())
    if len(lines) <= max_lines:
        return "\n".join(lines)
    head = lines[: max_lines // 3]
    tail = lines[-(max_lines - len(head) - 1) :]
    return "\n".join(head + ["[middle omitted by Codex Usage Guard]"] + tail)


def compress(text: str, kind: str) -> str:
    kind = kind.lower()
    if kind == "test":
        return compress_test_output(text)
    if kind == "git":
        return compress_git_diff(text)
    if kind == "log":
        return compress_log(text)
    return compress_generic(text)
