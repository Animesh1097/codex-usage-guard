import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from guard.executor import build_exec_command, decide_enforcement, enforce_task, parse_thread_id
from guard.state import load_task


class ExecutorTests(unittest.TestCase):
    def test_requires_worker_when_model_differs(self):
        decision = decide_enforcement(
            coordinator_model="gpt-5.6-luna",
            coordinator_reasoning="low",
            requested_model="gpt-5.6-terra",
            requested_reasoning="medium",
        )
        self.assertTrue(decision.requires_worker)
        self.assertIn("model differs", decision.reason)

    def test_requires_worker_when_reasoning_differs(self):
        decision = decide_enforcement(
            coordinator_model="gpt-5.6-terra",
            coordinator_reasoning="low",
            requested_model="gpt-5.6-terra",
            requested_reasoning="medium",
        )
        self.assertTrue(decision.requires_worker)
        self.assertIn("reasoning differs", decision.reason)

    def test_parent_match_avoids_nested_worker(self):
        decision = decide_enforcement(
            coordinator_model="gpt-5.6-terra",
            coordinator_reasoning="medium",
            requested_model="gpt-5.6-terra",
            requested_reasoning="medium",
        )
        self.assertFalse(decision.requires_worker)

    def test_exec_command_pins_model_reasoning_and_workspace_sandbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            output = root / "last.txt"
            command = build_exec_command(
                task_id="abc",
                repo_root=root,
                model="gpt-5.6-terra",
                reasoning_effort="medium",
                prompt="fix it",
                output_file=output,
                codex_executable="codex",
            )
            self.assertEqual(command[:2], ["codex", "exec"])
            self.assertIn("--model", command)
            self.assertIn("gpt-5.6-terra", command)
            self.assertIn('model_reasoning_effort="medium"', command)
            self.assertIn("--sandbox", command)
            self.assertIn("workspace-write", command)
            self.assertIn('approval_policy="never"', command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_parse_thread_id_from_jsonl(self):
        output = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-123"}),
                json.dumps({"type": "turn.started"}),
            ]
        )
        self.assertEqual(parse_thread_id(output), "thread-123")

    def test_enforce_task_uses_and_verifies_pinned_worker(self):
        with tempfile.TemporaryDirectory() as state_td, tempfile.TemporaryDirectory() as repo_td:
            state_root = Path(state_td)
            repo_root = Path(repo_td)
            (repo_root / ".git").mkdir()
            state = {
                "version": 4,
                "task_id": "task123",
                "objective": "fix the form",
                "repo_root": str(repo_root),
                "status": "active",
                "plan": {
                    "preferred_model": "gpt-5.6-terra",
                    "reasoning_effort": "medium",
                    "task_kind": "ui",
                    "context_budget_tokens": 14000,
                    "max_actions": 10,
                    "max_model_turns": 4,
                    "max_retries": 2,
                    "skill_refs": ["references/ui-ux.md"],
                },
                "repo": {
                    "test_command": None,
                    "build_command": None,
                    "lint_command": None,
                    "typecheck_command": None,
                },
                "file_hashes": {},
                "counters": {"actions": 0, "model_turns": 0, "retries": 0},
                "events": [],
                "completed": [],
                "unresolved": [],
                "usage": {"baseline": {}, "finish": None, "delta": None},
                "execution": None,
            }
            (state_root / "task123.json").write_text(json.dumps(state), encoding="utf-8")

            def fake_runner(command, **kwargs):
                output_index = command.index("--output-last-message") + 1
                Path(command[output_index]).write_text("worker finished", encoding="utf-8")
                stdout = json.dumps({"type": "thread.started", "thread_id": "worker-1"}) + "\n"
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

            worker_usage = {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
                "thread_id": "worker-1",
                "tokens_total": 4321,
                "token_breakdown": {"total_tokens": 4321},
            }
            with patch(
                "guard.executor._coordinator_snapshot",
                return_value={"model": "gpt-5.6-luna", "reasoning_effort": "low"},
            ), patch("guard.executor.usage_snapshot", return_value=worker_usage):
                result = enforce_task(
                    "task123",
                    root=state_root,
                    runner=fake_runner,
                    sleep_fn=lambda _: None,
                    codex_executable="codex",
                )

            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["effective_model"], "gpt-5.6-terra")
            self.assertEqual(result["final_message"], "worker finished")
            loaded = load_task("task123", root=state_root)
            self.assertEqual(loaded["counters"]["model_turns"], 1)
            self.assertEqual(loaded["execution"]["worker_thread_id"], "worker-1")


if __name__ == "__main__":
    unittest.main()
