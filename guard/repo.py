from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SENSITIVE_MARKERS = (
    "auth", "security", "permission", "credential", "secret", "payment", "billing",
    "migration", "schema", "prisma", "database", ".github/workflows", "docker",
    "terraform", "deploy", "vercel", "netlify", "infra",
)


@dataclass(frozen=True)
class RepoProfile:
    root: str
    tracked_files: int
    changed_files: tuple[str, ...] = field(default_factory=tuple)
    changed_lines: int = 0
    project_types: tuple[str, ...] = field(default_factory=tuple)
    sensitive_files: tuple[str, ...] = field(default_factory=tuple)
    package_manager: str | None = None
    test_command: str | None = None
    build_command: str | None = None
    lint_command: str | None = None
    typecheck_command: str | None = None
    docs_only: bool = False
    signals: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("changed_files", "project_types", "sensitive_files", "signals"):
            data[key] = list(data[key])
        return data


def _run(root: Path, *args: str, timeout: int = 5) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            list(args),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _git_root(path: Path) -> Path:
    probe = _run(path, "git", "rev-parse", "--show-toplevel")
    if probe and probe.returncode == 0 and probe.stdout.strip():
        return Path(probe.stdout.strip()).resolve()
    return path.resolve()


def _changed_files(root: Path) -> list[str]:
    proc = _run(root, "git", "status", "--porcelain")
    if not proc or proc.returncode != 0:
        return []
    paths: list[str] = []
    for raw in proc.stdout.splitlines():
        if len(raw) < 4:
            continue
        path = raw[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            paths.append(path.replace("\\", "/"))
    return sorted(dict.fromkeys(paths))


def _tracked_count(root: Path) -> int:
    proc = _run(root, "git", "ls-files")
    if not proc or proc.returncode != 0:
        return 0
    return sum(1 for line in proc.stdout.splitlines() if line.strip())


def _changed_lines(root: Path) -> int:
    # "git diff HEAD" already includes both staged and unstaged tracked changes.
    # Do not add --cached separately or staged lines are double-counted.
    total = 0
    proc = _run(root, "git", "diff", "--numstat", "HEAD")
    if not proc or proc.returncode != 0:
        return 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        for value in parts[:2]:
            if value.isdigit():
                total += int(value)
    return total


def _package_json(root: Path) -> dict[str, Any]:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _package_manager(root: Path) -> str | None:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        return "bun"
    if (root / "package-lock.json").exists() or (root / "package.json").exists():
        return "npm"
    return None


def _script_command(pm: str | None, script: str, scripts: dict[str, Any]) -> str | None:
    if not pm or script not in scripts:
        return None
    if pm == "npm":
        return f"npm run {script}" if script != "test" else "npm test"
    if pm == "bun":
        return f"bun run {script}"
    return f"{pm} {script}"


def _project_types(root: Path) -> list[str]:
    types: list[str] = []
    checks = (
        ("javascript", ("package.json",)),
        ("python", ("pyproject.toml", "requirements.txt", "setup.py")),
        ("rust", ("Cargo.toml",)),
        ("go", ("go.mod",)),
        ("java", ("pom.xml", "build.gradle", "build.gradle.kts")),
        ("dotnet", ("global.json",)),
    )
    for name, markers in checks:
        if any((root / marker).exists() for marker in markers):
            types.append(name)
    if not types:
        types.append("unknown")
    return types


def _python_commands(root: Path) -> tuple[str | None, str | None, str | None]:
    chunks: list[str] = []
    for name in ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.cfg", "tox.ini"):
        source = root / name
        if source.exists():
            try:
                chunks.append(source.read_text(encoding="utf-8", errors="replace").lower())
            except OSError:
                pass
    text = "\n".join(chunks)
    test = "python -m pytest" if ("pytest" in text or (root / "pytest.ini").exists()) else None
    lint = "python -m ruff check ." if "ruff" in text else None
    typecheck = "python -m mypy ." if "mypy" in text else None
    return test, lint, typecheck


def inspect_repo(repo_path: str | Path = ".") -> RepoProfile:
    root = _git_root(Path(repo_path))
    changed = _changed_files(root)
    tracked = _tracked_count(root)
    line_count = _changed_lines(root)
    types = _project_types(root)
    sensitive = [p for p in changed if any(marker in p.lower() for marker in SENSITIVE_MARKERS)]
    docs_ext = {".md", ".mdx", ".rst", ".txt"}
    docs_only = bool(changed) and all(Path(p).suffix.lower() in docs_ext for p in changed)

    pm = _package_manager(root)
    package = _package_json(root)
    scripts = package.get("scripts", {}) if isinstance(package.get("scripts", {}), dict) else {}
    test = _script_command(pm, "test", scripts)
    build = _script_command(pm, "build", scripts)
    lint = _script_command(pm, "lint", scripts)
    typecheck = _script_command(pm, "typecheck", scripts)

    if "python" in types:
        py_test, py_lint, py_type = _python_commands(root)
        test = test or py_test
        lint = lint or py_lint
        typecheck = typecheck or py_type

    signals: list[str] = []
    if tracked >= 1500:
        signals.append("large_repository")
    if len(changed) >= 10:
        signals.append("many_changed_files")
    if line_count >= 500:
        signals.append("large_diff")
    if sensitive:
        signals.append("sensitive_paths_changed")
    if docs_only:
        signals.append("docs_only_change")
    if test:
        signals.append("tests_available")
    if build:
        signals.append("build_available")
    if lint:
        signals.append("lint_available")
    if typecheck:
        signals.append("typecheck_available")

    return RepoProfile(
        root=str(root),
        tracked_files=tracked,
        changed_files=tuple(changed),
        changed_lines=line_count,
        project_types=tuple(types),
        sensitive_files=tuple(sensitive),
        package_manager=pm,
        test_command=test,
        build_command=build,
        lint_command=lint,
        typecheck_command=typecheck,
        docs_only=docs_only,
        signals=tuple(signals),
    )


def hash_file(path: str | Path) -> str | None:
    target = Path(path)
    if not target.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with target.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def changed_file_hashes(profile: RepoProfile) -> dict[str, str]:
    root = Path(profile.root)
    result: dict[str, str] = {}
    for rel in profile.changed_files:
        digest = hash_file(root / rel)
        if digest:
            result[rel] = digest
    return result
