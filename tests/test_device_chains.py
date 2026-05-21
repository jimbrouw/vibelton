from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeviceChainManifestTest(unittest.TestCase):
    def test_manifest_has_stage_1_5_targets(self) -> None:
        manifest = json.loads((ROOT / "device_chains.json").read_text(encoding="utf-8"))
        chains = manifest["chains"]
        self.assertEqual(15, len(chains))

        keys = {(item["genre_family"], item["role"]) for item in chains}
        for family in {"house/techno", "hip-hop/lo-fi", "dnb/ukg"}:
            for role in {"kick", "bass", "pad", "lead", "keys"}:
                self.assertIn((family, role), keys)


if __name__ == "__main__":
    unittest.main()
