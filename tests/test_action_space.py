import unittest

from guard.action_space import build_action_space


class ActionSpaceTests(unittest.TestCase):
    def test_ui_space_offers_real_browser_verification_when_available(self):
        actions = build_action_space(
            task_kind="ui",
            changed_files=2,
            test_status="pass",
            build_status="pass",
            lint_status="not-needed",
            typecheck_status="not-needed",
            browser_status="not-run",
            diff_reviewed=False,
            tests_available=True,
            build_available=True,
            lint_available=False,
            typecheck_available=False,
            browser_available=True,
            docs_only=False,
            production_check_required=False,
        )
        names = [item["operation"] for item in actions]
        self.assertIn("BROWSER_VERIFY", names)
        self.assertIn("DIFF_REVIEW", names)
        self.assertNotIn("DONE", names)

    def test_done_only_appears_after_verification_and_diff_review(self):
        actions = build_action_space(
            task_kind="general",
            changed_files=1,
            test_status="pass",
            build_status="not-needed",
            lint_status="not-needed",
            typecheck_status="not-needed",
            browser_status="not-needed",
            diff_reviewed=True,
            tests_available=True,
            build_available=False,
            lint_available=False,
            typecheck_available=False,
            browser_available=False,
            docs_only=False,
            production_check_required=False,
        )
        self.assertIn("DONE", [item["operation"] for item in actions])


if __name__ == "__main__":
    unittest.main()
