"""A6: approved sample / MIDI roots are visible at startup, config-driven, and enforced."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import midi_library, samples


class ApprovedRootsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / '.vibelton').mkdir()

    def write_config(self, **config) -> None:
        (self.home / '.vibelton' / 'config.json').write_text(json.dumps(config))

    def test_configured_roots_are_read_from_config(self) -> None:
        extra = self.home / 'my samples'
        self.write_config(extra_sample_roots=[str(extra)], midi_library_roots=[str(self.home / 'my midi')])
        with patch('pathlib.Path.home', return_value=self.home):
            self.assertIn(extra, samples._configured_sample_roots())
            self.assertIn(str(self.home / 'my midi'), midi_library.configured_midi_roots())

    def test_startup_lines_list_every_root(self) -> None:
        from vibelton import server   # imported here: importing the server loads .env.local into os.environ
        text = '\n'.join(server.approved_roots_lines())
        for root in samples.approved_roots():
            self.assertIn(str(root), text)
        self.assertIn('config.json', text)

    def test_file_outside_all_roots_is_refused(self) -> None:
        outside = self.home / 'elsewhere.wav'
        outside.write_bytes(b'RIFF')
        with self.assertRaises(ValueError):
            samples.source_path(str(outside))

    def test_file_inside_a_configured_root_is_accepted(self) -> None:
        root = self.home / 'approved'
        root.mkdir()
        wav = root / 'a.wav'
        wav.write_bytes(b'RIFF')
        with patch.object(samples, 'EXTRA_SAMPLE_ROOTS', (root,)):
            self.assertEqual(wav.resolve(), samples.source_path(str(wav)))


if __name__ == '__main__':
    unittest.main()
