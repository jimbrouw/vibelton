from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("node"), "node is required")
class DaemonGuardNodeTests(unittest.TestCase):
    def test_node_suite(self) -> None:
        res = subprocess.run(["node", "--test", str(ROOT / "tests" / "daemon_guard.test.cjs")],
                             cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(shutil.which("node"), "node is required")
class WebScriptSyntaxTests(unittest.TestCase):
    def test_every_web_script_parses(self) -> None:
        for script in sorted((ROOT / "web").glob("*.js")) + [ROOT / "m4l" / "daemon_guard.js", ROOT / "m4l" / "autoresize.js"]:
            res = subprocess.run(["node", "--check", str(script)], capture_output=True, text=True, timeout=30)
            self.assertEqual(0, res.returncode, f"{script.name}: {res.stderr}")
