import json
import unittest
from pathlib import Path

from guard.classifier import policy_for_scores


class PolicyFixtureParityTests(unittest.TestCase):
    def test_python_policy_matches_shared_fixtures(self):
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "policy_cases.json"
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))

        strategy_map = {
            "single-turn": "single_turn",
            "single-agent": "single_agent",
            "bounded-loop": "bounded_agent_loop",
            "plan-execute-verify": "plan_execute_verify",
        }

        for case in cases:
            with self.subTest(case=case["name"]):
                policy = policy_for_scores(case["complexity"], case["risk"])
                self.assertEqual(policy["strategy"], strategy_map[case["strategy"]])
                self.assertEqual(policy["max_actions"], case["max_actions"])
                self.assertEqual(policy["max_turns"], case["max_model_turns"])


if __name__ == "__main__":
    unittest.main()
