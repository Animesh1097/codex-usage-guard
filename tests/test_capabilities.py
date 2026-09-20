import unittest
from dataclasses import replace

from guard.capabilities import recommend_skill_refs
from guard.repo import RepoProfile


BASE = RepoProfile(root="/repo", tracked_files=10)


class CapabilityTests(unittest.TestCase):
    def test_ui_task_loads_ui_and_browser_refs(self):
        refs = recommend_skill_refs(
            "fix the responsive seller form layout",
            BASE,
            "ui",
        )
        self.assertIn("references/ui-ux.md", refs)
        self.assertIn("references/browser-verification.md", refs)
        self.assertLessEqual(len(refs), 2)

    def test_ui_bug_still_loads_ui_browser_refs(self):
        refs = recommend_skill_refs(
            "fix the mobile layout overlap and verify the responsive screen",
            BASE,
            "debugging",
        )
        self.assertIn("references/ui-ux.md", refs)
        self.assertIn("references/browser-verification.md", refs)

    def test_architecture_task_loads_system_design(self):
        refs = recommend_skill_refs(
            "design the API and database schema for a multi-tenant CRM",
            BASE,
            "database",
        )
        self.assertIn("references/system-design.md", refs)


if __name__ == "__main__":
    unittest.main()
