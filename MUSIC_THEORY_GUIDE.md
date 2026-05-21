# Vibelton: The Producer's Music Theory Manual (v3.0)

This manual documents the comprehensive electronic music theory knowledge, data models, and rhythmic/harmonic algorithms implemented in Vibelton. It bridges classical music theory with contemporary and underground electronic music production workflows in Ableton Live.

---

## 1. Fundamentals of Notes, Pitch Classes & Key Resolution

Vibelton maps the 12 chromatic pitches to integer pitch classes ($0$ to $11$), starting from C.

### Pitch Class Mapping
- **C / B♯**: 0
- **C♯ / D♭**: 1
- **D**: 2
- **D♯ / E♭**: 3
- **E / F♭**: 4
- **E♯ / F**: 5
- **F♯ / G♭**: 6
- **G**: 7
- **G♯ / A♭**: 8
- **A**: 9
- **A♯ / B♭**: 10
- **B / C♭**: 11

### Camelot Wheel DJ-Mixing Key Mapping
For seamless integration with DJ mixing and live performance workflows, Vibelton maps all scales to both standard keys and Camelot Mixing Wheel positions. 

| Pitch Class (Minor Root) | Minor Key Name | Camelot Code | Pitch Class (Major Root) | Major Key Name | Camelot Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 9 | A minor | 8A | 0 | C major | 8B |
| 4 | E minor | 9A | 7 | G major | 9B |
| 11 | B minor | 10A | 2 | D major | 10B |
| 6 | F♯ minor | 11A | 9 | A major | 11B |
| 1 | C♯ minor | 12A | 4 | E major | 12B |
| 8 | G♯ minor | 1A | 11 | B major | 1B |
| 3 | D♯ minor | 2A | 6 | F♯ major | 2B |
| 10 | A♯ minor | 3A | 1 | C♯ major | 3B |
| 5 | F minor | 4A | 8 | A♭ major | 4B |
| 0 | C minor | 5A | 3 | E♭ major | 5B |
| 7 | G minor | 6A | 10 | B♭ major | 6B |
| 2 | D minor | 7A | 5 | F major | 7B |

> [!TIP]
> **Harmonic Transition Rules**:
> - **Relative Transition**: Toggle between Minor and Major by keeping the number identical and switching letters (e.g., `8A` (A minor) $\leftrightarrow$ `8B` (C major)). This maintains the identical scale signature (zero sharps or flats).
> - **Perfect Fifth Shift**: Add or subtract 1 to the number to shift a perfect fifth up or down (e.g., `8A` (A minor) $\leftrightarrow$ `9A` (E minor) or `7A` (D minor)). These adjacent keys share 6 out of 7 scale tones, ensuring flawless, low-tension harmonic blends.

---

## 2. The Producer's Scale & Mode Master Matrix

Scale formulas are modeled as arrays of semitones relative to the root pitch class ($0$). Choosing a scale determines the emotional baseline of the track.

