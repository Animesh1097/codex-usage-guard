import subprocess
import tempfile
import unittest
from pathlib import Path

from guard.budget import budget_status
from guard.context import make_capsule
from guard.repo import inspect_repo
from guard.state import load_task, record_action, start_task


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    file = root / "app.py"
    file.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


class StateTests(unittest.TestCase):
    def test_budget_is_enforced(self):
        with tempfile.TemporaryDirectory() as repo_td, tempfile.TemporaryDirectory() as state_td:
            root = Path(repo_td)
            state_root = Path(state_td)
            init_repo(root)
            profile = inspect_repo(root)
            plan = {
                "max_actions": 2,
                "max_model_turns": 1,
                "max_retries": 1,
                "task_kind": "general",
                "strategy": "single_turn",
                "agent_profile": "guard_fast",
                "reasoning_effort": "low",
            }
            state = start_task("change x", plan, profile, root=state_root)
            task_id = state["task_id"]

            first = record_action(task_id, action="inspect", kind="deterministic", root=state_root)
            self.assertTrue(first["recorded"])
            second = record_action(task_id, action="edit", kind="model", root=state_root)
            self.assertTrue(second["recorded"])
            third = record_action(task_id, action="review", kind="model", root=state_root)
            self.assertFalse(third["recorded"])

            loaded = load_task(task_id, root=state_root)
            status = budget_status(loaded)
            self.assertFalse(status["may_continue"])
            self.assertIn(loaded["visual"]["phase"], {"execute", "verify"})

    def test_capsule_tracks_hash_change_without_full_history(self):
        with tempfile.TemporaryDirectory() as repo_td, tempfile.TemporaryDirectory() as state_td:
            root = Path(repo_td)
            state_root = Path(state_td)
            init_repo(root)
            target = root / "app.py"
            target.write_text("x = 2\n", encoding="utf-8")
            profile = inspect_repo(root)
            plan = {
                "max_actions": 4,
                "max_model_turns": 2,
                "max_retries": 1,
                "task_kind": "debugging",
                "strategy": "single_agent",
                "agent_profile": "guard_worker",
                "reasoning_effort": "medium",
            }
            state = start_task("fix app", plan, profile, root=state_root)
            task_id = state["task_id"]
            record_action(task_id, action="inspect", outcome="pass", root=state_root)

            target.write_text("x = 3\n", encoding="utf-8")
            capsule = make_capsule(task_id, root=state_root)
            self.assertIn("app.py", capsule["hot"]["changed_since_snapshot"])
            self.assertEqual(capsule["cold"]["full_event_count"], 1)
            self.assertIn("inspect", capsule["warm"]["completed"])


if __name__ == "__main__":
    unittest.main()
