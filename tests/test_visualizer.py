import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from guard.visualizer import (
    PixelFactory,
    activity_from_state,
    phase_from_state,
    task_kind_from_state,
    task_palette,
    visualizer_command,
)


class VisualizerStateTests(unittest.TestCase):
    def test_visual_phase_takes_priority(self):
        state = {
            "visual": {"phase": "work", "activity": "file_change"},
            "status": "active",
        }
        self.assertEqual(phase_from_state(state), "work")
        self.assertEqual(activity_from_state(state), "file_change")

    def test_old_route_and_execute_states_map_to_new_workflow(self):
        self.assertEqual(phase_from_state({"visual": {"phase": "route"}}), "plan")
        self.assertEqual(phase_from_state({"visual": {"phase": "execute"}}), "work")

    def test_completed_task_becomes_complete(self):
        self.assertEqual(phase_from_state({"status": "completed"}), "complete")

    def test_failed_task_becomes_failed(self):
        self.assertEqual(phase_from_state({"status": "failed"}), "failed")

    def test_task_palette_is_based_on_task_kind_not_model(self):
        ui = {"plan": {"task_kind": "ui"}}
        debugging = {"plan": {"task_kind": "debugging"}}
        self.assertEqual(task_kind_from_state(ui), "ui")
        self.assertNotEqual(task_palette("ui"), task_palette("debugging"))

    def test_compiled_visualizer_is_preferred_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "bin").mkdir()
            binary = root / "bin" / "usage-guard-visualizer.exe"
            binary.write_text("", encoding="utf-8")
            with patch("guard.visualizer.os.name", "nt"):
                command = visualizer_command("task-1", install_root=root)
            self.assertEqual(command, [str(binary), "--task-id", "task-1"])

    def test_visualizer_override_is_supported(self):
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / "custom-viewer.exe"
            binary.write_text("", encoding="utf-8")
            with patch.dict("guard.visualizer.os.environ", {"CODEX_USAGE_GUARD_VISUALIZER": str(binary)}, clear=False):
                command = visualizer_command("task-2", install_root=Path(td))
            self.assertEqual(command, [str(binary), "--task-id", "task-2"])

    def test_pipe_uses_valid_tk_joinstyle_option(self):
        calls = []

        class Canvas:
            def create_line(self, *args, **kwargs):
                calls.append(kwargs)
                if "jointstyle" in kwargs:
                    raise AssertionError("Tk Canvas uses joinstyle, not jointstyle")

            def create_oval(self, *args, **kwargs):
                pass

        factory = PixelFactory.__new__(PixelFactory)
        factory.canvas = Canvas()
        factory._pipe([0, 0, 10, 0, 10, 10])

        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call.get("joinstyle") == "miter" for call in calls))


if __name__ == "__main__":
    unittest.main()