| Scale/Mode | Semitone Formula | Harmonic Character | Production Vibe & Emotional Color | Primary Genres | Prominent Artists |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Major (Ionian)** | `(0, 2, 4, 5, 7, 9, 11)` | Diatonic Triads | Bright, triumphant, celebratory, commercial | Pop, Progressive House, Euro-Trance | Avicii, Swedish House Mafia |
| **Natural Minor (Aeolian)** | `(0, 2, 3, 5, 7, 8, 10)` | Sad turnarounds | Melancholic, cinematic, reflective, driving | Liquid DnB, Melodic Techno, Synthwave | Jon Hopkins, Tale Of Us |
| **Dorian Mode** | `(0, 2, 3, 5, 7, 9, 10)` | Sophisticated `IV` major | Jazzy, soulful, deep-grooved, nostalgic, cool | Classic Deep House, UK Garage, Detroit Techno | Disclosure, Kerri Chandler |
| **Phrygian Mode** | `(0, 1, 3, 5, 7, 8, 10)` | Dark $\flat\text{II}$ triad | Tense, industrial, hypnotic, aggressive | Dark Techno, Psytrance, UK Drill, Trap | Charlotte de Witte, Rezz |
| **Lydian Mode** | `(0, 2, 4, 6, 7, 9, 11)` | Raised $\sharp\text{IV}$ degree | Dreamy, spacey, ethereal, cinematic wonder | Leftfield Ambient, Progressive Dream-Trance | Aphex Twin, Tycho |
| **Mixolydian Mode** | `(0, 2, 4, 5, 7, 9, 10)` | Flat $\flat\text{VII}$ stab | Funky, bluesy, unresolving club energy | French House, Disco House, Afro-House | Daft Punk, Black Coffee |
| **Locrian Mode** | `(0, 1, 3, 5, 6, 8, 10)` | Diminished $\flat\text{V}$ | Unstable, post-apocalyptic, high-tension | Experimental, Industrial Techno, Leftfield Noise | Autechre, Lorn |
| **Harmonic Minor** | `(0, 2, 3, 5, 7, 8, 11)` | Tension-inducing leading note | Classical tragedy, dramatic, tense resolutions | Symphonic Techno, Gothic House, Trance | Boris Brejcha, Armin van Buuren |
| **Phrygian Dominant** | `(0, 1, 4, 5, 7, 8, 10)` | Raised 3rd in Phrygian | Middle-Eastern vibe, highly aggressive, exotic | Hard Techno, Acid Trance, Psytrance | Astrix, Amelie Lens |
| **Lydian Dominant** | `(0, 2, 4, 6, 7, 9, 10)` | Raised 4th, Flat 7th | Futuristic, alien, jazz-fusion, unstable | Leftfield Bass, Wonky, IDM | Flying Lotus, Hudson Mohawke |
| **Double Harmonic Major** | `(0, 1, 4, 5, 7, 8, 11)` | Double augmented 2nds | High psychedelic tension, exotic, ritualistic | Psytrance, Industrial, Acid Techno | Infected Mushroom |
| **Minor Pentatonic** | `(0, 3, 5, 7, 10)` | No half steps | Spacious, raw, feedback-friendly, dubby | Dubstep, Dub Techno, Minimal | Mala, Deepchord |

---

## 3. Extended Chord Progression Library by Genre

Chords are configured using semitone interval offsets stacked above a root note. Moving away from standard triads and employing extended chord types creates professional, release-ready harmonics.

### Extended Chord Formulas
- **Suspended Second (sus2):** `(0, 2, 7)` — Airy, transitional; removes gender (neither major nor minor).
- **Suspended Fourth (sus4):** `(0, 5, 7)` — Classic rhythmic tension builder. Excellent for UK Garage stabs.
- **Minor Seventh (m7):** `(0, 3, 7, 10)` — Moody foundation for all deep genres.
- **Major Seventh (Maj7):** `(0, 4, 7, 11)` — Bright, nostalgic, premium.
- **Minor Ninth (m9):** `(0, 3, 7, 10, 14)` — Essential for Deep House, UKG, and Amapiano. Elegant and rich.
- **Major Ninth (Maj9):** `(0, 4, 7, 11, 14)` — Warm, sophisticated, soulful.
- **Dominant Ninth (9):** `(0, 4, 7, 10, 14)` — Bluesy, driving, highly functional.
- **Minor Eleventh (m11):** `(0, 3, 7, 10, 14, 17)` — Ethereal space, jazz-fusion electronic chords.
- **Dominant Seventh Flat-9 (7b9):** `(0, 4, 7, 10, 13)` — Gothic, intense turnaround resolution.

### Modular Chord Progressions

#### 1. Soulful Deep House & Organic House
*Focuses on emotional weight and smooth transitions. Rich 7th and 9th chord structures.*
- **Progression 1 (Dorian Soul)**: `ii9` $\rightarrow$ `v9` $\rightarrow$ `Imaj9` $\rightarrow$ `IVmaj9`
  - *Roman*: `ii9` $\rightarrow$ `v9` $\rightarrow$ `Imaj9` $\rightarrow$ `IVmaj9`
  - *Semitones*: `[2, 5, 9, 12, 16]` $\rightarrow$ `[7, 10, 14, 17, 21]` $\rightarrow$ `[0, 4, 7, 11, 14]` $\rightarrow$ `[5, 9, 12, 16, 19]` (relative to key signature)
