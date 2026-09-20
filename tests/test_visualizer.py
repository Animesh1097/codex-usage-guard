import unittest

from guard.visualizer import PixelFactory, activity_from_state, model_palette, phase_from_state


class VisualizerStateTests(unittest.TestCase):
    def test_visual_phase_takes_priority(self):
        state = {
            "visual": {"phase": "execute", "activity": "file_change"},
            "execution": {"status": "pending-worker"},
        }
        self.assertEqual(phase_from_state(state), "execute")
        self.assertEqual(activity_from_state(state), "file_change")

    def test_verified_execution_becomes_complete(self):
        state = {"execution": {"status": "verified"}}
        self.assertEqual(phase_from_state(state), "complete")

    def test_failed_execution_becomes_failed(self):
        state = {"execution": {"status": "model-mismatch"}}
        self.assertEqual(phase_from_state(state), "failed")

    def test_model_palettes_are_distinct(self):
        self.assertNotEqual(model_palette("gpt-5.6-luna"), model_palette("gpt-5.6-terra"))
        self.assertNotEqual(model_palette("gpt-5.6-terra"), model_palette("gpt-5.6"))

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
