import unittest

from guard.compressor import compress_git_diff, compress_test_output, estimate_tokens


class CompressorTests(unittest.TestCase):
    def test_test_output_keeps_failure_and_reduces_size(self):
        noisy = "\n".join(
            [f"ok test_{i}" for i in range(200)]
            + ["FAIL test_payment", "AssertionError: expected 200 received 500"]
            + [f"noise {i}" for i in range(100)]
        )
        compact = compress_test_output(noisy)
        self.assertIn("FAIL test_payment", compact)
        self.assertIn("AssertionError", compact)
        self.assertLess(len(compact), len(noisy))
        self.assertLess(estimate_tokens(compact), estimate_tokens(noisy))

    def test_git_diff_keeps_changed_lines(self):
        body = ["diff --git a/a.py b/a.py", "--- a/a.py", "+++ b/a.py", "@@ -1,3 +1,3 @@"]
        body += [" unchanged line"] * 200
        body += ["-old_value", "+new_value"]
        compact = compress_git_diff("\n".join(body))
        self.assertIn("-old_value", compact)
        self.assertIn("+new_value", compact)
        self.assertNotIn(" unchanged line", compact)


if __name__ == "__main__":
    unittest.main()