- **Progression 2 (Classic Uplift)**: `i7` $\rightarrow$ `IV7` $\rightarrow$ `VImaj7` $\rightarrow$ `v9`
  - *Roman*: `i7` $\rightarrow$ `IV7` $\rightarrow$ `VImaj7` $\rightarrow$ `v9`

#### 2. UK Garage & Speed Garage
*Jazzy, skippy stabs. Typically utilizes parallel chord transposition or suspended chords.*
- **Progression 1 (Parallel Stab Shift)**: `i9` $\rightarrow$ `bVII9` $\rightarrow$ `iv9` $\rightarrow$ `v9`
  - *Shorthand*: Shift the identical minor 9th finger shape (`0, 3, 7, 10, 14`) intact along the roots: `0` $\rightarrow$ `-2` $\rightarrow$ `5` $\rightarrow$ `7`.
- **Progression 2 (UKG Turnaround)**: `ii7` $\rightarrow$ `V9` $\rightarrow$ `Imaj7` $\rightarrow$ `vi9`
  - *Vibe*: Highly melodic, reminiscent of classic 90s London club tracks.

#### 3. Melodic Techno & Progressive House
*Hypnotic, cyclical loops that maintain harmonic suspense without resolved endings.*
- **Progression 1 (The Unresolving Loop)**: `i` $\rightarrow$ `VImaj7` $\rightarrow$ `iv9` $\rightarrow$ `v_sus4`
  - *Semitones*: `[0, 3, 7]` $\rightarrow$ `[8, 12, 15, 19]` $\rightarrow$ `[5, 8, 12, 15, 19]` $\rightarrow$ `[7, 12, 14]`
- **Progression 2 (Dorian Suspense)**: `i` $\rightarrow$ `bVII` $\rightarrow$ `IV` $\rightarrow$ `iv`
  - *Vibe*: Keeps the listener locked in a state of continuous, driving motion.

#### 4. Amapiano & Afro House
*Static jazzy structures, rhythmic stabs, and sparse chord layouts that let the log drum breathe.*
- **Progression 1 (Sultry Dyads)**: `i9` $\rightarrow$ `iv11` (Static alternating sequence)
  - *Semitones*: `[0, 3, 10, 14]` $\rightarrow$ `[5, 8, 15, 17]`
- **Progression 2 (Afro-Jazz Movement)**: `i7` $\rightarrow$ `bVIImaj7` $\rightarrow$ `v7` $\rightarrow$ `VImaj7`

#### 5. Synthwave, Outrun & Retrowave
*Uplifting major chords layered with driving minor roots. Highly emotional and cinematic.*
- **Progression 1 (The 80s Hero)**: `i` $\rightarrow$ `bVII` $\rightarrow$ `bVI` $\rightarrow$ `bVII`
  - *Roman*: `i` $\rightarrow$ `VII` $\rightarrow$ `VI` $\rightarrow$ `VII`
  - *Semitones*: `[0, 3, 7]` $\rightarrow$ `[10, 14, 17]` $\rightarrow$ `[8, 12, 15]` $\rightarrow$ `[10, 14, 17]` (e.g., A minor $\rightarrow$ G major $\rightarrow$ F major $\rightarrow$ G major)
- **Progression 2 (Modal Outrun)**: `i` $\rightarrow$ `bIII` $\rightarrow$ `IV` $\rightarrow$ `bVI`
  - *Note*: Major `IV` chord in a minor key triggers the cinematic Dorian lift.

#### 6. Dubstep, Grime & UK Drill
*High-tension modal substitution chords. Focuses heavily on semitone friction.*
- **Progression 1 (The Phrygian Tension)**: `i` $\rightarrow$ `bII` $\rightarrow$ `i` $\rightarrow$ `vii`
  - *Semitones*: `[0, 3, 7]` $\rightarrow$ `[1, 5, 8]` (Neapolitan) $\rightarrow$ `[0, 3, 7]` $\rightarrow$ `[11, 2, 5]` (Diminished)
