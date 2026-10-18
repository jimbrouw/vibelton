from __future__ import annotations

import array
import cmath
import hashlib
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / '.vibelton' / 'sample-analysis-cache'

NOTE_NAMES = ('C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')
PITCH_CLASS_TO_SEMITONE: dict[str, int] = {
    'C': 0, 'B#': 0,
    'C#': 1, 'DB': 1,
    'D': 2,
    'D#': 3, 'EB': 3,
    'E': 4, 'FB': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'GB': 6,
    'G': 7,
    'G#': 8, 'AB': 8,
    'A': 9,
    'A#': 10, 'BB': 10,
    'B': 11, 'CB': 11,
}


def _ffmpeg_bin() -> str:
    return shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'


def parse_pitch_class(key_str: str | None) -> int | None:
    if not key_str or not isinstance(key_str, str):
        return None
    cleaned = key_str.strip()
    if not cleaned:
        return None
    token = cleaned.split()[0].strip()
    is_minor = False
    if token.endswith('m') and len(token) >= 2 and token[:-1].upper() in PITCH_CLASS_TO_SEMITONE:
        is_minor = True
        token = token[:-1]
    elif 'minor' in cleaned.lower() or 'min' in cleaned.lower():
        is_minor = True
    semi = PITCH_CLASS_TO_SEMITONE.get(token.upper())
    if semi is None:
        return None
    return semi


