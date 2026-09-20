import io
import unittest

from guard.hud import HUDState, AnimatedHUD, render_hud, visual_snapshot


class HudTests(unittest.TestCase):
    def test_render_hud_is_compact_and_model_neutral(self):
        text = render_hud(
            phase="work",
            action_used=2,
            action_limit=10,
            model_turns_used=1,
            model_turns_limit=4,
            tokens=4321,
            status="active",
        )
        self.assertIn("4,321", text)
        self.assertIn("actions", text)
        self.assertIn("turns", text)
        self.assertNotIn("luna", text.lower())
        self.assertNotIn("terra", text.lower())
        self.assertLessEqual(len(text.splitlines()), 6)

    def test_non_tty_hud_does_not_emit_animation(self):
        stream = io.StringIO()
        hud = AnimatedHUD(HUDState(), stream=stream, enabled=False)
        hud.start()
        hud.stop(final_status="completed")
        self.assertEqual(stream.getvalue(), "")

    def test_visual_snapshot_uses_real_task_phase_and_budget(self):
        state = {
            "status": "active",
            "plan": {
                "max_actions": 10,
                "max_model_turns": 4,
            },
            "counters": {"actions": 3, "model_turns": 1},
            "visual": {"phase": "verify"},
            "usage": {"delta": {"tokens_delta": 9876}},
        }
        text = visual_snapshot(state)
        self.assertIn("9,876", text)
        self.assertIn("3/10", text)


if __name__ == "__main__":
    unittest.main()