- **Progression 2 (Locrian Friction)**: `i` $\rightarrow$ `bV` $\rightarrow$ `iv` $\rightarrow$ `bII`

---

## 4. Rhythm Grids & Advanced Drum Programming

Micro-timing and humanization groove are key. Electronic grooves are modeled using explicit 16th-note subdivision offsets measured in beats (where $1.0\text{ beat} = 480\text{ PPQ ticks}$ in standard DAW coordinates).

### The Standard 4/4 16th-Note Grid (480 Ticks per Quarter Note)
- **Beat 1**: `0.0` (Tick `0`)
- **Beat 1.25 (16th offbeat)**: `0.25` (Tick `120`)
- **Beat 1.5 (8th offbeat)**: `0.5` (Tick `240`)
- **Beat 1.75 (16th offbeat)**: `0.75` (Tick `360`)

```
Step:  1   2   3   4  |  5   6   7   8  |  9  10  11  12  | 13  14  15  16
Beat: 0.0 .25 .50 .75 | 1.0 1.25 1.50 1.75 | 2.0 2.25 2.50 2.75 | 3.0 3.25 3.50 3.75
Tick:  0  120 240 360 | 480 600  720  840  | 960 1080 1200 1320 | 1440 1560 1680 1800
```

### Rhythmic Groove DNA Models

```carousel
#### 1. UK Garage 2-Step / Skippy Shuffle
- **Push/Pull subdivisions**: Push even 16th subdivisions (subdivisions 1 and 3, which are index 1 and index 3 of each beat) late by $+20$ ticks (`+0.0417` beats). This delays the "e" and "a" of the beat, creating a skippy, rolling swing.
- **Weak-beat Curve**: `(1.0, 0.65, 0.9, 0.9)` (Accent downbeats perfectly, dip the first offbeat to 65% to let the snare breathe, spike the final subdivision to 90% to push into the next beat).
- **Rhythmic Blueprint**:
  - Kick: `[0.0, 2.5]` (Beat 2 and Beat 4 kicks are completely deleted).
  - Snare/Clap: Landing crisply on `[1.0, 3.0]`.
  - Percussive ghost hits and rimshots are placed on delayed 16th positions.
<!-- slide -->
#### 2. MPC 58% Swing (Hip-Hop & House Classic)
- **Push/Pull subdivisions**: Shift even-numbered 16th notes (indices 1 and 3) late by $+32$ ticks (`+0.0667` beats). All odd subdivisions stay straight. This is the definitive "MPC Swing" formula popularized by Roger Linn.
- **Rhythmic Blueprint**:
  - Kick: `[0.0, 1.0, 2.0, 3.0]` (Straight 4-on-the-floor for House) or syncopated `[0.0, 2.5, 3.25]` for Boom-Bap.
  - Hi-hats: Straight on downbeats, but heavily swung on subdivisions 1 and 3, generating that organic, swaying "bounce".
<!-- slide -->
#### 3. Dembow / Afrobeats Clave Sequence
- **Push/Pull subdivisions**: Keep swing tight to straight (`dembow` groove profile).
- **Weak-beat Curve**: `(1.0, 0.65, 0.95, 0.95)`.
- **Rhythmic Blueprint**:
  - Linear $3\text{-}3\text{-}2$ Clave Grid: Accents land strictly on steps 1, 4, 7, 9, 12, 15 of the 16-step grid.
  - Translated to beats: `[0.0, 0.75, 1.5, 2.0, 2.75, 3.5]`.
  - In Reggaeton: The kick follows `[0.0, 1.5, 2.5]`, while the snare rim stab emphasizes `[0.75, 1.75, 2.75, 3.75]` (steps 4, 8, 12, 16).
<!-- slide -->
#### 4. Drum & Bass / Jungle Breakbeat Programming
- **Push/Pull subdivisions**: Extremely tight, fast micro-timing (`dnb_tight`). Push even subdivisions slightly early to pull the groove forward (e.g., `-0.005` beats).
- **Rhythmic Blueprint**:
  - Classic 2-Step DnB Kick/Snare pattern:
    - Kick: `[0.0, 2.5]` (Step 1, and the syncopated step 11 offbeat).
    - Snare: `[1.0, 3.0]` (Step 5 and Step 13).
  - Amen Break Chopped Grid: High-speed, syncopated ride and snare ghosts filling steps 3, 4, 7, 8, 10, 12, 15.
<!-- slide -->
#### 5. Irregular / Generative IDM Grids (Aphex Twin / Autechre)
- **Push/Pull subdivisions**: Unconventional, utilizing prime numbers or mathematical curves (e.g., Fibonacci acceleration where subdivisions get progressively pushed closer to the beat).
- **Rhythmic Blueprint**:
  - Irregular Time Signatures: Compressing the standard bar into $5/4$ (`length_beats = 5.0`) or $7/8$ (`length_beats = 3.5`).
  - Euclidean Rhythms: Spacing $k$ hits across $n$ steps as evenly as possible. For example, $E(5,8)$ generates a syncopated pattern: `[0.0, 0.75, 1.25, 2.0, 2.75]`.
```