def _decode_pcm_channels(path: Path, max_seconds: float = 16.0, target_sr: int = 22050) -> tuple[list[float], list[float] | None, int]:
    """Decode audio file into normalized float samples in [-1.0, 1.0].
    Returns (mono_samples, right_channel_or_None_if_mono, sample_rate).
    Uses stdlib wave when possible for speed, falling back to ffmpeg for non-PCM formats.
    """
    try:
        with wave.open(str(path), 'rb') as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sr = wf.getframerate()
            comp_type = wf.getcomptype()
            if comp_type == 'NONE' and sampwidth in (1, 2, 3, 4) and sr > 0:
                max_frames = int(min(wf.getnframes(), max(1, int(sr * max_seconds))))
                raw = wf.readframes(max_frames)
                samples_all = _unpack_pcm_bytes(raw, sampwidth)
                if channels <= 1:
                    mono = samples_all
                    right = None
                else:
                    left = samples_all[0::channels]
                    right = samples_all[1::channels]
                    mono = [(l + r) * 0.5 for l, r in zip(left, right)]
                if sr > 48000:
                    step = max(1, round(sr / target_sr))
                    mono = mono[::step]
                    if right is not None:
                        right = right[::step]
                    sr = int(round(sr / step))
                return mono, right, sr
    except Exception:
        pass

    cmd = [
        _ffmpeg_bin(),
        '-v', 'error',
        '-i', str(path),
        '-t', str(float(max_seconds)),
        '-ac', '2',
        '-ar', str(int(target_sr)),
        '-f', 's16le',
        '-',
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0 or not proc.stdout:
        return [], None, target_sr
    arr = array.array('h')
    usable = (len(proc.stdout) // 4) * 4
    arr.frombytes(proc.stdout[:usable])
    scale = 1.0 / 32768.0
    left = [arr[i] * scale for i in range(0, len(arr), 2)]
    right = [arr[i] * scale for i in range(1, len(arr), 2)]
    mono = [(l + r) * 0.5 for l, r in zip(left, right)]
    return mono, right, target_sr


def _unpack_pcm_bytes(raw: bytes, sampwidth: int) -> list[float]:
    if not raw:
        return []
    if sampwidth == 2:
        arr = array.array('h')
        usable = (len(raw) // 2) * 2
        arr.frombytes(raw[:usable])
        scale = 1.0 / 32768.0
        return [x * scale for x in arr]
    if sampwidth == 1:
        return [(b - 128) / 128.0 for b in raw]
    if sampwidth == 3:
        out: list[float] = []
        scale = 1.0 / 8388608.0
        for i in range(0, len(raw) - 2, 3):
            val = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
            if val & 0x800000:
                val -= 0x1000000
            out.append(val * scale)
        return out
    if sampwidth == 4:
        arr = array.array('i')
        usable = (len(raw) // 4) * 4
        arr.frombytes(raw[:usable])
        scale = 1.0 / 2147483648.0
        return [x * scale for x in arr]
    return []


def _fft_radix2(x: list[complex]) -> list[complex]:
    n = len(x)
    if n <= 1:
        return x
    # Bit-reversal permutation
    j = 0
    a = list(x)
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        half = length >> 1
        angle = -2.0 * math.pi / length
        wlen = cmath.rect(1.0, angle)
        for i in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(half):
                u = a[i + k]
                v = a[i + k + half] * w
                a[i + k] = u + v
                a[i + k + half] = u - v
                w *= wlen
        length <<= 1
    return a


def _compute_band_energy(samples: list[float], sr: int) -> dict[str, Any]:
    if not samples or sr <= 0:
        return {
            'low_pct': 0.0,
            'low_mid_pct': 0.0,
            'mid_pct': 0.0,
            'high_pct': 0.0,
            'low_db': -120.0,
            'low_mid_db': -120.0,
            'mid_db': -120.0,
            'high_db': -120.0,
            'dominant_band': 'silent',
        }
    fft_size = 2048 if len(samples) >= 2048 else 1024
    while fft_size > len(samples) and fft_size > 256:
        fft_size //= 2

    window = [0.5 * (1.0 - math.cos(2.0 * math.pi * i / max(1, fft_size - 1))) for i in range(fft_size)]
    num_frames = min(16, max(1, len(samples) // max(1, fft_size // 2)))
    if len(samples) <= fft_size:
        starts = [0]
    else:
        step = max(1, (len(samples) - fft_size) // max(1, num_frames - 1))
        starts = [min(len(samples) - fft_size, i * step) for i in range(num_frames)]

    low_e = 0.0
    low_mid_e = 0.0
    mid_e = 0.0
    high_e = 0.0
    half_n = fft_size // 2

    for start in starts:
        chunk = samples[start:start + fft_size]
        if len(chunk) < fft_size:
            chunk = chunk + [0.0] * (fft_size - len(chunk))
        windowed = [complex(chunk[i] * window[i], 0.0) for i in range(fft_size)]
        spec = _fft_radix2(windowed)
        for k in range(1, half_n + 1):
            freq = (k * sr) / float(fft_size)
            mag_sq = (spec[k].real * spec[k].real + spec[k].imag * spec[k].imag) / (fft_size * fft_size)
            if 20.0 <= freq < 120.0:
                low_e += mag_sq
            elif 120.0 <= freq < 500.0:
                low_mid_e += mag_sq
            elif 500.0 <= freq < 4000.0:
                mid_e += mag_sq
            elif 4000.0 <= freq <= 11000.0:
                high_e += mag_sq

    frame_count = float(max(1, len(starts)))
    low_e /= frame_count
    low_mid_e /= frame_count
    mid_e /= frame_count
    high_e /= frame_count

    total_e = low_e + low_mid_e + mid_e + high_e
    if total_e <= 1e-18:
        return {
            'low_pct': 0.0,
            'low_mid_pct': 0.0,
            'mid_pct': 0.0,
            'high_pct': 0.0,
            'low_db': -120.0,
            'low_mid_db': -120.0,
            'mid_db': -120.0,
            'high_db': -120.0,
            'dominant_band': 'silent',
        }

    low_pct = round(100.0 * low_e / total_e, 2)
    low_mid_pct = round(100.0 * low_mid_e / total_e, 2)
    mid_pct = round(100.0 * mid_e / total_e, 2)
    high_pct = round(max(0.0, 100.0 - (low_pct + low_mid_pct + mid_pct)), 2)

    def _to_db(val: float) -> float:
        return round(10.0 * math.log10(max(val, 1e-12)), 2)

    bands = {
        'low': low_pct,
        'low_mid': low_mid_pct,
        'mid': mid_pct,
        'high': high_pct,
    }
    dominant = max(bands.items(), key=lambda kv: kv[1])[0]
    return {
        'low_pct': low_pct,
        'low_mid_pct': low_mid_pct,
        'mid_pct': mid_pct,
        'high_pct': high_pct,
        'low_db': _to_db(low_e),
        'low_mid_db': _to_db(low_mid_e),
        'mid_db': _to_db(mid_e),
        'high_db': _to_db(high_e),
        'dominant_band': dominant,
    }


def _compute_onset_density(samples: list[float], sr: int) -> dict[str, Any]:
    duration = len(samples) / float(sr) if sr > 0 else 0.0
    if not samples or duration <= 0.02:
        return {
            'transient_count': 0,
            'onsets_per_second': 0.0,
            'groove_density': 'sparse',
        }
    frame_len = max(1, int(sr * 0.010))
    energies: list[float] = []
    for i in range(0, len(samples) - frame_len + 1, frame_len):
        frame = samples[i:i + frame_len]
        energies.append(math.sqrt(sum(s * s for s in frame) / frame_len))

    if len(energies) < 3:
        return {
            'transient_count': 0,
            'onsets_per_second': 0.0,
            'groove_density': 'sparse',
        }

    flux = [0.0]
    for i in range(1, len(energies)):
        diff = energies[i] - energies[i - 1]
        flux.append(diff if diff > 0.0 else 0.0)

    mean_flux = sum(flux) / len(flux)
    max_flux = max(flux)
    if max_flux <= 1e-4:
        return {
            'transient_count': 0,
            'onsets_per_second': 0.0,
            'groove_density': 'sparse',
        }

    threshold = max(mean_flux * 2.2, max_flux * 0.14, 0.008)
    min_gap_frames = max(1, int(0.060 / 0.010))  # 60ms minimum inter-onset gap
    onset_frames: list[int] = []
    last_onset = -min_gap_frames * 2
    for i in range(1, len(flux) - 1):
        if flux[i] >= threshold and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            if i - last_onset >= min_gap_frames:
                onset_frames.append(i)
                last_onset = i

    onsets_per_sec = round(len(onset_frames) / duration, 2)
    if onsets_per_sec < 2.0:
        groove_density = 'sparse'
    elif onsets_per_sec < 5.5:
        groove_density = 'medium'
    else:
        groove_density = 'dense'

    return {
        'transient_count': len(onset_frames),
        'onsets_per_second': onsets_per_sec,
        'groove_density': groove_density,
    }


def _estimate_pitch_yin(samples: list[float], sr: int, target_key: str | None = None) -> dict[str, Any]:
    empty_result = {
        'detected': False,
        'fundamental_hz': None,
        'midi_note': None,
        'note_name': None,
        'pitch_class': None,
        'cents_offset': 0.0,
        'confidence': 0.0,
        'recommended_pitch_coarse': 0,
        'recommended_pitch_fine': 0,
    }
    if not samples or sr <= 0:
        return empty_result

    min_freq = 30.0
    max_freq = 400.0
    tau_min = max(2, int(sr / max_freq))
    tau_max = int(sr / min_freq)
    win_size = max(tau_max * 2 + 16, int(sr * 0.08))
    if len(samples) < tau_max + 16:
        return empty_result
    win_size = min(len(samples), win_size)
    W = min(win_size - tau_max - 1, int(sr * 0.05))
    if W <= tau_min:
        W = max(tau_min + 2, len(samples) // 2)
    if W + tau_max >= len(samples):
        tau_max = max(tau_min + 2, len(samples) - W - 1)
    if tau_max <= tau_min:
        return empty_result

    # Find highest-RMS steady-state window
    best_start = 0
    best_rms = -1.0
    step = max(1, (len(samples) - (W + tau_max)) // 8)
    for start in range(0, max(1, len(samples) - (W + tau_max)), step):
        seg = samples[start:start + W]
        rms = sum(s * s for s in seg) / len(seg)
        if rms > best_rms:
            best_rms = rms
            best_start = start

    if best_rms < 1e-7:
        return empty_result

    seg = samples[best_start:best_start + W + tau_max + 1]
    d = [0.0] * (tau_max + 1)
    cmndf = [1.0] * (tau_max + 1)
    running_sum = 0.0

    for tau in range(1, tau_max + 1):
        diff_sq = 0.0
        for j in range(W):
            delta = seg[j] - seg[j + tau]
            diff_sq += delta * delta
        d[tau] = diff_sq
        running_sum += diff_sq
        cmndf[tau] = (diff_sq * tau / running_sum) if running_sum > 1e-15 else 1.0

    yin_threshold = 0.15
    best_tau = None
    for tau in range(tau_min, tau_max):
        if cmndf[tau] < yin_threshold:
            while tau + 1 <= tau_max and cmndf[tau + 1] < cmndf[tau]:
                tau += 1
            best_tau = tau
            break

    if best_tau is None:
        best_tau = min(range(tau_min, tau_max + 1), key=lambda t: cmndf[t])

    confidence = round(max(0.0, min(1.0, 1.0 - cmndf[best_tau])), 3)
    if confidence < 0.35:
        return empty_result

    # Parabolic interpolation on d[tau] around best_tau
    if 1 < best_tau < tau_max:
        s0 = d[best_tau - 1]
        s1 = d[best_tau]
        s2 = d[best_tau + 1]
        denom = 2.0 * (s0 - 2.0 * s1 + s2)
        if abs(denom) > 1e-15:
            shift = (s0 - s2) / denom
            if -1.0 < shift < 1.0:
                refined_tau = best_tau + shift
            else:
                refined_tau = float(best_tau)
        else:
            refined_tau = float(best_tau)
    else:
        refined_tau = float(best_tau)

    fundamental_hz = sr / refined_tau
    if not (25.0 <= fundamental_hz <= 450.0):
        return empty_result

    midi_exact = 69.0 + 12.0 * math.log2(fundamental_hz / 440.0)
    midi_note = int(round(midi_exact))
    cents_offset = round((midi_exact - midi_note) * 100.0, 2)
    if cents_offset > 50.0:
        cents_offset = 50.0
    elif cents_offset < -50.0:
        cents_offset = -50.0

    semitone = midi_note % 12
    octave = (midi_note // 12) - 1
    pitch_class = NOTE_NAMES[semitone]
    note_name = f'{pitch_class}{octave}'

    # Compute recommended pitch_fine in [-50, 49] to bring sample in tune
    fine_correction = int(round(-cents_offset))
    coarse_adj = 0
    if fine_correction >= 50:
        fine_correction -= 100
        coarse_adj += 1
    elif fine_correction < -50:
        fine_correction += 100
        coarse_adj -= 1

    target_semi = parse_pitch_class(target_key)
    if target_semi is not None:
        diff_semi = (target_semi - semitone) % 12
        if diff_semi > 6:
            diff_semi -= 12
        coarse_adj += diff_semi

    return {
        'detected': True,
        'fundamental_hz': round(fundamental_hz, 2),
        'midi_note': midi_note,
        'note_name': note_name,
        'pitch_class': pitch_class,
        'cents_offset': cents_offset,
        'confidence': confidence,
        'recommended_pitch_coarse': int(coarse_adj),
        'recommended_pitch_fine': int(fine_correction),
    }


def calculate_smart_tuning(
    sample_key: str | int | dict[str, Any] | None,
    target_key: str | None,
    cents_offset: float = 0.0,
) -> dict[str, int]:
    """Compute Ableton clip pitch_coarse (-48..48 semitones) and pitch_fine (-50..49 cents)
    to tune a sample from sample_key (or pitch_analysis dict) to target_key.
    """
    sample_semi: int | None = None
    if isinstance(sample_key, dict):
        if sample_key.get('detected') and sample_key.get('midi_note') is not None:
            sample_semi = int(sample_key['midi_note']) % 12
        elif sample_key.get('pitch_class') or sample_key.get('note_name'):
            sample_semi = parse_pitch_class(str(sample_key.get('pitch_class') or sample_key.get('note_name')))
        if 'cents_offset' in sample_key and sample_key['cents_offset'] is not None:
            cents_offset = float(sample_key['cents_offset'])
    elif isinstance(sample_key, int):
        sample_semi = sample_key % 12
    elif isinstance(sample_key, str):
        sample_semi = parse_pitch_class(sample_key)

    fine_correction = int(round(-float(cents_offset or 0.0)))
    coarse_adj = 0
    if fine_correction >= 50:
        fine_correction -= 100
        coarse_adj += 1
    elif fine_correction < -50:
        fine_correction += 100
        coarse_adj -= 1

    target_semi = parse_pitch_class(target_key)
    if sample_semi is not None and target_semi is not None:
        diff_semi = (target_semi - sample_semi) % 12
        if diff_semi > 6:
            diff_semi -= 12
        coarse_adj += diff_semi

    return {
        'pitch_coarse': max(-48, min(48, int(coarse_adj))),
        'pitch_fine': max(-50, min(49, int(fine_correction))),
    }


def _recompute_target_tuning(pitch_info: dict[str, Any], target_key: str | None) -> dict[str, Any]:
    out = dict(pitch_info)
    if not out.get('detected') or out.get('midi_note') is None:
        return out
    smart = calculate_smart_tuning(out, target_key)
    out['recommended_pitch_coarse'] = int(smart['pitch_coarse'])
    out['recommended_pitch_fine'] = int(smart['pitch_fine'])
    return out



def analyse_audio_file(
    path: Path | str,
    max_seconds: float = 16.0,
    target_key: str | None = None,
    sha256: str | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    file_path = Path(path)
    cache_file = None
    if use_cache:
        file_hash = sha256
        if not file_hash and file_path.exists():
            digest = hashlib.sha256()
            with file_path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(65536), b''):
                    digest.update(chunk)
            file_hash = digest.hexdigest()
        if file_hash:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f'{file_hash}.json'
            if cache_file.exists():
                try:
                    cached = json.loads(cache_file.read_text())
                    cached['pitch_analysis'] = _recompute_target_tuning(cached.get('pitch_analysis', {}), target_key)
                    return cached
                except Exception:
                    pass

    mono, _, sr = _decode_pcm_channels(file_path, max_seconds=max_seconds)
    band_energy = _compute_band_energy(mono, sr)
    onset_density = _compute_onset_density(mono, sr)
    pitch_analysis = _estimate_pitch_yin(mono, sr, target_key=target_key)

    result = {
        'band_energy': band_energy,
        'spectral_bands': band_energy,
        'onset_density': onset_density,
        'pitch_analysis': pitch_analysis,
    }
    if cache_file is not None:
        try:
            cache_file.write_text(json.dumps(result, indent=2, sort_keys=True))
        except Exception:
            pass
    return result


def score_sample_candidate(
    sample_meta: dict[str, Any],
    *,
    role: str = 'percussion',
    target_bpm: float | None = 119.0,
    target_key: str | None = None,
    occupied_bands: list[str] | None = None,
) -> dict[str, Any]:
    role_key = str(role or 'percussion').strip().lower()
    bands = sample_meta.get('spectral_bands') or sample_meta.get('band_energy') or {}
    low_pct = float(bands.get('low_pct', 0.0))
    low_mid_pct = float(bands.get('low_mid_pct', 0.0))
    mid_pct = float(bands.get('mid_pct', 0.0))
    high_pct = float(bands.get('high_pct', 0.0))
    onset = sample_meta.get('onset_density') or {}
    onsets_per_sec = float(onset.get('onsets_per_second', 0.0))
    pitch = _recompute_target_tuning(sample_meta.get('pitch_analysis') or {}, target_key)

    # 1. BPM closeness score (0..100)
    hints = sample_meta.get('filename_bpm_hints') or []
    bpm_score = 72.0
    matched_bpm = None
    if target_bpm and hints:
        best_diff = 999.0
        for h in hints:
            for candidate_bpm in (float(h), float(h) * 2.0, float(h) * 0.5):
                diff = abs(candidate_bpm - float(target_bpm))
                if diff < best_diff:
                    best_diff = diff
                    matched_bpm = float(h)
        bpm_score = max(10.0, round(100.0 - best_diff * 4.5, 2))

    # 2. Spectral fit & Anti-Clash score (0..100)
    if role_key in ('bass', 'sub', '808', 'kick'):
        role_energy = low_pct * 1.15 + low_mid_pct * 0.35 - high_pct * 0.4
    elif role_key in ('top_loop', 'hats', 'shaker', 'percussion', 'drum_loop', 'drums'):
        role_energy = high_pct * 0.95 + mid_pct * 0.45 - low_pct * 0.65 - low_mid_pct * 0.45
        if onsets_per_sec >= 2.0:
            role_energy += 12.0
    elif role_key in ('vocal', 'lead', 'hook', 'chords', 'synth'):
        role_energy = mid_pct * 0.9 + low_mid_pct * 0.35 + high_pct * 0.25 - low_pct * 0.5
    else:  # fx / texture
        role_energy = high_pct * 0.65 + mid_pct * 0.55 - low_pct * 0.4

    clash_penalty = 0.0
    occupied = {b.lower() for b in (occupied_bands or [])}
    if 'low_mid' in occupied or 'mud' in occupied:
        clash_penalty += low_mid_pct * 0.55
    if 'low' in occupied and role_key not in ('bass', 'sub', '808', 'kick'):
        clash_penalty += low_pct * 0.70
    if 'mid' in occupied and role_key in ('percussion', 'shaker', 'hats', 'top_loop'):
        clash_penalty += mid_pct * 0.25

    spectral_fit_score = round(max(0.0, min(100.0, 50.0 + role_energy * 0.55 - clash_penalty * 0.55)), 2)

    # 3. Tuning plan & harmonic score
    tuning_plan = {
        'target_key': target_key,
        'detected_note': pitch.get('note_name'),
        'cents_offset': pitch.get('cents_offset', 0.0),
        'pitch_coarse': int(pitch.get('recommended_pitch_coarse', 0)),
        'pitch_fine': int(pitch.get('recommended_pitch_fine', 0)),
    }
    harmonic_score = 80.0
    if role_key in ('bass', 'sub', '808', 'chords', 'lead', 'synth'):
        if pitch.get('detected'):
            shift = abs(int(pitch.get('recommended_pitch_coarse', 0)))
            harmonic_score = max(30.0, 100.0 - shift * 8.0)
        else:
            harmonic_score = 55.0

    total_score = round(
        spectral_fit_score * 0.50 + bpm_score * 0.30 + harmonic_score * 0.20,
        2,
    )
    return {
        'total_score': total_score,
        'bpm_score': bpm_score,
        'matched_bpm_hint': matched_bpm,
        'spectral_fit_score': spectral_fit_score,
        'harmonic_score': round(harmonic_score, 2),
        'clash_penalty': round(clash_penalty, 2),
        'tuning_plan': tuning_plan,
    }


def _measure_render_stats(path: Path) -> dict[str, Any]:
    mono, right, sr = _decode_pcm_channels(path, max_seconds=30.0)
    if not mono or sr <= 0:
        return {
            'path': str(path),
            'loudness_lufs_approx': -120.0,
            'rms_dbfs': -120.0,
            'sample_peak_dbfs': -120.0,
            'true_peak_dbfs_approx': -120.0,
            'crest_factor_db': 0.0,
            'stereo_correlation': 1.0,
            'band_energy': _compute_band_energy([], 22050),
        }

    mean_sq = sum(s * s for s in mono) / len(mono)
    rms_dbfs = 10.0 * math.log10(max(mean_sq, 1e-12))
    # Gated loudness approximation (blocks above -70 dBFS and relative -10 dB gate)
    block_size = max(1, int(sr * 0.400))
    block_ms: list[float] = []
    for i in range(0, len(mono), max(1, block_size // 2)):
        blk = mono[i:i + block_size]
        if blk:
            b_ms = sum(s * s for s in blk) / len(blk)
            if 10.0 * math.log10(max(b_ms, 1e-12)) > -70.0:
                block_ms.append(b_ms)
    if block_ms:
        rel_gate = (sum(block_ms) / len(block_ms)) * 0.1
        gated = [b for b in block_ms if b >= rel_gate] or block_ms
        loudness_lufs = round(-0.691 + 10.0 * math.log10(max(sum(gated) / len(gated), 1e-12)), 2)
    else:
        loudness_lufs = -120.0

    sample_peak = max(abs(s) for s in mono)
    # Inter-sample true peak approximation via parabolic mid-point interpolation
    true_peak = sample_peak
    for i in range(1, len(mono) - 1):
        mid_est = abs(0.5 * (mono[i] + mono[i + 1]) + 0.125 * (mono[i] + mono[i + 1] - mono[i - 1] - mono[min(len(mono) - 1, i + 2)]))
        if mid_est > true_peak:
            true_peak = mid_est

    sample_peak_dbfs = round(20.0 * math.log10(max(sample_peak, 1e-6)), 2)
    true_peak_dbfs = round(20.0 * math.log10(max(true_peak, 1e-6)), 2)
    rms_dbfs_round = round(rms_dbfs, 2)
    crest_factor_db = round(sample_peak_dbfs - rms_dbfs_round, 2)

    stereo_corr = 1.0
    if right is not None and len(right) == len(mono):
        # Reconstruct left from mono and right: mono = (L+R)/2 => L = 2*mono - R
        left = [2.0 * m - r for m, r in zip(mono, right)]
        sum_lr = sum(l * r for l, r in zip(left, right))
        sum_l2 = sum(l * l for l in left)
        sum_r2 = sum(r * r for r in right)
        denom = math.sqrt(sum_l2 * sum_r2)
        if denom > 1e-12:
            stereo_corr = round(max(-1.0, min(1.0, sum_lr / denom)), 3)

    band_energy = _compute_band_energy(mono, sr)
    return {
        'path': str(path),
        'loudness_lufs_approx': loudness_lufs,
        'rms_dbfs': rms_dbfs_round,
        'sample_peak_dbfs': sample_peak_dbfs,
        'true_peak_dbfs_approx': true_peak_dbfs,
        'crest_factor_db': crest_factor_db,
        'stereo_correlation': stereo_corr,
        'band_energy': band_energy,
    }


def compare_renders(before_path: Path | str, after_path: Path | str) -> dict[str, Any]:
    before_stats = _measure_render_stats(Path(before_path))
    after_stats = _measure_render_stats(Path(after_path))
    b_bands = before_stats['band_energy']
    a_bands = after_stats['band_energy']

    spectral_delta_db = {
        'low_db': round(float(a_bands['low_db']) - float(b_bands['low_db']), 2),
        'low_mid_db': round(float(a_bands['low_mid_db']) - float(b_bands['low_mid_db']), 2),
        'mid_db': round(float(a_bands['mid_db']) - float(b_bands['mid_db']), 2),
        'high_db': round(float(a_bands['high_db']) - float(b_bands['high_db']), 2),
    }
    spectral_pct_delta = {
        'low_pct': round(float(a_bands['low_pct']) - float(b_bands['low_pct']), 2),
        'low_mid_pct': round(float(a_bands['low_mid_pct']) - float(b_bands['low_mid_pct']), 2),
        'mid_pct': round(float(a_bands['mid_pct']) - float(b_bands['mid_pct']), 2),
        'high_pct': round(float(a_bands['high_pct']) - float(b_bands['high_pct']), 2),
    }

    recommendations: list[str] = []
    if spectral_delta_db['low_db'] < -3.0:
        recommendations.append('Candidate has significantly less sub/low energy (20-120 Hz) than reference; check Kick/Bass level or sub reinforcement.')
    elif spectral_delta_db['low_db'] > 3.0:
        recommendations.append('Candidate has heavier sub/low build-up (20-120 Hz) than reference; trim sub-bass or tighten kick tail.')
    if spectral_delta_db['low_mid_db'] > 2.5:
        recommendations.append('Low-mid build-up detected (120-500 Hz); consider a 2-3 dB cut around 250 Hz on Chords/Pads.')
    if spectral_delta_db['high_db'] < -3.0:
        recommendations.append('Top-end air/transient energy (4-11 kHz) is darker than reference; brighten hats/shakers or high-shelf vocal.')
    if after_stats['true_peak_dbfs_approx'] > -0.3:
        recommendations.append('True peak exceeds -0.3 dBFS; lower limiter ceiling to -1.0 dBTP to prevent clipping.')

    return {
        'status': 'compared',
        'reference_or_before': before_stats,
        'candidate_or_after': after_stats,
        'deltas': {
            'loudness_delta_db': round(after_stats['loudness_lufs_approx'] - before_stats['loudness_lufs_approx'], 2),
            'rms_delta_db': round(after_stats['rms_dbfs'] - before_stats['rms_dbfs'], 2),
            'peak_delta_db': round(after_stats['sample_peak_dbfs'] - before_stats['sample_peak_dbfs'], 2),
            'crest_delta_db': round(after_stats['crest_factor_db'] - before_stats['crest_factor_db'], 2),
            'spectral_delta_db': spectral_delta_db,
            'spectral_pct_delta': spectral_pct_delta,
        },
        'recommendations': recommendations,
    }


def _lowpass_sub(samples: list[float], sr: int, cutoff_hz: float = 115.0) -> list[float]:
    if not samples or sr <= 0:
        return []
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / float(sr)
    alpha = dt / (rc + dt)
    out = [0.0] * len(samples)
    prev = samples[0]
    for i, x in enumerate(samples):
        prev = prev + alpha * (x - prev)
        out[i] = prev
    # Second pass for 12 dB/oct roll-off
    prev2 = out[0]
    for i, x in enumerate(out):
        prev2 = prev2 + alpha * (x - prev2)
        out[i] = prev2
    return out


def diagnose_kick_bass_clash(kick_path: Path | str, bass_path: Path | str) -> dict[str, Any]:
    kick_mono, _, k_sr = _decode_pcm_channels(Path(kick_path), max_seconds=16.0)
    bass_mono, _, b_sr = _decode_pcm_channels(Path(bass_path), max_seconds=16.0)
    sr = k_sr or b_sr or 22050
    n = min(len(kick_mono), len(bass_mono))
    if n == 0:
        return {
            'status': 'empty_audio',
            'clash_detected': False,
            'phase_cancellation_detected': False,
            'sub_phase_correlation': 0.0,
            'envelope_overlap_ms': 0.0,
            'polarity_inverted_gain_db': 0.0,
            'optimal_delay_ms': 0.0,
            'recommendations': [],
        }

    kick_sub = _lowpass_sub(kick_mono[:n], sr, cutoff_hz=115.0)
    bass_sub = _lowpass_sub(bass_mono[:n], sr, cutoff_hz=115.0)

    k_energy = sum(k * k for k in kick_sub)
    b_energy = sum(b * b for b in bass_sub)
    denom = math.sqrt(k_energy * b_energy)
    sub_corr = (sum(k * b for k, b in zip(kick_sub, bass_sub)) / denom) if denom > 1e-12 else 0.0
    sub_corr = round(max(-1.0, min(1.0, sub_corr)), 4)

    sum_normal_sq = sum((k + b) * (k + b) for k, b in zip(kick_sub, bass_sub)) / n
    sum_invert_sq = sum((k - b) * (k - b) for k, b in zip(kick_sub, bass_sub)) / n
    normal_db = 10.0 * math.log10(max(sum_normal_sq, 1e-12))
    invert_db = 10.0 * math.log10(max(sum_invert_sq, 1e-12))
    polarity_gain_db = round(invert_db - normal_db, 2)

    # Envelope overlap in 10 ms frames
    frame_len = max(1, int(sr * 0.010))
    k_peak = max((abs(k) for k in kick_sub), default=0.0)
    b_peak = max((abs(b) for b in bass_sub), default=0.0)
    k_thresh = max(1e-4, k_peak * 0.25)
    b_thresh = max(1e-4, b_peak * 0.25)
    overlap_frames = 0
    kick_active_frames = 0
    for i in range(0, n - frame_len + 1, frame_len):
        k_env = max(abs(x) for x in kick_sub[i:i + frame_len])
        b_env = max(abs(x) for x in bass_sub[i:i + frame_len])
        if k_env >= k_thresh:
            kick_active_frames += 1
            if b_env >= b_thresh:
                overlap_frames += 1
    envelope_overlap_ms = round(overlap_frames * 10.0, 1)
    overlap_ratio = round(overlap_frames / float(max(1, kick_active_frames)), 3)

    # Search small phase/timing shifts (-10 ms to +10 ms)
    max_shift = max(1, int(sr * 0.010))
    step_shift = max(1, int(sr * 0.001))
    best_shift_samples = 0
    best_shift_sq = sum_normal_sq
    for shift in range(-max_shift, max_shift + 1, step_shift):
        if shift == 0:
            continue
        if shift > 0:
            ks = kick_sub[:n - shift]
            bs = bass_sub[shift:n]
        else:
            s = -shift
            ks = kick_sub[s:n]
            bs = bass_sub[:n - s]
        if ks:
            sq = sum((k + b) * (k + b) for k, b in zip(ks, bs)) / len(ks)
            if sq > best_shift_sq:
                best_shift_sq = sq
                best_shift_samples = shift

    optimal_delay_ms = round((best_shift_samples / float(sr)) * 1000.0, 2)
    delay_gain_db = round(10.0 * math.log10(max(best_shift_sq, 1e-12)) - normal_db, 2)

    kick_pitch = _estimate_pitch_yin(kick_mono[:n], sr)
    bass_pitch = _estimate_pitch_yin(bass_mono[:n], sr)

    phase_cancellation = bool(sub_corr < -0.25 or polarity_gain_db >= 1.5)
    clash_detected = bool(phase_cancellation or (overlap_ratio >= 0.45 and envelope_overlap_ms >= 40.0))

    recommendations: list[dict[str, Any]] = []
    if phase_cancellation:
        recommendations.append({
            'action': 'invert_polarity',
            'gain_improvement_db': polarity_gain_db,
            'reason': f'Sub-band correlation is {sub_corr:.2f}; inverting bass polarity recovers +{polarity_gain_db:.2f} dB of low-end punch.',
        })
    if delay_gain_db >= 0.8 and abs(optimal_delay_ms) > 0.0:
        recommendations.append({
            'action': 'nudge_timing_ms',
            'delay_ms': optimal_delay_ms,
            'gain_improvement_db': delay_gain_db,
            'reason': f'Shifting bass timing by {optimal_delay_ms:+.1f} ms aligns sub phase for +{delay_gain_db:.2f} dB punch.',
        })
    if overlap_ratio >= 0.45 and envelope_overlap_ms >= 40.0:
        recommendations.append({
            'action': 'sidechain_duck_sub',
            'overlap_ms': envelope_overlap_ms,
            'overlap_ratio': overlap_ratio,
            'reason': f'Kick and bass sub envelopes overlap for {envelope_overlap_ms:.0f} ms ({overlap_ratio * 100:.0f}% of kick hits); add 3-5 dB sidechain ducking below 110 Hz.',
        })
    if kick_pitch.get('detected') and bass_pitch.get('detected'):
        cents_diff = round(float(bass_pitch.get('cents_offset', 0.0)) - float(kick_pitch.get('cents_offset', 0.0)), 1)
        if abs(cents_diff) >= 12.0:
            recommendations.append({
                'action': 'retune_cents',
                'recommended_pitch_fine': int(bass_pitch.get('recommended_pitch_fine', 0)),
                'reason': f'Bass cent offset ({bass_pitch.get("cents_offset"):+.1f}c) differs from kick ({kick_pitch.get("cents_offset"):+.1f}c); set bass pitch_fine to {bass_pitch.get("recommended_pitch_fine"):+d}c.',
            })

    severity = 'high' if phase_cancellation else ('medium' if clash_detected else 'low')
    return {
        'status': 'analysed',
        'clash_detected': clash_detected,
        'phase_cancellation_detected': phase_cancellation,
        'severity': severity,
        'sub_phase_correlation': sub_corr,
        'envelope_overlap_ms': envelope_overlap_ms,
        'envelope_overlap_ratio': overlap_ratio,
        'polarity_inverted_gain_db': polarity_gain_db,
        'optimal_delay_ms': optimal_delay_ms,
        'delay_gain_db': delay_gain_db,
        'kick_pitch': kick_pitch,
        'bass_pitch': bass_pitch,
        'recommendations': recommendations,
    }


def _estimate_fundamental_pitch(samples: list[float], sr: int) -> dict[str, Any]:
    """Estimate fundamental pitch for bass/melodic segments up to 1200 Hz."""
    if not samples or sr <= 0:
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': 0.0, 'cents_offset': 0.0}
    min_freq = 32.0
    max_freq = 1200.0
    tau_min = max(2, int(sr / max_freq))
    tau_max = min(len(samples) // 2 - 2, int(sr / min_freq))
    if tau_max <= tau_min:
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': 0.0, 'cents_offset': 0.0}
    W = min(len(samples) - tau_max - 1, max(tau_max + 4, int(sr * 0.045)))
    if W <= tau_min:
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': 0.0, 'cents_offset': 0.0}

    rms = math.sqrt(sum(s * s for s in samples[:W]) / W)
    if rms < 1e-4:
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': 0.0, 'cents_offset': 0.0}

    d = [0.0] * (tau_max + 1)
    cmndf = [1.0] * (tau_max + 1)
    running_sum = 0.0
    for tau in range(1, tau_max + 1):
        diff_sq = 0.0
        for j in range(W):
            delta = samples[j] - samples[j + tau]
            diff_sq += delta * delta
        d[tau] = diff_sq
        running_sum += diff_sq
        cmndf[tau] = (diff_sq * tau / running_sum) if running_sum > 1e-15 else 1.0

    best_tau = None
    for tau in range(tau_min, tau_max):
        if cmndf[tau] < 0.16:
            while tau + 1 <= tau_max and cmndf[tau + 1] < cmndf[tau]:
                tau += 1
            best_tau = tau
            break
    if best_tau is None:
        best_tau = min(range(tau_min, tau_max + 1), key=lambda t: cmndf[t])

    confidence = round(max(0.0, min(1.0, 1.0 - cmndf[best_tau])), 3)
    if confidence < 0.35:
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': confidence, 'cents_offset': 0.0}

    refined_tau = float(best_tau)
    if 1 < best_tau < tau_max:
        s0, s1, s2 = d[best_tau - 1], d[best_tau], d[best_tau + 1]
        denom = 2.0 * (s0 - 2.0 * s1 + s2)
        if abs(denom) > 1e-15:
            shift = (s0 - s2) / denom
            if -1.0 < shift < 1.0:
                refined_tau = best_tau + shift

    fundamental_hz = sr / refined_tau
    if not (30.0 <= fundamental_hz <= 1250.0):
        return {'detected': False, 'midi_note': None, 'fundamental_hz': None, 'confidence': 0.0, 'cents_offset': 0.0}

    midi_exact = 69.0 + 12.0 * math.log2(fundamental_hz / 440.0)
    midi_note = int(round(midi_exact))
    cents_offset = round((midi_exact - midi_note) * 100.0, 2)
    semitone = midi_note % 12
    octave = (midi_note // 12) - 1
    return {
        'detected': True,
        'fundamental_hz': round(fundamental_hz, 2),
        'midi_note': midi_note,
        'note_name': f'{NOTE_NAMES[semitone]}{octave}',
        'pitch_class': NOTE_NAMES[semitone],
        'cents_offset': cents_offset,
        'confidence': confidence,
        'rms': rms,
    }


def transcribe_audio_to_midi(
    path: Path | str,
    *,
    bpm: float = 120.0,
    max_seconds: float = 16.0,
    quantize_grid: float = 0.25,
) -> dict[str, Any]:
    """Segment audio into grid/onset windows and transcribe fundamental pitches to MIDI notes."""
    file_path = Path(path)
    mono, _, sr = _decode_pcm_channels(file_path, max_seconds=max_seconds)
    bpm_val = max(40.0, min(240.0, float(bpm or 120.0)))
    grid_beats = max(0.0625, float(quantize_grid or 0.25))
    sec_per_beat = 60.0 / bpm_val
    step_sec = grid_beats * sec_per_beat
    step_samples = max(64, int(round(sr * step_sec)))

    if not mono or sr <= 0:
        return {
            'path': str(file_path),
            'bpm': bpm_val,
            'quantize_grid': grid_beats,
            'note_count': 0,
            'notes': [],
            'detected_key': None,
            'detected_scale': None,
            'confidence': 0.0,
        }


    peak_rms = 0.0
    window_estimates: list[dict[str, Any]] = []
    num_steps = max(1, int(round(len(mono) / float(step_samples))))
    for step_idx in range(num_steps):
        start_samp = step_idx * step_samples
        end_samp = min(len(mono), start_samp + step_samples)
        seg = mono[start_samp:end_samp]
        if len(seg) < 64:
            continue
        est = _estimate_fundamental_pitch(seg, sr)
        if est.get('detected') and est.get('rms', 0.0) > peak_rms:
            peak_rms = est['rms']
        window_estimates.append({
            'step_idx': step_idx,
            'beat_start': round(step_idx * grid_beats, 4),
            'est': est,
        })

    rms_gate = max(1e-3, peak_rms * 0.15)
    raw_notes: list[dict[str, Any]] = []
    confidences: list[float] = []
    pc_weights: dict[int, float] = {}

    for item in window_estimates:
        est = item['est']
        if not est.get('detected') or est.get('rms', 0.0) < rms_gate:
            continue
        pitch = int(est['midi_note'])
        beat_start = float(item['beat_start'])
        vel = max(45, min(124, int(round(65 + 55 * (est['rms'] / max(1e-6, peak_rms))))))
        confidences.append(float(est['confidence']))
        pc = pitch % 12
        pc_weights[pc] = pc_weights.get(pc, 0.0) + grid_beats

        # Merge contiguous windows of the same pitch unless there was a sharp amplitude re-attack
        if (
            raw_notes
            and raw_notes[-1]['pitch'] == pitch
            and abs((raw_notes[-1]['start'] + raw_notes[-1]['duration']) - beat_start) < 0.001
        ):
            raw_notes[-1]['duration'] = round(raw_notes[-1]['duration'] + grid_beats, 4)
            raw_notes[-1]['velocity'] = max(raw_notes[-1]['velocity'], vel)
        else:
            raw_notes.append({
                'pitch': pitch,
                'start': round(beat_start, 4),
                'duration': round(grid_beats, 4),
                'velocity': vel,
            })

    detected_key = None
    detected_scale = None
    if pc_weights:
        minor_template = (0, 2, 3, 5, 7, 8, 10)
        major_template = (0, 2, 4, 5, 7, 9, 11)
        best_score = -1.0
        for root_pc in range(12):
            for scale_name, tmpl in (('minor', minor_template), ('major', major_template)):
                sc = sum(pc_weights.get((root_pc + iv) % 12, 0.0) for iv in tmpl) + pc_weights.get(root_pc, 0.0) * 0.4
                if sc > best_score:
                    best_score = sc
                    detected_key = NOTE_NAMES[root_pc]
                    detected_scale = scale_name

    avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    return {
        'path': str(file_path),
        'bpm': bpm_val,
        'quantize_grid': grid_beats,
        'note_count': len(raw_notes),
        'notes': raw_notes,
        'detected_key': detected_key,
        'detected_scale': detected_scale,
        'confidence': avg_conf,
    }


def slice_loop_transients(
    path: Path | str,
    *,
    max_slices: int = 16,
    bpm: float = 120.0,
    max_seconds: float = 30.0,
) -> dict[str, Any]:
    """Detect transient onsets and return slice markers with spectral band, pitch labels, and drum-rack MIDI notes."""
    file_path = Path(path)
    mono, _, sr = _decode_pcm_channels(file_path, max_seconds=max(1.0, float(max_seconds or 30.0)))
    duration = round(len(mono) / float(sr), 4) if sr > 0 else 0.0
    bpm_val = max(40.0, min(240.0, float(bpm or 120.0)))
    beats_per_sec = bpm_val / 60.0
    bars_est = max(1, int(round((duration * beats_per_sec) / 4.0))) if duration > 0 else 0
    peak = max((abs(s) for s in mono), default=0.0)
    if not mono or sr <= 0 or duration <= 0.02 or peak < 1e-4:
        return {
            'path': str(file_path),
            'bpm': bpm_val,
            'bars': 0,
            'duration_seconds': duration,
            'slice_count': 0,
            'slices': [],
            'midi_notes': [],
        }

    frame_len = max(1, int(sr * 0.010))
    energies: list[float] = []
    for i in range(0, len(mono) - frame_len + 1, frame_len):
        frame = mono[i:i + frame_len]
        energies.append(math.sqrt(sum(s * s for s in frame) / frame_len))

    flux = [0.0]
    for i in range(1, len(energies)):
        diff = energies[i] - energies[i - 1]
        flux.append(diff if diff > 0.0 else 0.0)

    mean_flux = sum(flux) / max(1, len(flux))
    max_flux = max(flux, default=0.0)
    threshold = max(mean_flux * 1.8, max_flux * 0.12, 0.005)
    min_gap_frames = max(1, int(0.060 / 0.010))
    first_active_frame = next((idx for idx, e in enumerate(energies) if e >= 1e-4), 0)
    onset_samples: list[int] = [first_active_frame * frame_len]
    last_frame = first_active_frame
    for i in range(max(1, first_active_frame + 1), len(flux) - 1):
        if flux[i] >= threshold and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            if i - last_frame >= min_gap_frames:
                onset_samples.append(i * frame_len)
                last_frame = i

    limit = max(1, min(64, int(max_slices or 16)))
    onset_samples = onset_samples[:limit]
    slices: list[dict[str, Any]] = []
    midi_notes: list[dict[str, Any]] = []
    for idx, start_s in enumerate(onset_samples):
        end_s = onset_samples[idx + 1] if idx + 1 < len(onset_samples) else len(mono)
        seg = mono[start_s:end_s]
        band_info = _compute_band_energy(seg, sr)
        pitch_info = _estimate_fundamental_pitch(seg, sr)
        start_sec = round(start_s / float(sr), 4)
        end_sec = round(end_s / float(sr), 4)
        start_beat = round(start_sec * beats_per_sec, 4)
        dur_beat = round(max(0.0625, (end_sec - start_sec) * beats_per_sec), 4)
        seg_rms = math.sqrt(sum(s * s for s in seg) / max(1, len(seg)))
        vel = max(55, min(124, int(round(70 + 50 * min(1.0, seg_rms * 2.5)))))
        slices.append({
            'slice_index': idx,
            'start_seconds': start_sec,
            'end_seconds': end_sec,
            'start_beat': start_beat,
            'duration_beats': dur_beat,
            'dominant_band': band_info.get('dominant_band', 'mid'),
            'note_name': pitch_info.get('note_name'),
            'midi_note': pitch_info.get('midi_note'),
            'cents_offset': pitch_info.get('cents_offset', 0.0),
        })
        midi_notes.append({
            'pitch': min(127, 36 + idx),
            'start': start_beat,
            'duration': dur_beat,
            'velocity': vel,
            'mute': False,
        })

    return {
        'path': str(file_path),
        'bpm': bpm_val,
        'bars': bars_est,
        'duration_seconds': duration,
        'slice_count': len(slices),
        'slices': slices,
        'midi_notes': midi_notes,
    }

