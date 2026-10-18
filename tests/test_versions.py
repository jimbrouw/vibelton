from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from vibelton import versions

REAL_ROOT = Path(__file__).resolve().parent.parent


class VersionWarningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root, self.lib = base / "repo", base / "lib"
        (self.root / "ableton_remote_script" / "Vibelton").mkdir(parents=True)
        (self.root / "m4l").mkdir()
        (self.root / "vibelton").mkdir()
        (self.root / "vibelton" / "server.py").write_text("x = 1\n")
        (self.root / "ableton_remote_script" / "Vibelton" / "Vibelton.py").write_text('BRIDGE_VERSION = "b-2"\n')
        (self.root / "ableton_remote_script" / "Vibelton" / "helper.py").write_text("y = 2\n")
        (self.root / "m4l" / "daemon_guard.js").write_text("const DEVICE_VERSION = 'd-2';\n")
        (self.root / "m4l" / "autoresize.js").write_text("// resize\n")
        (self.root / "m4l" / "Vibelton Arranger.amxd").write_bytes(b"amxd-bytes")
        self.install_bridge()
        self.install_device()
        self.startup = versions.code_hash(self.root)

    def install_bridge(self) -> None:
        target = versions.remote_script_dir(self.lib)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.root / "ableton_remote_script" / "Vibelton", target)

    def install_device(self) -> None:
        for directory in versions.device_dirs(self.lib)[:1]:
            directory.mkdir(parents=True, exist_ok=True)
            for name in versions.DEVICE_FILES:
                shutil.copy2(self.root / "m4l" / name, directory / name)

    def collect(self, running="b-2", loaded=None, startup=None) -> dict:
        return versions.collect({"bridge_version": running}, root=self.root, library=self.lib,
                                loaded=loaded, startup_hash=startup or self.startup)

    def codes(self, result) -> list[str]:
        return [w["code"] for w in result["warnings"]]

    def test_everything_current_has_no_warnings(self) -> None:
        result = self.collect(loaded={"device_version": "d-2"})
        self.assertEqual([], result["warnings"])
        self.assertTrue(result["ok"])
        self.assertEqual(("b-2", "b-2", "b-2"), (result["bridge"]["running"], result["bridge"]["installed"], result["bridge"]["repo"]))
        self.assertEqual("d-2", result["device"]["repo"])

    def test_installed_remote_script_older_than_the_repo(self) -> None:
        (self.root / "ableton_remote_script" / "Vibelton" / "helper.py").write_text("y = 3\n")  # same version string, new code
        result = self.collect()
        self.assertEqual(["bridge_installed_stale"], self.codes(result))
        self.assertIn("install_remote_script.py", result["warnings"][0]["fix"])
        self.assertIn("restart Live", result["warnings"][0]["fix"])

    def test_live_running_a_different_script_than_installed(self) -> None:
        result = self.collect(running="b-1")
        self.assertEqual(["bridge_running_stale"], self.codes(result))
        self.assertIn("Restart Live", result["warnings"][0]["fix"])

    def test_missing_remote_script(self) -> None:
        shutil.rmtree(versions.remote_script_dir(self.lib))
        self.assertIn("bridge_not_installed", self.codes(self.collect()))

    def test_stale_library_device_names_the_files_and_the_fix(self) -> None:
        (versions.device_dirs(self.lib)[0] / "daemon_guard.js").write_text("const DEVICE_VERSION = 'd-1';\n")
        result = self.collect()
        self.assertEqual(["device_library_stale"], self.codes(result))
        self.assertIn("daemon_guard.js", result["warnings"][0]["message"])
        self.assertIn("deploy_m4l.py --apply", result["warnings"][0]["fix"])
        self.assertEqual("d-1", result["device"]["library"][0]["version"])

    def test_js_files_in_a_folder_without_the_device_are_not_a_warning(self) -> None:
        # The device lives in m4l/; stale JS left in the parent folder is unused, not a stale device.
        extra = versions.device_dirs(self.lib)[1]
        extra.mkdir(parents=True)
        (extra / "daemon_guard.js").write_text("const DEVICE_VERSION = 'd-0';\n")
        result = self.collect()
        self.assertEqual([], self.codes(result))
        self.assertEqual(1, len(result["device"]["library"]))

    def test_device_not_in_the_library(self) -> None:
        shutil.rmtree(versions.device_dirs(self.lib)[0])
        self.assertEqual(["device_not_in_library"], self.codes(self.collect()))

    def test_device_loaded_in_live_older_than_the_repo(self) -> None:
        result = self.collect(loaded={"device_version": "d-1"})
        self.assertEqual(["device_loaded_stale"], self.codes(result))
        self.assertIn("drag it in again", result["warnings"][0]["fix"])

    def test_no_report_from_the_device_is_not_a_warning(self) -> None:
        self.assertNotIn("device_loaded_stale", self.codes(self.collect(loaded=None)))

    def test_server_started_before_the_code_changed(self) -> None:
        (self.root / "vibelton" / "server.py").write_text("x = 2\n")
        result = self.collect()
        self.assertEqual(["server_stale"], self.codes(result))
        self.assertIn("Restart the server", result["warnings"][0]["fix"])

    def test_caches_and_ds_store_do_not_count_as_changes(self) -> None:
        installed = versions.remote_script_dir(self.lib)
        (installed / "__pycache__").mkdir()
        (installed / "__pycache__" / "Vibelton.cpython-314.pyc").write_bytes(b"junk")
        (installed / ".DS_Store").write_bytes(b"junk")
        self.assertEqual([], self.collect()["warnings"])

    def test_several_problems_are_all_reported(self) -> None:
        (versions.device_dirs(self.lib)[0] / "autoresize.js").write_text("// old\n")
        result = self.collect(running="b-1", loaded={"device_version": "d-1"})
        self.assertEqual({"bridge_running_stale", "device_library_stale", "device_loaded_stale"}, set(self.codes(result)))
        for warning in result["warnings"]:
            self.assertTrue(warning["message"] and warning["fix"])

    def test_record_device_validates(self) -> None:
        self.assertEqual("d-9", versions.record_device({"device_version": "d-9"})["device_version"])
        for bad in ({}, {"device_version": ""}, {"device_version": 5}, {"device_version": "x" * 200}):
            with self.assertRaises(ValueError):
                versions.record_device(bad)


class RepoConsistencyTests(unittest.TestCase):
    def test_repo_versions_are_defined(self) -> None:
        self.assertTrue(versions.repo_bridge_version(REAL_ROOT))
        self.assertTrue(versions.repo_device_version(REAL_ROOT))

    @unittest.skipUnless(shutil.which("node"), "node is required")
    def test_the_guards_constant_is_what_the_server_compares_against(self) -> None:
        out = subprocess.run(["node", "-e", 'console.log(require("./m4l/daemon_guard.js").DEVICE_VERSION)'],
                             cwd=str(REAL_ROOT), capture_output=True, text=True, timeout=30)
        self.assertEqual(versions.repo_device_version(REAL_ROOT), out.stdout.strip().splitlines()[0])


if __name__ == "__main__":
    unittest.main()
