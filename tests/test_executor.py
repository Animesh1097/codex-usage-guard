import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from guard.executor import build_exec_command, decide_enforcement, parse_thread_id


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


if __name__ == "__main__":
    unittest.main()
