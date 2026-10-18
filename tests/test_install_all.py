from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install_all  # noqa: E402
import deploy_m4l  # noqa: E402


@unittest.skipUnless(sys.platform == "darwin", "the installer targets macOS")
class InstallAllTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / "Music" / "Ableton" / "User Library").mkdir(parents=True)
        self.lines: list[str] = []

    def run_install(self, apply: bool) -> int:
        return install_all.run(self.home, apply, python_path="/usr/bin/fake-python", out=self.lines.append)

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.home)) for p in self.home.rglob("*") if p.is_file())

    def test_a_dry_run_changes_nothing(self) -> None:
        self.assertEqual(0, self.run_install(False))
        self.assertEqual([], self.files())
        self.assertTrue(any("Dry run" in line for line in self.lines))

    def test_apply_installs_everything_and_verifies_the_device(self) -> None:
        self.assertEqual(0, self.run_install(True), self.lines)
        library = install_all.library_for(self.home)
        self.assertTrue((library / "Remote Scripts" / "Vibelton" / "Vibelton.py").is_file())
        folder = install_all.device_folder(library)
        for name in (deploy_m4l.DEVICE, *deploy_m4l.SUPPORT_JS):
            self.assertEqual(deploy_m4l.sha(ROOT / "m4l" / name), deploy_m4l.sha(folder / name), name)
        config = json.loads((self.home / ".vibelton" / "config.json").read_text())
        self.assertEqual({"repo_path": str(ROOT), "python_path": "/usr/bin/fake-python"}, config)
        self.assertTrue(any("Quit and reopen Ableton Live" in line for line in self.lines))

    def test_an_existing_config_is_never_overwritten(self) -> None:
        (self.home / ".vibelton").mkdir()
        (self.home / ".vibelton" / "config.json").write_text('{"port": 9000}')
        self.assertEqual(0, self.run_install(True))
        self.assertEqual({"port": 9000}, json.loads((self.home / ".vibelton" / "config.json").read_text()))

    def test_running_it_twice_is_harmless(self) -> None:
        self.assertEqual(0, self.run_install(True))
        before = self.files()
        self.assertEqual(0, self.run_install(True))
        self.assertEqual(before, self.files())

    def test_an_existing_device_copy_is_updated_in_place_not_duplicated(self) -> None:
        library = install_all.library_for(self.home)
        old = install_all.device_folder(library) / "m4l"
        old.mkdir(parents=True)
        (old / "Vibelton Arranger.amxd").write_bytes(b"old")
        self.assertEqual(0, self.run_install(True))
        self.assertEqual(deploy_m4l.sha(ROOT / "m4l" / "Vibelton Arranger.amxd"), deploy_m4l.sha(old / "Vibelton Arranger.amxd"))
        self.assertFalse((install_all.device_folder(library) / "Vibelton Arranger.amxd").exists())

    def test_old_python_and_missing_live_are_refused_before_anything_changes(self) -> None:
        self.assertTrue(any("3.11" in p for p in install_all.preflight(self.home, version=(3, 10, 0))))
        empty = Path(self.tmp.name) / "nolive"
        empty.mkdir()
        self.assertTrue(any("User Library was not found" in p for p in install_all.preflight(empty)))
        self.assertEqual(1, install_all.run(empty, True, out=self.lines.append))
        self.assertEqual([], sorted(p.name for p in empty.iterdir()))


if __name__ == "__main__":
    unittest.main()
