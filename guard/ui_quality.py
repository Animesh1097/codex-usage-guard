from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .repo import inspect_repo


UI_EXTENSIONS = {".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte"}

HIGH_AMBITION_TERMS = (
    "eye-catching", "eye catching", "premium", "luxury", "editorial", "distinctive",
    "unique", "polished", "memorable", "fashion", "brand-forward", "high-end",
    "high end", "world class", "beautiful", "stunning", "visual identity",
    "not generic", "not like a generic", "best-looking", "best looking",
)

BRAND_SURFACE_TERMS = (
    "landing page", "homepage", "campaign", "portfolio", "launch page", "marketing",
    "brand", "hero", "website",
)

@dataclass(frozen=True)
class UIFinding:
    severity: str
    rule: str
    path: str
    line: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    (
        "important",
        "non-semantic-click-target",
        re.compile(r"<(?:div|span)\b[^>]*\bonClick\s*=", re.IGNORECASE),
        "Use a semantic button/link for interactive behavior instead of a clickable div/span.",
    ),
    (
        "important",
        "missing-image-alt",
        re.compile(r"<img\b(?![^>]*\balt\s*=)[^>]*>", re.IGNORECASE),
        "Image is missing an alt attribute. Use meaningful alt text or alt=\"\" for decorative imagery.",
    ),
    (
        "important",
        "focus-ring-removed",
        re.compile(r"(?:outline\s*:\s*none|outline-none)(?![^\n]*(?:focus-visible|focus:))", re.IGNORECASE),
        "Focus indication appears to be removed without a visible keyboard-focus replacement.",
    ),
    (
        "important",
        "unsafe-gradient-text",
        re.compile(r"(?:bg-clip-text|background-clip\s*:\s*text)", re.IGNORECASE),
        "Gradient/clipped text is a common decorative reflex and can hurt legibility; prefer solid text unless brand intent requires it.",
    ),
    (
        "important",
        "decorative-stripes",
        re.compile(r"repeating-(?:linear|radial)-gradient\s*\(", re.IGNORECASE),
        "Decorative repeating-gradient backgrounds often add noise without improving hierarchy.",
    ),
    (
        "important",
        "arbitrary-z-index",
        re.compile(r"(?:z-\[(?:[1-9]\d{2,})\]|z-index\s*:\s*(?:[1-9]\d{2,}))", re.IGNORECASE),
        "Use a small semantic z-index scale instead of arbitrary very large values.",
    ),
    (
        "polish",
        "transition-all",
        re.compile(r"(?:\btransition-all\b|transition\s*:\s*all\b)", re.IGNORECASE),
        "Animate only the properties that should move; transition-all creates accidental motion and can be expensive.",
    ),
    (
        "polish",
        "bounce-motion",
        re.compile(r"(?:\banimate-bounce\b|animation[^;\n]*\bbounce\b)", re.IGNORECASE),
        "Bounce/elastic motion is rarely appropriate for product UI; use restrained, interruptible transitions.",
    ),
    (
        "polish",
        "oversized-radius",
        re.compile(r"(?:rounded-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)|border-radius\s*:\s*(?:2[4-9]|[3-9]\d)px)", re.IGNORECASE),
        "Large card/section radii can make generated UI feel generic. Confirm this radius is part of the design language.",
    ),
    (
        "polish",
        "eyebrow-reflex",
        re.compile(r"\buppercase\b[^\n]{0,100}\btracking-(?:wide|wider|widest)\b|\btracking-(?:wide|wider|widest)\b[^\n]{0,100}\buppercase\b", re.IGNORECASE),
        "Repeated tiny uppercase tracked labels are a common generated-UI scaffold. Use only when the information hierarchy earns it.",
    ),
)


def _read_package(root: Path) -> dict[str, Any]:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}


def design_brief(task: str, repo_path: str | Path = ".") -> dict[str, Any]:
    """Return deterministic UI art-direction constraints before implementation."""
    context = inspect_ui_context(repo_path)
    text = " ".join(task.lower().split())
    high_ambition = any(term in text for term in HIGH_AMBITION_TERMS)
    surface = "brand-marketing" if any(term in text for term in BRAND_SURFACE_TERMS) else "product-ui"

    if high_ambition:
        critique_passes = 2
        bar = "design-grade"
        direction = (
            "Create a deliberate visual concept before coding. The result must have a recognizable "
            "composition, typographic hierarchy, and product-specific identity rather than a default SaaS shell."
        )
    else:
        critique_passes = 1
        bar = "production"
        direction = (
            "Preserve or establish a coherent product design system and make the primary workflow clear, "
            "responsive, accessible, and visually intentional."
        )

    return {
        "surface": surface,
        "visual_ambition": bar,
        "rendered_critique_passes": critique_passes,
        "browser_visual_review_required": True,
        "source_audit_is_not_visual_approval": True,
        "direction": direction,
        "must_define_before_coding": [
            "primary user and primary action",
            "visual concept in one sentence",
            "layout/composition rule",
            "typography roles",
            "color roles and accent restraint",
            "density/spacing rhythm",
            "signature detail that makes the interface product-specific",
        ],
        "rendered_review_dimensions": [
            "first-viewport hierarchy",
            "composition and balance",
            "typographic character",
            "spacing rhythm",
            "color/material coherence",
            "control craft and states",
            "responsive recomposition",
            "product-specific identity",
            "accessibility and focus",
        ],
        "anti_default_shell": high_ambition,
        "ui_context": context,
    }


