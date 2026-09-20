import unittest

from guard.visualizer import PixelFactory, activity_from_state, phase_from_state, task_kind_from_state, task_palette


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
