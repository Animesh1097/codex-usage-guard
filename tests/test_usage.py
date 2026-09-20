import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from guard.usage import usage_delta, usage_snapshot


class UsageTests(unittest.TestCase):
    def _home(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        td = tempfile.TemporaryDirectory()
        home = Path(td.name)
        db = sqlite3.connect(home / "state_5.sqlite")
        db.execute(
            "CREATE TABLE threads (id TEXT PRIMARY KEY, model TEXT, reasoning_effort TEXT, tokens_used INTEGER, cwd TEXT, updated_at INTEGER)"
        )
        db.execute(
            "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?)",
            ("thread-1", "gpt-test", "medium", 1000, "/repo", 10),
        )
        db.commit()
        db.close()
        sessions = home / "sessions" / "2026" / "09"
        sessions.mkdir(parents=True)
        payload = {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 800,
                        "cached_input_tokens": 400,
                        "output_tokens": 150,
                        "reasoning_output_tokens": 50,
                        "total_tokens": 1000,
                    },
                    "model_context_window": 100000,
                },
                "rate_limits": {
                    "primary": {"used_percent": 20.0, "window_minutes": 300, "resets_at": 1},
                    "secondary": {"used_percent": 5.0, "window_minutes": 10080, "resets_at": 2},
                    "plan_type": "plus",
                },
            },
        }
        (sessions / "rollout-thread-1.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return td, home

    def test_snapshot_reads_thread_and_rate_limits_locally(self):
        td, home = self._home()
        try:
            snap = usage_snapshot(thread_id="thread-1", home=home)
            self.assertTrue(snap["available"])
            self.assertEqual(snap["tokens_total"], 1000)
            self.assertEqual(snap["model"], "gpt-test")
            self.assertEqual(snap["reasoning_effort"], "medium")
            self.assertEqual(snap["rate_limits"]["primary"]["used_percent"], 20.0)
            self.assertEqual(snap["rate_limits"]["secondary"]["window_minutes"], 10080)
            self.assertEqual(snap["token_breakdown"]["cached_input_tokens"], 400)
            self.assertEqual(snap["tokens_global_total"], 1000)
        finally:
            td.cleanup()

    def test_delta_requires_same_thread_for_tokens(self):
        before = {
            "thread_id": "a",
            "tokens_total": 100,
            "rate_limits": {"primary": {"used_percent": 10.0}, "secondary": {"used_percent": 20.0}},
        }
        after = {
            "thread_id": "a",
            "tokens_total": 460,
            "rate_limits": {"primary": {"used_percent": 13.0}, "secondary": {"used_percent": 21.0}},
        }
        delta = usage_delta(before, after)
        self.assertEqual(delta["tokens_delta"], 360)
        self.assertEqual(delta["primary_used_percent_delta"], 3.0)
        self.assertEqual(delta["secondary_used_percent_delta"], 1.0)

        other = dict(
            after,
            thread_id="b",
            tokens_global_total=800,
        )
        before_global = dict(before, tokens_global_total=500)
        fallback = usage_delta(before_global, other)
        self.assertEqual(fallback["tokens_delta"], 300)
        self.assertEqual(fallback["token_delta_scope"], "global-approximate")


if __name__ == "__main__":
    unittest.main()
