import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from guard.classifier import classify_task


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


class ClassifierTests(unittest.TestCase):
    def test_simple_task_uses_fast_profile(self):
        plan = classify_task("change the footer phone number", repo_path="/definitely/not/a/repo")
        self.assertLessEqual(plan.complexity, 2)
        self.assertEqual(plan.agent_profile, "guard_fast")
        self.assertEqual(plan.preferred_model, "gpt-5.6-luna")
        self.assertEqual(plan.reasoning_effort, "low")

    def test_complex_production_bug_uses_documented_strong_model(self):
        plan = classify_task(
            "Investigate an intermittent production authentication failure, find root cause, fix it, and verify deployment",
            repo_path="/definitely/not/a/repo",
        )
        self.assertGreaterEqual(plan.complexity, 8)
        self.assertGreaterEqual(plan.risk, 6)
        self.assertEqual(plan.agent_profile, "guard_reasoner")
        self.assertEqual(plan.preferred_model, "gpt-5.6")
        self.assertEqual(plan.strategy, "plan_execute_verify")
        self.assertEqual(plan.max_parallel_agents, 1)

    def test_repo_sensitive_change_increases_risk_and_finds_commands(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest run", "build": "vite build", "lint": "eslint ."}}),
                encoding="utf-8",
            )
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            (root / "src").mkdir()
            auth = root / "src" / "auth.ts"
            auth.write_text("export const ok = true;\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            auth.write_text("export const ok = false;\n", encoding="utf-8")

            plan = classify_task("fix this", repo_path=root)
            self.assertGreaterEqual(plan.risk, 3)
            self.assertIn("sensitive_paths_changed", plan.repo_signals)
            self.assertTrue(plan.requires_tests)


if __name__ == "__main__":
    unittest.main()
