from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelton import production
from vibelton import queue


class ArrangerCompanionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        
        patcher = patch('vibelton.production.ROOT', self.root / 'production')
        patcher.start()
        self.addCleanup(patcher.stop)
        
        patcher = patch('vibelton.queue.QUEUE_DIR', self.root / 'queue')
        patcher.start()
        self.addCleanup(patcher.stop)

        self.enqueued: list[dict] = []
        def enqueue(actions, source):
            self.enqueued.append({'actions': actions, 'source': source})
            return {'id': 'cmd-%d' % len(self.enqueued)}
        patcher = patch.object(production.queue, 'enqueue', side_effect=enqueue)
        patcher.start()
        self.addCleanup(patcher.stop)

        # 16-bar loop setup for 4 stems
        self.fp_kick = 'k' * 64
        self.fp_bass = 'b' * 64
        self.fp_chords = 'c' * 64
        self.fp_hats = 'h' * 64

        self.state = {
            'connected': True,
            'updated_at': time.time(),
            'capabilities': ['production_v1', 'arrangement_copy_v2'],
            'session_id': 'arranger-test-session',
            'tempo': 124.0,
            'metre': [4, 4],
            'arrangement_readable': True,
            'arrangement_end': 64.0,
            'set_path': '/path/to/MyTrack_vibelton-working-copy.als',
            'production': {
                'schema_version': 'vibelton.production-project-state/v1',
                'session_id': 'arranger-test-session',
                'revision': 'rev-arr-1',
                'set_path': '/Sets/shape vibelton-working-copy.als',
                'tempo': 124.0,
                'metre': [4, 4],
                'tracks': [
                    {
                        'id': 'trk-kick', 'name': '1-Kick', 'type': 'midi',
                        'mixer': {'volume': 0.85, 'pan': 0.0, 'sends': [0.0]},
                        'devices': [], 'routing': 'Main',
                        'arrangement_clips': [
                            {'name': 'Kick Loop', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0, 'fingerprint': self.fp_kick}
                        ],
                        'session_clips': []
                    },
                    {
                        'id': 'trk-bass', 'name': '2-Bass', 'type': 'midi',
                        'mixer': {'volume': 0.8, 'pan': 0.0, 'sends': [0.0]},
                        'devices': [], 'routing': 'Main',
                        'arrangement_clips': [
                            {'name': 'Bass Loop', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0, 'fingerprint': self.fp_bass}
                        ],
                        'session_clips': []
                    },
                    {
                        'id': 'trk-hats', 'name': '3-Hats', 'type': 'midi',
                        'mixer': {'volume': 0.7, 'pan': 0.0, 'sends': [0.0]},
                        'devices': [], 'routing': 'Main',
                        'arrangement_clips': [
                            {'name': 'Hats Loop', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0, 'fingerprint': self.fp_hats}
                        ],
                        'session_clips': []
                    },
                    {
                        'id': 'trk-chords', 'name': '4-Chords', 'type': 'midi',
                        'mixer': {'volume': 0.75, 'pan': 0.0, 'sends': [0.0]},
                        'devices': [], 'routing': 'Main',
                        'arrangement_clips': [
                            {'name': 'Chords Loop', 'start_beat': 0.0, 'end_beat': 64.0, 'length': 64.0, 'fingerprint': self.fp_chords}
                        ],
                        'session_clips': []
                    }
                ]
            }
        }
        patcher = patch.object(production.queue, 'current_state', side_effect=lambda: self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_maxpat_device_structure(self) -> None:
        """Verify the Max for Live device patcher meets all architecture requirements."""
        maxpat_path = Path(__file__).resolve().parent.parent / 'm4l' / 'Vibelton Arranger.maxpat'
        self.assertTrue(maxpat_path.is_file(), 'Vibelton Arranger.maxpat must exist')
        data = json.loads(maxpat_path.read_text(encoding='utf-8'))
        patcher = data.get('patcher', {})

        self.assertEqual(1, patcher.get('openinpresentation'))
        self.assertEqual(750.0, patcher.get('devicewidth'))

        boxes = patcher.get('boxes', [])
        box_texts = [b.get('box', {}).get('text', '') for b in boxes]
        box_classes = [b.get('box', {}).get('maxclass', '') for b in boxes]

        self.assertTrue(any(t.startswith('node.script') for t in box_texts))   # a newobj, as Max saves it
        self.assertNotIn('node.script', box_classes)
        self.assertTrue(any('daemon_guard.js' in t for t in box_texts))
        self.assertIn('jweb', box_classes)

        # Check presentation sizing for jweb (750x190)
        jweb_box = next(b['box'] for b in boxes if b['box'].get('maxclass') == 'jweb')
        self.assertEqual([0.0, 0.0, 750.0, 190.0], jweb_box.get('presentation_rect'))
        self.assertIn('arranger_device.html', jweb_box.get('url', ''))

        # Check popout subpatcher with @floating 1 (900x550)
        popout_box = next(b['box'] for b in boxes if b['box'].get('text') == 'p popout')
        popout_attrs = popout_box.get('saved_object_attributes', {})
        self.assertEqual(1, popout_attrs.get('floating'))
        popout_rect = popout_box.get('patcher', {}).get('rect', [])
        # width = 1050 - 150 = 900, height = 700 - 150 = 550
        self.assertEqual(900.0, popout_rect[2] - popout_rect[0])
        self.assertEqual(550.0, popout_rect[3] - popout_rect[1])

        # Check Info View annotations
        live_thisdevice = next(b['box'] for b in boxes if b['box'].get('maxclass') == 'live.thisdevice')
        self.assertIn('annotation', live_thisdevice)
        self.assertIn('Vibelton Arranger', live_thisdevice['annotation'])

    def test_daemon_guard_script(self) -> None:
        """Verify daemon_guard.js node script resolves python and pings server."""
        daemon_path = Path(__file__).resolve().parent.parent / 'm4l' / 'daemon_guard.js'
        self.assertTrue(daemon_path.is_file(), 'daemon_guard.js must exist')

        res = subprocess.run(
            ['node', '-e', 'const dg = require("./m4l/daemon_guard.js"); console.log(typeof dg.pingStatus, typeof dg.resolvePython);'],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True,
            text=True
        )
        self.assertEqual(0, res.returncode, f'daemon_guard.js failed: {res.stderr}')
        self.assertIn('function function', res.stdout)

    def test_web_assets(self) -> None:
        """Verify web HTML, JS, and CSS assets exist and contain required components."""
        web_dir = Path(__file__).resolve().parent.parent / 'web'
        html = (web_dir / 'arranger_device.html').read_text(encoding='utf-8')
        js = (web_dir / 'arranger_device.js').read_text(encoding='utf-8')
        css = (web_dir / 'arranger_device.css').read_text(encoding='utf-8')

        # HTML checks
        self.assertIn('connectionPill', html)
        self.assertIn('btnPopout', html)
        self.assertIn('stemsContainer', html)
        self.assertIn('genreSelect', html)
        self.assertIn('energySvg', html)
        self.assertIn('energyTooltip', html)
        self.assertIn('btnScaffold', html)
        self.assertIn('btnRollback', html)

        # CSS checks
        self.assertIn('#1e1e1e', css)
        self.assertIn('#e6d765', css)
        self.assertIn('.energy-tooltip', css)

        # JS checks
        self.assertIn('executeScaffold', js)
        # The genre list comes from the server; the built-in list is only a fallback.
        self.assertIn('/api/production/genres', js)
        self.assertNotIn('GENRE_VARIANTS_MAP', js)
        self.assertIn('select-menu-group', css)
        self.assertIn('executeRollback', js)
        self.assertIn('drawEnergyCurve', js)

    def test_scaffold_arrangement_plan_creation_and_rollback(self) -> None:
        """Verify end-to-end subtractive arrangement planning, execution, and rollback by plan_id."""
        plan = production.create_scaffold_plan({
            'genre': 'House',
            'variant_id': 'club-version',
            'snapshot_name': 'Test Scaffold House'
        })

        self.assertEqual('Draft', plan['status'])
        self.assertEqual(1, len(plan['actions']))
        action = plan['actions'][0]
        self.assertEqual('apply_arrangement_copies', action['type'])
        self.assertTrue(len(action['copies']) > 0)

        # Apply plan
        job = production.execute({'plan_id': plan['id'], 'working_copy_confirmed': True})
        self.assertEqual('Queued', job['status'])

        # Simulate bridge execution readback
        exec_dir = self.root / 'queue' / 'production-executions'
        exec_dir.mkdir(parents=True, exist_ok=True)
        (exec_dir / (job['id'] + '.json')).write_text(json.dumps({
            'job_id': job['id'],
            'status': 'Applied',
            'completed_actions': len(action['copies']),
            'created_copies': action['copies'],
            'created_locators': [],
            'post_revision': 'rev-arr-2'
        }), encoding='utf-8')
        self.state['production']['revision'] = 'rev-arr-2'
        # Live now really contains every placed copy (rollback re-reads the Arrangement).
        tracks = {t['id']: t for t in self.state['production']['tracks']}
        for copy_spec in action['copies']:
            track = tracks[copy_spec['source_track_id']]
            source = next(c for c in track['arrangement_clips']
                          if c['start_beat'] == copy_spec['source_start_beat'])
            length = source['end_beat'] - source['start_beat']
            if copy_spec['destination_beat'] == copy_spec['source_start_beat']:
                continue  # the scaffold keeps the loop already sitting there
            track['arrangement_clips'].append(dict(
                source, start_beat=copy_spec['destination_beat'],
                end_beat=copy_spec['destination_beat'] + length))

        # Test rollback by plan_id (simulates client calling /api/production/plans/{plan_id}/rollback)
        rb_job = production.rollback_plan(plan['id'], {'working_copy_confirmed': True})
        self.assertEqual('Queued', rb_job['status'])

        rb_plan = production.get_plan(rb_job['plan_id'])
        self.assertEqual('rollback_arrangement_copies', rb_plan['actions'][0]['type'])
        placed = [c for c in action['copies'] if c['destination_beat'] != c['source_start_beat']]
        self.assertEqual(placed, rb_plan['actions'][0]['copies'])

    def test_scaffold_safety_requires_working_copy_confirmation(self) -> None:
        """Execution and rollback fail if working copy is not confirmed."""
        plan = production.create_scaffold_plan({'genre': 'House', 'variant_id': 'club-version'})
        with self.assertRaisesRegex(ValueError, 'working copy'):
            production.execute({'plan_id': plan['id'], 'working_copy_confirmed': False})


if __name__ == '__main__':
    unittest.main()
