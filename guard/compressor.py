from __future__ import annotations

import math
import re
from collections.abc import Iterable


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CRITICAL = re.compile(
    r"(error|fail(?:ed|ure)?|exception|assert|traceback|expected|received|warn(?:ing)?|fatal|panic|timeout|denied|not found|cannot|unable)",
    re.IGNORECASE,
)
SUMMARY = re.compile(
    r"(tests?\b|passed|failed|skipped|duration|time|build|compiled|lint|coverage|suites?)",
    re.IGNORECASE,
)


def estimate_tokens(text: str) -> int:
    """Cheap local estimate for telemetry. It is not OpenAI billing data."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _clean(text: str) -> str:
    return ANSI.sub("", text).replace("\r\n", "\n")


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
    lines = _clean(text).splitlines()
    if len(lines) <= 80:
        return "\n".join(_dedupe(lines))

    interesting = {i for i, line in enumerate(lines) if CRITICAL.search(line)}
    for i in range(max(0, len(lines) - 80), len(lines)):
        if SUMMARY.search(lines[i]):
            interesting.add(i)

    compact = _windowed(lines, interesting, radius=3)
    if not compact:
        compact = lines[-60:]
    compact = _dedupe(compact)

    if len(compact) > max_lines:
        compact = compact[: max_lines - 1] + ["[output truncated by Codex Usage Guard]"]
    return "\n".join(compact)


def _compress_diff_hunk(hunk: list[str], context_radius: int) -> list[str]:
    if not hunk:
        return []
    header = hunk[0:1] if hunk[0].startswith("@@") else []
    body = hunk[1:] if header else hunk
    changed = {
        i
        for i, line in enumerate(body)
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    }
    if not changed:
        return header
    keep: set[int] = set()
    for idx in changed:
        keep.update(range(max(0, idx - context_radius), min(len(body), idx + context_radius + 1)))
    selected: list[str] = []
    last: int | None = None
    for idx in sorted(keep):
        if last is not None and idx > last + 1:
            selected.append(" ... unchanged context omitted ...")
        selected.append(body[idx])
        last = idx
    return header + selected


def compress_git_diff(text: str, max_lines: int = 320, context_radius: int = 2) -> str:
    lines = _clean(text).splitlines()
    if len(lines) <= 120:
        return "\n".join(lines)

    output: list[str] = []
    hunk: list[str] = []

    def flush_hunk() -> None:
        nonlocal hunk
        if hunk:
            output.extend(_compress_diff_hunk(hunk, context_radius))
            hunk = []

    for line in lines:
        if line.startswith("diff --git"):
            flush_hunk()
            output.append(line)
        elif line.startswith(("index ", "--- ", "+++ ", "new file mode ", "deleted file mode ", "rename from ", "rename to ")):
            flush_hunk()
            output.append(line)
        elif line.startswith("@@"):
            flush_hunk()
            hunk = [line]
        elif hunk:
            hunk.append(line)
    flush_hunk()

    output = _dedupe(output)
    if len(output) > max_lines:
        output = output[: max_lines - 1] + ["[diff truncated by Codex Usage Guard]"]
    return "\n".join(output)


def compress_log(text: str, max_lines: int = 180) -> str:
    lines = _clean(text).splitlines()
    if len(lines) <= 80:
        return "\n".join(_dedupe(lines))

    interesting = {i for i, line in enumerate(lines) if CRITICAL.search(line)}
    compact = _windowed(lines, interesting, radius=3)
    compact += lines[-25:]
    compact = _dedupe(compact)
    if len(compact) > max_lines:
        compact = compact[: max_lines - 1] + ["[log truncated by Codex Usage Guard]"]
    return "\n".join(compact)


def compress_generic(text: str, max_lines: int = 180) -> str:
    lines = _dedupe(_clean(text).splitlines())
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
