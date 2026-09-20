import io
import unittest

from guard.hud import HUDState, AnimatedHUD, render_hud, visual_snapshot


class HudTests(unittest.TestCase):
    def test_render_hud_is_compact_and_visual(self):
        text = render_hud(
            phase="route",
            coordinator_model="gpt-5.6-luna",
            requested_model="gpt-5.6-terra",
            reasoning="medium",
            action_used=2,
            action_limit=10,
            model_turns_used=1,
            model_turns_limit=4,
            tokens=4321,
            status="verified",
        )
        self.assertIn("luna", text)
        self.assertIn("terra", text)
        self.assertIn("4,321", text)
        self.assertIn("█", text)
        self.assertLessEqual(len(text.splitlines()), 6)

    def test_non_tty_hud_does_not_emit_animation(self):
        stream = io.StringIO()
        hud = AnimatedHUD(HUDState(), stream=stream, enabled=False)
        hud.start()
        hud.stop(final_status="verified")
        self.assertEqual(stream.getvalue(), "")

    def test_visual_snapshot_uses_worker_route_and_budget(self):
        state = {
            "status": "active",
            "plan": {
                "preferred_model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
                "max_actions": 10,
                "max_model_turns": 4,
            },
            "counters": {"actions": 3, "model_turns": 1},
            "execution": {
                "status": "verified",
                "coordinator_model": "gpt-5.6-luna",
                "requested_model": "gpt-5.6-terra",
                "requested_reasoning": "medium",
                "effective_reasoning": "medium",
                "worker_usage": {"tokens_total": 9876},
            },
        }
        text = visual_snapshot(state)
        self.assertIn("luna", text)
        self.assertIn("terra", text)
        self.assertIn("9,876", text)


if __name__ == "__main__":
    unittest.main()
