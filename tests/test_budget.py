import unittest

from guard.budget import assert_action_allowed, budget_status


class BudgetTests(unittest.TestCase):
    def test_model_turn_budget(self):
        state = {
            "plan": {"max_actions": 5, "max_model_turns": 1, "max_retries": 1},
            "counters": {"actions": 1, "model_turns": 1, "retries": 0},
        }
        status = budget_status(state)
        self.assertEqual(status["remaining"]["model_turns"], 0)
        allowed, reason = assert_action_allowed(state, kind="model")
        self.assertFalse(allowed)
        self.assertIn("budget", reason)

    def test_retry_budget(self):
        state = {
            "plan": {"max_actions": 5, "max_model_turns": 3, "max_retries": 1},
            "counters": {"actions": 1, "model_turns": 0, "retries": 1},
        }
        allowed, reason = assert_action_allowed(state, kind="deterministic", is_retry=True)
        self.assertFalse(allowed)
        self.assertIn("retry", reason)


if __name__ == "__main__":
    unittest.main()
