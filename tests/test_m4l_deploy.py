from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_amxd  # noqa: E402
import deploy_m4l  # noqa: E402


class M4lBuildDeployTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m4l = Path(self.tmp.name) / "m4l"
        shutil.copytree(ROOT / "m4l", self.m4l)

    def test_repo_amxd_is_in_sync_with_maxpat(self) -> None:
        self.assertTrue(build_amxd.in_sync())

    def test_pack_unpack_roundtrip(self) -> None:
        raw = (ROOT / "m4l" / "Vibelton Arranger.maxpat").read_bytes()
        self.assertEqual(raw, build_amxd.unpack(build_amxd.pack(raw)))

    def test_patcher_routes_errors_and_retry(self) -> None:
        patcher = json.loads((ROOT / "m4l" / "Vibelton Arranger.maxpat").read_text())["patcher"]
        texts = {b["box"]["id"]: b["box"].get("text", "") for b in patcher["boxes"]}
        self.assertIn("offline_url", texts["obj-9"])
        self.assertIn("retry", texts["obj-9"])
        ids = {(l["patchline"]["source"][0], l["patchline"]["destination"][0]) for l in patcher["lines"]}
        self.assertIn(("obj-15", "obj-12"), ids)  # prepend loadurl -> jweb
        self.assertIn(("obj-16", "obj-8"), ids)   # retry -> node.script

    def test_node_script_is_saved_the_way_max_saves_it(self) -> None:
        # Max stores node.script as a plain newobj; maxclass "node.script" cannot be created, which leaves the
        # helper un-started and every patchcord to/from it deleted on load.
        patcher = json.loads((ROOT / "m4l" / "Vibelton Arranger.maxpat").read_text())["patcher"]
        box = next(b["box"] for b in patcher["boxes"] if b["box"].get("text", "").startswith("node.script"))
        self.assertEqual("newobj", box["maxclass"])
        self.assertEqual({"autostart", "defer", "node", "npm", "watch"}, set(box["saved_object_attributes"]))

    def test_every_patchcord_end_exists(self) -> None:
        def walk(patcher: dict) -> None:
            ids = {b["box"]["id"] for b in patcher["boxes"]}
            for line in patcher.get("lines", []):
                for end in ("source", "destination"):
                    self.assertIn(line["patchline"][end][0], ids)
            for b in patcher["boxes"]:
                if "patcher" in b["box"]:
                    walk(b["box"]["patcher"])
        walk(json.loads((ROOT / "m4l" / "Vibelton Arranger.maxpat").read_text())["patcher"])

    def test_preflight_clean_for_repo(self) -> None:
        self.assertEqual([], deploy_m4l.preflight(ROOT / "m4l"))

    def test_preflight_blocks_stale_amxd(self) -> None:
        pat = self.m4l / "Vibelton Arranger.maxpat"
        pat.write_text(pat.read_text() + " ")
        self.assertTrue(any("does not match" in p for p in deploy_m4l.preflight(self.m4l)))

    def test_preflight_blocks_missing_referenced_js(self) -> None:
        (self.m4l / "daemon_guard.js").unlink()
        self.assertTrue(any("daemon_guard.js" in p for p in deploy_m4l.preflight(self.m4l)))

    def test_frozen_device_with_different_embedded_js_is_blocked(self) -> None:
        amxd = self.m4l / "Vibelton Arranger.amxd"
        amxd.write_bytes(amxd.read_bytes() + b"dlst" + b"old js contents")
        problems = deploy_m4l.preflight(self.m4l)
        self.assertTrue(any("frozen" in p for p in problems), problems)

    def test_deploy_copies_and_verifies(self) -> None:
        target = Path(self.tmp.name) / "library"
        target.mkdir()
        (target / "daemon_guard.js").write_text("stale")
        self.assertEqual([], deploy_m4l.deploy([target], self.m4l))
        states = {dst.name: state for _, dst, state in deploy_m4l.plan([target], self.m4l)}
        self.assertEqual({"same"}, set(states.values()))

    def test_deploy_refuses_when_preflight_fails(self) -> None:
        (self.m4l / "daemon_guard.js").unlink()
        target = Path(self.tmp.name) / "library"
        self.assertTrue(deploy_m4l.deploy([target], self.m4l))
        self.assertFalse(target.exists())

    def stale_library(self) -> tuple[Path, Path, Path]:
        base = Path(self.tmp.name) / "Max Audio Effect"
        (base / "m4l").mkdir(parents=True)
        (base / "daemon_guard.js").write_text("stale")
        (base / "autoresize.js").write_text("stale")
        (base / "Some Other.adv").write_text("keep")
        (base / "m4l" / "Vibelton Arranger.amxd").write_bytes(b"device")
        (base / "m4l" / "daemon_guard.js").write_text("in use")
        return base, base / "m4l", base / "daemon_guard.js"

    def test_clean_stale_dry_run_lists_and_changes_nothing(self) -> None:
        base, device_dir, stray = self.stale_library()
        found = deploy_m4l.stale_support_files([base, device_dir])
        self.assertEqual({base / "daemon_guard.js", base / "autoresize.js"}, set(found))
        self.assertEqual(0, deploy_m4l.main(["--clean-stale", "--target", str(base), "--target", str(device_dir)]))
        self.assertTrue(stray.exists() and (base / "autoresize.js").exists())

    def test_clean_stale_apply_removes_only_unused_support_js(self) -> None:
        base, device_dir, stray = self.stale_library()
        self.assertEqual(0, deploy_m4l.main(["--clean-stale", "--apply", "--target", str(base), "--target", str(device_dir)]))
        self.assertFalse(stray.exists() or (base / "autoresize.js").exists())
        self.assertTrue((base / "Some Other.adv").exists())
        self.assertTrue((device_dir / "daemon_guard.js").exists() and (device_dir / "Vibelton Arranger.amxd").exists())


if __name__ == "__main__":
    unittest.main()