---

## 5. Arrangement & Structural Blueprints

Electronic music arrangement is designed around tension-and-release cycles (usually structured in multiples of 8 or 16 bars) that coordinate DJ-friendly mixing transitions and club-focused peak points.

### Arrangement Chart: 4 Classic Tension-Release Profiles

```mermaid
grid
```

#### Blueprint 1: The Club Journey (Hypnotic / Dub Techno)
Designed for continuous momentum, subtle dynamic growth, and long DJ blending zones.

```
[0.0 - 16.0 Bars]     DJ Intro: Kick & offbeat hi-hat only. Continuous synth rumble. Low energy.
[16.0 - 48.0 Bars]    Groove Build: Introduce modular percussion loop. Open filters on chords.
[48.0 - 64.0 Bars]    Tension Breakdown: Drop the kick. Chord stabs open up with delay automation.
[64.0 - 96.0 Bars]    Peak Drop: Heavy kick returns. Introduce sharp white-noise hats. High energy.
[96.0 - 112.0 Bars]   Groove Reduction: Snare rolls stop. Kick drum filtered down. Bassline drops.
[112.0 - 128.0 Bars]  DJ Outro: Only kick drum and sustained ambient pad remains. Fades out.
```

#### Blueprint 2: The Pop Hook (Future Bass / Melodic House)
Designed for high dramatic contrast between sparse verses, rising builds, and maximum-impact drops.

```
[0.0 - 8.0 Bars]      Ambient Intro: Acoustic piano chords or soft vocal texture. No drums.
[8.0 - 24.0 Bars]     Verse A/B: Soft kick drum enters. Sub-bass plays long root notes.
[24.0 - 32.0 Bars]    Pre-Chorus Build: Snares double in speed. Pitches glide upward. Vocal rise.
[32.0 - 48.0 Bars]    The Drop: Huge supersaw chords, heavy bass drops, and full drum kit.
[48.0 - 56.0 Bars]    Breakdown: Drums stop completely. Sustained pad and solo vocal element.
[56.0 - 64.0 Bars]    DJ Outro: Simple drum loop and bassline. Harmonically resolving.
```

#### Blueprint 3: The Skippy Flow (UK Garage / 2-Step)
Designed for swinging, vocal-led club vibes with sudden rhythmic transitions.

```
[0.0 - 16.0 Bars]     DJ Intro: Skippy swung hats and sub-bass. Soft kick on step 1.
[16.0 - 24.0 Bars]    Verse A: Vocal hook enters. Light Rhodes keyboard parallel stabs.
[24.0 - 32.0 Bars]    Build: Pitch-shifted vocal rise. Low-pass filter sweeps on the drum bus.
[32.0 - 48.0 Bars]    Main Drop: 2-Step kick kicks in. Full sub-bass bounce. Soulful vocals.
[48.0 - 56.0 Bars]    Rhythmic Breakdown: Claps and snares drop. Only kick and hats continue.
[56.0 - 64.0 Bars]    Outro: Fades into simple rimshot percussion and filter sweeps.
```

