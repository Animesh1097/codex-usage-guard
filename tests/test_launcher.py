import tempfile
import unittest
from pathlib import Path

from guard.launcher import build_codex_command, preview_launch, resolve_launch_input


class LauncherTests(unittest.TestCase):
    def test_build_command_pins_repo_model_and_reasoning(self):
        repo_root = r"C:\Projects\demo"
        command = build_codex_command(
            task_id="abc123",
            task="fix the seller form",
            repo_root=repo_root,
            model="gpt-5.6-terra",
            reasoning_effort="medium",
            codex_executable="codex",
        )
        self.assertEqual(command[:2], ["codex", "--cd"])
        self.assertIn(repo_root, command)
        self.assertIn("--model", command)
        self.assertIn("gpt-5.6-terra", command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn("abc123", command[-1])
        self.assertIn("Do not create a second guarded task", command[-1])

    def test_preview_routes_without_creating_a_codex_session(self):
        preview = preview_launch("change the footer phone number", repo="/definitely/not/a/repo")
        self.assertEqual(preview["preferred_model"], "gpt-5.6-luna")
        self.assertEqual(preview["reasoning_effort"], "low")
        self.assertEqual(preview["agent_profile"], "guard_fast")

    def test_existing_directory_can_be_first_argument(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root, task = resolve_launch_input([td, "fix the form"])
            self.assertEqual(repo_root, Path(td).resolve())
            self.assertEqual(task, "fix the form")


if __name__ == "__main__":
    unittest.main()
