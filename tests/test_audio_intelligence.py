from __future__ import annotations

import array
import math
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from vibelton import audio_intelligence, samples


def _write_sine_wav(
    path: Path,
    freq_hz: float,
    *,
    duration_s: float = 1.0,
    sr: int = 22050,
    amplitude: float = 0.7,
    phase_rad: float = 0.0,
) -> Path:
    n_samples = int(sr * duration_s)
    pcm = array.array('h')
    for i in range(n_samples):
        t = i / float(sr)
        val = amplitude * math.sin(2.0 * math.pi * freq_hz * t + phase_rad)
        pcm.append(int(max(-32767, min(32767, round(val * 32767)))))
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _write_pulse_train_wav(
    path: Path,
    pulses_per_sec: float,
    *,
    carrier_hz: float = 6500.0,
    duration_s: float = 2.0,
    sr: int = 22050,
) -> Path:
    n_samples = int(sr * duration_s)
    pcm = array.array('h')
    period = 1.0 / max(0.5, pulses_per_sec)
    for i in range(n_samples):
        t = i / float(sr)
        phase_in_beat = t % period
        env = math.exp(-phase_in_beat * 45.0) if phase_in_beat < 0.08 else 0.0
        val = 0.8 * env * math.sin(2.0 * math.pi * carrier_hz * t)
        pcm.append(int(max(-32767, min(32767, round(val * 32767)))))
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


class AudioIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        cache_dir = self.root / 'cache'
        p = patch.object(audio_intelligence, 'CACHE_DIR', cache_dir)
        p.start()
        self.addCleanup(p.stop)

    def test_55hz_sine_detects_a1_with_zero_cents_offset(self):
        wav = _write_sine_wav(self.root / 'sub_a1.wav', 55.0)
        res = audio_intelligence.analyse_audio_file(wav, use_cache=False)
        pitch = res['pitch_analysis']
        self.assertTrue(pitch['detected'])
        self.assertEqual(33, pitch['midi_note'])
        self.assertEqual('A1', pitch['note_name'])
        self.assertEqual('A', pitch['pitch_class'])
        self.assertAlmostEqual(55.0, pitch['fundamental_hz'], delta=0.4)
        self.assertAlmostEqual(0.0, pitch['cents_offset'], delta=2.0)
        self.assertEqual(0, pitch['recommended_pitch_fine'])

    def test_detuned_54_37hz_sine_recommends_plus_20_cents_and_target_key_shift(self):
        # 55.0 * 2^(-20/1200) = 54.3683 Hz
        wav = _write_sine_wav(self.root / 'detuned_a1.wav', 54.37)
        res = audio_intelligence.analyse_audio_file(wav, target_key='Ab', use_cache=False)
        pitch = res['pitch_analysis']
        self.assertTrue(pitch['detected'])
        self.assertEqual('A1', pitch['note_name'])
        self.assertAlmostEqual(-20.0, pitch['cents_offset'], delta=2.5)
        self.assertIn(pitch['recommended_pitch_fine'], (19, 20, 21))
        # A -> Ab is -1 semitone coarse shift
        self.assertEqual(-1, pitch['recommended_pitch_coarse'])

    def test_low_vs_high_frequency_band_classification(self):
        low_wav = _write_sine_wav(self.root / 'low_60.wav', 60.0)
        high_wav = _write_sine_wav(self.root / 'high_6000.wav', 6000.0)
        mid_wav = _write_sine_wav(self.root / 'lowmid_250.wav', 250.0)

        low_res = audio_intelligence.analyse_audio_file(low_wav, use_cache=False)['band_energy']
        high_res = audio_intelligence.analyse_audio_file(high_wav, use_cache=False)['band_energy']
        mid_res = audio_intelligence.analyse_audio_file(mid_wav, use_cache=False)['band_energy']

        self.assertGreater(low_res['low_pct'], 90.0)
        self.assertEqual('low', low_res['dominant_band'])

        self.assertGreater(high_res['high_pct'], 90.0)
        self.assertEqual('high', high_res['dominant_band'])

        self.assertGreater(mid_res['low_mid_pct'], 90.0)
        self.assertEqual('low_mid', mid_res['dominant_band'])

    def test_onset_density_distinguishes_sparse_and_dense_loops(self):
        sparse_wav = _write_pulse_train_wav(self.root / 'sparse.wav', pulses_per_sec=1.0)
        dense_wav = _write_pulse_train_wav(self.root / 'dense.wav', pulses_per_sec=8.0)

        sparse_onset = audio_intelligence.analyse_audio_file(sparse_wav, use_cache=False)['onset_density']
        dense_onset = audio_intelligence.analyse_audio_file(dense_wav, use_cache=False)['onset_density']

        self.assertEqual('sparse', sparse_onset['groove_density'])
        self.assertEqual('dense', dense_onset['groove_density'])
        self.assertGreater(dense_onset['onsets_per_second'], sparse_onset['onsets_per_second'])

    def test_anti_clash_scorer_ranks_high_shaker_above_muddy_loop_when_low_mid_occupied(self):
        shaker_wav = _write_pulse_train_wav(self.root / 'Shaker_120.wav', pulses_per_sec=6.0, carrier_hz=7000.0)
        muddy_wav = _write_sine_wav(self.root / 'MuddyLoop_120.wav', 260.0)

        p1 = patch.object(samples, 'SAMPLE_ROOT', self.root)
        p2 = patch.object(samples, 'EXTRA_SAMPLE_ROOTS', ())
        p1.start(); p2.start()
        self.addCleanup(p1.stop); self.addCleanup(p2.stop)

        rec = samples.recommend_samples({
            'role': 'percussion',
            'target_bpm': 119.0,
            'target_key': 'Ab',
            'occupied_bands': ['low', 'low_mid'],
            'candidate_paths': [str(muddy_wav), str(shaker_wav)],
        })
        ranked = rec['recommendations']
        self.assertEqual(2, len(ranked))
        self.assertEqual(str(shaker_wav.resolve()), ranked[0]['path'])
        self.assertGreater(ranked[0]['score'], ranked[1]['score'])

        shuffled = samples.quick_shuffle({
            'target_bpm': 119.0,
            'target_key': 'Ab',
            'candidate_paths': [str(shaker_wav), str(muddy_wav)],
            'locked_slots': {'top_loop': str(shaker_wav)},
        })
        self.assertTrue(shuffled['slots'][0]['locked'])
        self.assertEqual(str(shaker_wav.resolve()), shuffled['slots'][0]['selected']['path'])

    def test_kick_bass_phase_cancellation_detected_at_180_degrees(self):
        kick_wav = _write_sine_wav(self.root / 'kick_60.wav', 60.0, phase_rad=0.0)
        bass_out = _write_sine_wav(self.root / 'bass_60_inv.wav', 60.0, phase_rad=math.pi)
        bass_in = _write_sine_wav(self.root / 'bass_60_in.wav', 60.0, phase_rad=0.0)

        clash = audio_intelligence.diagnose_kick_bass_clash(kick_wav, bass_out)
        self.assertTrue(clash['phase_cancellation_detected'])
        self.assertTrue(clash['clash_detected'])
        self.assertLess(clash['sub_phase_correlation'], -0.9)
        self.assertGreater(clash['polarity_inverted_gain_db'], 6.0)
        actions = [r['action'] for r in clash['recommendations']]
        self.assertIn('invert_polarity', actions)

        aligned = audio_intelligence.diagnose_kick_bass_clash(kick_wav, bass_in)
        self.assertFalse(aligned['phase_cancellation_detected'])
        self.assertGreater(aligned['sub_phase_correlation'], 0.9)

    def test_compare_renders_computes_loudness_and_spectral_deltas(self):
        ref_wav = _write_sine_wav(self.root / 'ref_low.wav', 60.0, amplitude=0.8)
        cand_wav = _write_sine_wav(self.root / 'cand_high.wav', 6000.0, amplitude=0.2)

        comp = audio_intelligence.compare_renders(ref_wav, cand_wav)
        self.assertEqual('compared', comp['status'])
        self.assertLess(comp['deltas']['loudness_delta_db'], -6.0)
        self.assertLess(comp['deltas']['spectral_delta_db']['low_db'], -20.0)
        self.assertGreater(comp['deltas']['spectral_delta_db']['high_db'], 20.0)
        self.assertTrue(len(comp['recommendations']) >= 1)

    def test_transcribe_audio_to_midi_4_note_melody_at_120_bpm(self):
        # 4-note melody WAV: C3 (48) -> Eb3 (51) -> G3 (55) -> Bb3 (58) at 120 BPM (0.5s per beat)
        sr = 22050
        note_pitches = (48, 51, 55, 58)
        pcm = array.array('h')
        samples_per_beat = int(sr * 0.5)
        for midi_p in note_pitches:
            freq = 440.0 * (2.0 ** ((midi_p - 69.0) / 12.0))
            for i in range(samples_per_beat):
                t = i / float(sr)
                val = 0.75 * math.sin(2.0 * math.pi * freq * t)
                pcm.append(int(max(-32767, min(32767, round(val * 32767)))))
        melody_wav = self.root / 'melody_c_min7_120.wav'
        with wave.open(str(melody_wav), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())

        res = audio_intelligence.transcribe_audio_to_midi(melody_wav, bpm=120.0, quantize_grid=0.25)
        self.assertEqual(4, len(res['notes']))
        pitches = tuple(n['pitch'] for n in res['notes'])
        starts = tuple(round(n['start'], 2) for n in res['notes'])
        self.assertEqual((48, 51, 55, 58), pitches)
        self.assertEqual((0.0, 1.0, 2.0, 3.0), starts)
        self.assertEqual('C', res['detected_key'])
        self.assertEqual('minor', res['detected_scale'])

    def test_slice_loop_transients_returns_band_and_pitch_markers(self):
        pulse_wav = _write_pulse_train_wav(self.root / 'chop_test.wav', pulses_per_sec=4.0, duration_s=2.0)
        sliced = audio_intelligence.slice_loop_transients(pulse_wav, max_slices=16)
        self.assertGreaterEqual(sliced['slice_count'], 4)
        self.assertEqual(0.0, sliced['slices'][0]['start_seconds'])
        self.assertEqual('high', sliced['slices'][0]['dominant_band'])
        self.assertEqual(sliced['slice_count'], len(sliced['midi_notes']))

    def test_stereo_silent_and_short_wav_edge_cases(self):
        sr = 22050
        # 1. Silent 1-second stereo WAV
        silent_wav = self.root / 'silent_stereo.wav'
        with wave.open(str(silent_wav), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(array.array('h', [0] * (sr * 2)).tobytes())
        t_silent = audio_intelligence.transcribe_audio_to_midi(silent_wav, bpm=120.0, quantize_grid=0.5)
        self.assertEqual(0, t_silent['note_count'])
        self.assertEqual(0.5, t_silent['quantize_grid'])
        self.assertEqual([], t_silent['notes'])
        s_silent = audio_intelligence.slice_loop_transients(silent_wav, bpm=124.0)
        self.assertEqual(0, s_silent['slice_count'])
        self.assertEqual(0, s_silent['bars'])
        self.assertEqual(124.0, s_silent['bpm'])
        self.assertEqual([], s_silent['slices'])
        self.assertEqual([], s_silent['midi_notes'])

        # Zero-frame WAV early return schema check
        empty_wav = self.root / 'empty_zero.wav'
        with wave.open(str(empty_wav), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(b'')
        t_empty = audio_intelligence.transcribe_audio_to_midi(empty_wav, bpm=128.0, quantize_grid=0.125)
        self.assertEqual(0, t_empty['note_count'])
        self.assertEqual(0.125, t_empty['quantize_grid'])
        self.assertEqual([], t_empty['notes'])

        # 2. Pitched stereo WAV (A3 = 220 Hz on L+R)
        stereo_wav = self.root / 'stereo_a3.wav'
        pcm_stereo = array.array('h')
        for i in range(sr):
            sample_val = int(round(0.7 * math.sin(2.0 * math.pi * 220.0 * (i / float(sr))) * 32767))
            pcm_stereo.append(sample_val)
            pcm_stereo.append(sample_val)
        with wave.open(str(stereo_wav), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_stereo.tobytes())
        t_stereo = audio_intelligence.transcribe_audio_to_midi(stereo_wav, bpm=120.0)
        self.assertGreaterEqual(t_stereo['note_count'], 1)
        self.assertEqual(57, t_stereo['notes'][0]['pitch'])

    def test_slice_loop_transients_respects_max_seconds_beyond_16s(self) -> None:
        long_wav = self.root / 'long_18s.wav'
        sr = 8000
        total_samples = sr * 18
        pcm = array.array('h', [0] * total_samples)
        # Put impulses at 1.0s and 17.0s
        for onset_sec in (1.0, 17.0):
            start_idx = int(onset_sec * sr)
            for i in range(int(0.05 * sr)):
                if start_idx + i < total_samples:
                    pcm[start_idx + i] = int(round(0.85 * math.sin(2.0 * math.pi * 200.0 * (i / float(sr))) * 32767))
        with wave.open(str(long_wav), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())

        res_default = audio_intelligence.slice_loop_transients(long_wav, max_slices=8, bpm=120.0, max_seconds=20.0)
        self.assertGreaterEqual(res_default['duration_seconds'], 17.5)
        self.assertTrue(any(s['start_seconds'] >= 16.5 for s in res_default['slices']))


if __name__ == '__main__':
    unittest.main()
