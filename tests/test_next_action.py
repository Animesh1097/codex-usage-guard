import unittest

from guard.next_action import predict_next_action


class NextActionTests(unittest.TestCase):
    def test_prefers_tests_after_change(self):
        result = predict_next_action(task_kind="debugging", changed_files=2)
        self.assertEqual(result.action, "run_targeted_tests")

    def test_failed_test_is_diagnosed_before_retry(self):
        result = predict_next_action(task_kind="debugging", changed_files=2, test_status="fail")
        self.assertEqual(result.action, "inspect_test_failure")

    def test_stops_after_verified_general_change(self):
        result = predict_next_action(
            task_kind="general",
            changed_files=1,
            test_status="pass",
            build_status="not-needed",
            lint_status="not-needed",
            diff_reviewed=True,
        )
        self.assertTrue(result.stop)
        self.assertEqual(result.action, "stop")


if __name__ == "__main__":
    unittest.main()
