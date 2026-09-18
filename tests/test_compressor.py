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

    def test_git_diff_keeps_changed_lines_and_small_context(self):
        body = [
            "diff --git a/a.py b/a.py",
            "index 1111111..2222222 100644",
            "--- a/a.py",
            "+++ b/a.py",
            "@@ -1,205 +1,205 @@",
        ]
        body += [f" context_{i}" for i in range(100)]
        body += ["-old_value", "+new_value"]
        body += [f" trailing_{i}" for i in range(100)]
        compact = compress_git_diff("\n".join(body), context_radius=2)
        self.assertIn("-old_value", compact)
        self.assertIn("+new_value", compact)
        self.assertIn(" context_99", compact)
        self.assertIn(" trailing_0", compact)
        self.assertNotIn(" context_0", compact)
        self.assertLess(len(compact.splitlines()), 30)

    def test_ansi_noise_is_removed(self):
        noisy = "\x1b[31mERROR\x1b[0m something failed\n" + "\n".join(["noise"] * 100)
        compact = compress_test_output(noisy)
        self.assertIn("ERROR", compact)
        self.assertNotIn("\x1b", compact)


if __name__ == "__main__":
    unittest.main()