#### Blueprint 4: The Generative Leftfield Arc (IDM / Ambient)
Non-formulaic structure that evolves progressively without standard drops, utilizing asymmetrical phrases.

```
[0.0 - 12.0 Bars]     Asymmetric Phrase A: Generative FM plucks playing in 5/4 time.
[12.0 - 28.0 Bars]    Progressive Shift: Complex glitch percussion enters. Random velocity.
[28.0 - 40.0 Bars]    Polyrhythmic Bridge: Heavy sub-bass drone enters. Plucks transition.
[40.0 - 56.0 Bars]    Generative Outro: Ambient noise filters slowly wash away the instruments.
```

---

## 6. Monophonic Basslines & Sub-Bass Engineering

The low-frequency range (MIDI pitch 24 to 55 / $32\text{ Hz}$ to $146\text{ Hz}$) is highly sensitive. To prevent muddy, phase-cancelled mixes, Vibelton enforces strict Register Formatting constraints.

### Critical Sub-Bass Rules
1. **The Low Interval Limit (LIL)**: Below $100\text{ Hz}$ (MIDI pitch 43 / G2), interval stacking is strictly forbidden. Basslines must be completely **monophonic**. No thirds, fourths, or fifths allowed.
2. **Kick/Bass Alignment**: Sidechain compression, envelope ducking, or MIDI offset programming must be used when the kick and sub-bass land on the identical beat position.
3. **Octave Jumps for Portamento**: Classic sub-bass slides must be drawn using high-velocity notes placed an octave or two higher, overlapping the root note's tail to trigger legato portamento.

### Sub-Bass Syntheses & Shorthands

```carousel
#### 1. Trap & Drill 808 Glides
- **Formula**: Saturated, monophonic sine wave with a moderate decay.
- **Rhythmic Rule**: Lock the first hit to the downbeat kick. Apply sudden pitch glides on syncopated 16th subdivisions by overlapping notes transposed $+12$ or $+24$ semitones.
- **MIDI Example**: Note 1 (`start=0.0`, `duration=0.9`, `pitch=36`), overlapping Note 2 (`start=0.8`, `duration=0.4`, `pitch=48`, `velocity=115`) to trigger a perfect octave sweep slide in the DAW.
<!-- slide -->
#### 2. Amapiano Log Drum Engine
- **Formula**: Saturated sub-bass paired with a sharp FM marimba attack transient.
- **Rhythmic Rule**: Avoid downbeats. Log drums operate in dynamic call-and-response against the percussion, playing fast 16th-note double strikes or triplets.
- **MIDI Example**: Triplet tap on steps 7, 8, 9: `[1.5, 1.625, 1.75]` using deep square-wave pitches between 28 and 38.
<!-- slide -->
#### 3. Drum & Bass Reese Bass
- **Formula**: Two or more slightly detuned, low-passed sawtooth waves creating a thick, chorused movement.
- **Rhythmic Rule**: Sustained, long-form drones. Reese notes typically hold across 4 to 8 bars, modulating filter cutoff envelopes rather than switching pitches rapidly.
- **MIDI Example**: `Note(pitch=33, start=0.0, duration=15.75)`.
<!-- slide -->
#### 4. Psytrance Rolling Triplet Bass
- **Formula**: Punchy, short-decay analog saw wave locked strictly behind the kick.
- **Rhythmic Rule**: Kick lands straight on every quarter beat (`0.0, 1.0, 2.0, 3.0`). Bass hits three consecutive times on the 16th offbeats directly after the kick, skipping the downbeat to allow the kick's transient to pop.
- **MIDI Example**: Kick on `0.0`, Bass on `[0.25, 0.5, 0.75]` with short durations `0.18`.
```

---

## 7. Intelligent Voicing & Voice Leading Rules

To make chord progressions sound organic and expensive, Vibelton manages note voicing transitions automatically through two mathematically distinct algorithms.

