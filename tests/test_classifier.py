import unittest

from guard.classifier import classify_task


class ClassifierTests(unittest.TestCase):
    def test_simple_task_uses_fast_profile(self):
        plan = classify_task("change the footer phone number", repo_path="/definitely/not/a/repo")
        self.assertLessEqual(plan.complexity, 2)
        self.assertEqual(plan.agent_profile, "guard_fast")
        self.assertEqual(plan.reasoning_effort, "low")

    def test_complex_production_bug_escalates(self):
        plan = classify_task(
            "Investigate an intermittent production authentication failure, find root cause, fix it, and verify deployment",
            repo_path="/definitely/not/a/repo",
        )
        self.assertGreaterEqual(plan.complexity, 8)
        self.assertGreaterEqual(plan.risk, 6)
        self.assertEqual(plan.agent_profile, "guard_reasoner")
        self.assertEqual(plan.strategy, "plan_execute_verify")
        self.assertEqual(plan.max_parallel_agents, 1)


if __name__ == "__main__":
    unittest.main()