def inspect_ui_context(repo_path: str | Path = ".") -> dict[str, Any]:
    profile = inspect_repo(repo_path)
    root = Path(profile.root)
    package = _read_package(root)
    deps: dict[str, Any] = {}
    for key in ("dependencies", "devDependencies"):
        value = package.get(key)
        if isinstance(value, dict):
            deps.update(value)

    styling: list[str] = []
    libraries: list[str] = []
    if "tailwindcss" in deps or (root / "tailwind.config.js").exists() or (root / "tailwind.config.ts").exists():
        styling.append("tailwind")
    if any(name in deps for name in ("styled-components", "@emotion/react", "@emotion/styled")):
        styling.append("css-in-js")
    if any(name in deps for name in ("sass", "node-sass")):
        styling.append("sass")
    if "@mui/material" in deps:
        libraries.append("mui")
    if "antd" in deps:
        libraries.append("antd")
    if "@chakra-ui/react" in deps:
        libraries.append("chakra")
    if any(name.startswith("@radix-ui/") for name in deps):
        libraries.append("radix")
    if "lucide-react" in deps:
        libraries.append("lucide")
    if (root / "components.json").exists():
        libraries.append("shadcn")

    token_candidates = [
        "src/index.css", "src/globals.css", "app/globals.css", "styles/globals.css",
        "src/styles.css", "src/styles/globals.css", "theme.css", "tokens.css",
    ]
    token_files: list[str] = []
    css_variable_count = 0
    for rel in token_candidates:
        path = root / rel
        if not path.is_file():
            continue
        token_files.append(rel)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:50000]
        except OSError:
            continue
        css_variable_count += len(re.findall(r"--[a-zA-Z0-9_-]+\s*:", text))

    return {
        "repo_root": profile.root,
        "styling": sorted(set(styling)) or ["existing-project-style"],
        "component_libraries": sorted(set(libraries)),
        "token_files": token_files,
        "css_variable_count": css_variable_count,
        "changed_ui_files": [
            path for path in profile.changed_files if Path(path).suffix.lower() in UI_EXTENSIONS
        ],
    }


def _candidate_files(root: Path, changed: tuple[str, ...], max_files: int = 200) -> list[Path]:
    changed_ui = [
        root / rel
        for rel in changed
        if Path(rel).suffix.lower() in UI_EXTENSIONS and (root / rel).is_file()
    ]
    if changed_ui:
        return changed_ui[:max_files]

    roots = [root / name for name in ("src", "app", "pages", "components", "styles")]
    results: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in UI_EXTENSIONS:
                results.append(path)
                if len(results) >= max_files:
                    return results
    return results


def audit_ui(repo_path: str | Path = ".", *, max_files: int = 200) -> dict[str, Any]:
    profile = inspect_repo(repo_path)
    root = Path(profile.root)
    files = _candidate_files(root, profile.changed_files, max_files=max_files)
    findings: list[UIFinding] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        rel = path.relative_to(root).as_posix()
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            for severity, rule, pattern, message in RULES:
                if pattern.search(line):
                    findings.append(UIFinding(severity, rule, rel, line_no, message))

            # Border + very large shadow on one utility/class line is a common generated-card tell.
            lowered = line.lower()
            if (
                ("shadow-2xl" in lowered or "shadow-xl" in lowered)
                and re.search(r"\bborder(?:-|\b)", lowered)
            ):
                findings.append(
                    UIFinding(
                        "polish",
                        "border-plus-heavy-shadow",
                        rel,
                        line_no,
                        "Avoid combining a structural border with a heavy decorative shadow unless the design system explicitly uses both.",
                    )
                )

    order = {"blocker": 0, "important": 1, "polish": 2}
    findings.sort(key=lambda item: (order.get(item.severity, 9), item.path, item.line, item.rule))
    counts = {
        "blocker": sum(1 for item in findings if item.severity == "blocker"),
        "important": sum(1 for item in findings if item.severity == "important"),
        "polish": sum(1 for item in findings if item.severity == "polish"),
    }
    return {
        "repo_root": profile.root,
        "files_scanned": len(files),
        "used_changed_files": bool(
            [path for path in profile.changed_files if Path(path).suffix.lower() in UI_EXTENSIONS]
        ),
        "counts": counts,
        "findings": [item.to_dict() for item in findings],
        "passes_strict_gate": counts["blocker"] == 0 and counts["important"] == 0,
        "source_quality_only": True,
        "visual_review_required": True,
        "visual_quality_approved": None,
        "visual_quality_note": (
            "This deterministic source audit checks implementation hygiene and common UI anti-patterns. "
            "It cannot approve aesthetic quality; rendered visual critique is still required."
        ),
    }
