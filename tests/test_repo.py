import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from guard.repo import changed_file_hashes, inspect_repo


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)


class RepoTests(unittest.TestCase):
    def test_detects_js_commands_and_sensitive_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest run", "build": "vite build", "typecheck": "tsc --noEmit"}}),
                encoding="utf-8",
            )
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
            (root / "src").mkdir()
            auth = root / "src" / "auth.ts"
            auth.write_text("export const x = 1;\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            auth.write_text("export const x = 2;\n", encoding="utf-8")

            profile = inspect_repo(root)
            self.assertEqual(profile.package_manager, "pnpm")
            self.assertEqual(profile.test_command, "pnpm test")
            self.assertEqual(profile.build_command, "pnpm build")
            self.assertEqual(profile.typecheck_command, "pnpm typecheck")
            self.assertIn("src/auth.ts", profile.sensitive_files)
            self.assertIn("sensitive_paths_changed", profile.signals)
            self.assertIn("src/auth.ts", changed_file_hashes(profile))

    def test_docs_only_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            readme = root / "README.md"
            readme.write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            readme.write_text("two\n", encoding="utf-8")
            profile = inspect_repo(root)
            self.assertTrue(profile.docs_only)
            self.assertIn("docs_only_change", profile.signals)


if __name__ == "__main__":
    unittest.main()
