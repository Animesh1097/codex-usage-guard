import unittest

from guard.next_action import predict_next_action


class NextActionTests(unittest.TestCase):
    def test_prefers_tests_after_change(self):
        result = predict_next_action(task_kind="debugging", changed_files=2)
        self.assertEqual(result.action, "run_targeted_tests")

    def test_failed_test_is_diagnosed_before_retry(self):
        result = predict_next_action(task_kind="debugging", changed_files=2, test_status="fail")
        self.assertEqual(result.action, "inspect_test_failure")

    def test_docs_only_skips_model_heavy_checks(self):
        result = predict_next_action(
            task_kind="docs",
            changed_files=1,
            tests_available=True,
            build_available=True,
            docs_only=True,
        )
        self.assertEqual(result.action, "review_git_diff")

    def test_typecheck_precedes_build(self):
        result = predict_next_action(
            task_kind="ui",
            changed_files=2,
            test_status="pass",
            typecheck_available=True,
            build_available=True,
        )
        self.assertEqual(result.action, "run_typecheck")

    def test_budget_exhaustion_stops_normal_loop(self):
        result = predict_next_action(
            task_kind="debugging",
            changed_files=2,
            budget_exhausted=True,
        )
        self.assertEqual(result.action, "reassess_or_escalate")

    def test_stops_after_verified_general_change(self):
        result = predict_next_action(
            task_kind="general",
            changed_files=1,
            test_status="pass",
            build_status="not-needed",
            lint_status="not-needed",
            typecheck_status="not-needed",
            diff_reviewed=True,
        )
        self.assertTrue(result.stop)
        self.assertEqual(result.action, "stop")


if __name__ == "__main__":
    unittest.main()
