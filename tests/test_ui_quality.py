import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from guard.repo import RepoProfile
from guard.ui_quality import audit_ui, design_brief, inspect_ui_context


class UIQualityTests(unittest.TestCase):
    def _profile(self, root: Path, changed: tuple[str, ...]) -> RepoProfile:
        return RepoProfile(
            root=str(root),
            tracked_files=len(changed),
            changed_files=changed,
            project_types=("javascript",),
        )

    def test_audit_flags_accessibility_and_generated_ui_reflexes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "Card.tsx"
            source.parent.mkdir(parents=True)
            source.write_text(
                '<div onClick={save} className="border shadow-2xl rounded-3xl transition-all">Save</div>\n'
                '<img src="/hero.png" />\n'
                '<p className="uppercase tracking-widest">Overview</p>\n',
                encoding="utf-8",
            )
            profile = self._profile(root, ("src/Card.tsx",))
            with patch("guard.ui_quality.inspect_repo", return_value=profile):
                result = audit_ui(root)

            rules = {item["rule"] for item in result["findings"]}
            self.assertIn("non-semantic-click-target", rules)
            self.assertIn("missing-image-alt", rules)
            self.assertIn("oversized-radius", rules)
            self.assertIn("transition-all", rules)
            self.assertIn("border-plus-heavy-shadow", rules)
            self.assertIn("eyebrow-reflex", rules)
            self.assertFalse(result["passes_strict_gate"])
            self.assertTrue(result["source_quality_only"])
            self.assertTrue(result["visual_review_required"])
            self.assertIsNone(result["visual_quality_approved"])

    def test_high_ambition_ui_task_requires_two_rendered_critiques(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = self._profile(root, ())
            with patch("guard.ui_quality.inspect_repo", return_value=profile):
                brief = design_brief(
                    "Build a polished eye-catching CRM dashboard that is not generic",
                    root,
                )

            self.assertEqual(brief["visual_ambition"], "design-grade")
            self.assertEqual(brief["rendered_critique_passes"], 2)
            self.assertTrue(brief["anti_default_shell"])
            self.assertTrue(brief["browser_visual_review_required"])

    def test_standard_ui_task_uses_production_bar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = self._profile(root, ())
            with patch("guard.ui_quality.inspect_repo", return_value=profile):
                brief = design_brief("fix the form spacing on mobile", root)

            self.assertEqual(brief["visual_ambition"], "production")
            self.assertEqual(brief["rendered_critique_passes"], 1)
            self.assertFalse(brief["anti_default_shell"])

    def test_context_detects_existing_design_system(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text(
                '{"dependencies":{"tailwindcss":"1","@radix-ui/react-dialog":"1","lucide-react":"1"}}',
                encoding="utf-8",
            )
            (root / "components.json").write_text("{}", encoding="utf-8")
            css = root / "src" / "index.css"
            css.parent.mkdir(parents=True)
            css.write_text(":root { --surface: white; --ink: black; }", encoding="utf-8")
            profile = self._profile(root, ())
            with patch("guard.ui_quality.inspect_repo", return_value=profile):
                result = inspect_ui_context(root)

            self.assertIn("tailwind", result["styling"])
            self.assertIn("radix", result["component_libraries"])
            self.assertIn("shadcn", result["component_libraries"])
            self.assertGreaterEqual(result["css_variable_count"], 2)


if __name__ == "__main__":
    unittest.main()