```
[Soprano]  MIDI 67-84  -----------------------> Leads, Hooks, Plucks
[Alto]     MIDI 55-72  -----------------------> Counter-melodies, Upper Chords
[Tenor]    MIDI 42-60  -----------------------> Pad Foundations, Chord Roots
[Bass]     MIDI 24-48  -----------------------> Sub-Bass, 808s, Log Drums
```

### Mode A: Classical Smooth Inversion (`best_inversion`)
Optimized for Ambient pads, Pop progressions, and Trance hooks. It minimizes physical finger movement, ensuring transitions are smooth and natural.
1. Generate all possible inversions of the target chord across neighboring octaves.
2. Calculate the cumulative semitone distance delta relative to the previously voiced chord:
   $$\text{Distance} = \sum_{j=1}^{N} |P_{\text{current}, j} - P_{\text{previous}, j}|$$
3. Select the inversion that minimizes physical travel, keeping the voice grouping compact and compact.

### Mode B: Parallel Sampling Shift (`parallel_motion`)
Optimized for Deep House, UK Garage, Detroit Techno, and Jungle.
1. Lock the initial chord voicing to the exact interval structure specified by the user prompt (e.g., Root Position Minor 9th: `0, 3, 7, 10, 14`).
2. Do not invert or alter internal note gaps when the progression shifts chords.
3. Move the entire geometric chord shape up or down intact, matching the new root pitch class.

> [!NOTE]
> **Production Heritage**: Parallel shifting replicates the classic sound of hardware samplers (e.g., AKAI S1000). Producers in the 90s would sample a single chord stab, map it across the keyboard, and play progressions. Transposing the sample shifted the filters, grain, and speeds together, creating the warm, locked-harmony vibe of house music.

---

## 8. Ableton Live Native MIDI Tool Strategies

Implement these electronic music theory concepts inside Ableton Live using native MIDI effects and editing workflows.

### 1. Scale MIDI Effect (Lock Inputs to Keys)
Never hit a wrong note during live performance or generative sequencing.
1. Search for the **Scale** device in the MIDI Effects browser and drag it onto your instrument track.
2. Configure the 12x12 grid to map input semitones to your target mode. For example, to lock to **Dorian**, choose the Dorian preset.
3. Keep your input MIDI keys straight (white keys); the Scale effect will automatically transpose off-scale notes to the nearest in-scale Dorian pitches.

### 2. Chord MIDI Effect (The Parallel Stab Generator)
Generate massive, authentic stabs with a single MIDI note trigger.
1. Drag the **Chord** MIDI effect before your synthesizer or sampler.
2. To create the iconic **Minor 9th Stab**, set the Shift controls to:
   - **Shift 1**: `+3st` (Minor Third)
   - **Shift 2**: `+7st` (Perfect Fifth)
   - **Shift 3**: `+10st` (Minor Seventh)
   - **Shift 4**: `+14st` (Major Ninth)
3. Set your synth to monophonic mode. Now, playing a single key will trigger a flawless, parallel minor 9th chord, replicating Mode B's sampling shift instantly.

### 3. Velocity MIDI Effect (Adding Rhythmic Humanization)
Give mechanical MIDI patterns the soft dynamics of a real session musician.
1. Insert the **Velocity** device at the start of your MIDI chain.
2. Set **Drive** to a low value ($5\% - 15\%$) to add soft random dynamics.
3. Adjust **Random** to $10 - 25$. This adds randomized volume fluctuations on every single strike, mimicking Vibelton's groove profiles and making your hi-hat and snare rolls sound organic.

### 4. Extracting Ableton Grooves (.agr)
Capture the micro-timing feel of legendary swing hardware directly onto your DAW grid.
1. Right-click on any drum audio loop with a great feel (e.g., a classic MPC loop or a UKG drum loop) and select **Extract Groove(s)**.
2. This creates an `.agr` groove template inside your project's Groove Pool.
3. Drag your MIDI clips into the Groove Pool, or click **Commit** in the Clip View to permanently apply the micro-timing push/pull and velocity curves to your MIDI notes.