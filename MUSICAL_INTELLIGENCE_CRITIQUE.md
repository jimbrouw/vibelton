# Vibelton — Musical Intelligence Critique & Upgrade Plan

> For Jim. No code in this doc. This is the brief you hand to the AI coding assistant.
> Status labels follow Jim's house rules: [Inference], [Unverified], [Speculation].

---

## TL;DR

- **Yes, niche down. Start with House and its sub-genres.** Going broad now will lock in "samey" everywhere. Get House right, then copy the template into DnB, then Trap.
- **The robotic feel is not a genre-data problem. It's an architecture problem.** Every part picks one pattern at the start and repeats it. Fix that first.
- **Three fixes give 80% of the perceived improvement**: (1) bar-to-bar pattern variation, (2) section-aware reharmonisation, (3) a transitions library (fills, drops, risers, kick-drops).

If you only act on three things, act on those three.

---

## 1. What's making it sound robotic — read this first

Based on reading `vibelton/genre_dna.py`, `vibelton/actions.py` (the `genre_drums`, `genre_bassline`, `genre_chords`, `genre_lead` functions), and `vibelton/planner.py` (`expanded_song_sketch_plan`).

### 1.1 One pattern per part, picked once, repeated forever

`pick_pattern(patterns, seed)` returns a single variant chosen by hashing the prompt. That same kick/snare/hat/bass/chord/lead pattern then plays on bar 1, bar 2, bar 3 ... bar 16 of a section. A real producer changes patterns roughly every 2, 4 or 8 bars.

[Inference] This is the single biggest reason it sounds like a loop instead of a track.

### 1.2 Bar-to-bar mutation is almost zero

In `genre_drums` the only variation across bars is:
- A probabilistic hat drop based on `bar % 4`.
- A snare fill on the last bar of every 4.

There is no programmed kick drop, no opening hi-hat for one bar, no tom roll, no ride swap, no crash on the "1" of a new section, no clap-doubling, no snare-edit.

### 1.3 Chord progression never changes between sections

`genre_chords` reads `COMMON_PROGRESSIONS[mode]` once and cycles it. Intro, build, drop, break, drop 2, outro — all the same chords. Real tracks reduce to one chord in the drop, drop to two chords in the breakdown, modulate up a semitone or tone for the final chorus, or borrow from the parallel mode in the break.

### 1.4 The energy axis only nudges velocity and duration

`energy = "intro" / "build" / "main" / "break"` reduces velocity by a fixed amount and lengthens notes. It doesn't change which notes play, which voicing is used, which octave the bass sits in, or whether the kick is present.

### 1.5 The curated genre grammar isn't wired into the generator

`CURATED_GENRES` has lovely prose — `rules`, `rule_breakers`, `vibe_words` — but the local generator never reads `rules` or `rule_breakers`. That text is only injected into the OpenAI prompt. So if a user doesn't have an API key (the default), the "rule-breaker" instructions never affect what gets generated.

### 1.6 Voice leading is implemented, but reharmonisation is not

`harmony.py` is good work — Mode A (`best_inversion`) and Mode B (`parallel_motion`) are described in `MUSIC_THEORY_GUIDE.md` and they're real techniques. But there's no modulation, no borrowed chord substitution between sections, no II-V-I turnaround into the drop.

### 1.7 No transitions — risers, fills, drops, sweeps — outside the Finisher

The Finisher inserts riser and crash clips. The Song Maker (`expanded_song_sketch_plan`) doesn't. So a song-sketch arrangement has nothing connecting one section to the next: it just stops and the next pattern starts.

### 1.8 MIDI library is "match by name then use as-is"

`midi_library.py` finds the first file whose filename or folder contains the style word. It doesn't fit to key, doesn't blend two clips, doesn't pick different clips for different sections, doesn't pick longer/shorter versions for build vs drop.

### 1.9 Each "genre" is one DNA, not a family

`HOUSE` is one profile, but `house` covers Deep House, Tech House, Garage House, Afro House, Future House, Bass House, Disco House, Progressive — and they're musically very different. Same with DnB (Liquid, Neurofunk, Jump-Up, Half-Time, Minimal, Ragga Jungle), Trap (Atlanta, Drill, Phonk, Plug, Rage), Hip-Hop (Boom-Bap, Lo-Fi, West Coast, Trap-influenced).

### 1.10 Your own listening notes already flagged this

From `LISTENING_NOTES.md`, 2026-04-30: *"genre sameness on trap/ambient"*. 2026-05-01: *"prompts 5/8 sounding too harmonically similar"*. You already know.

---

## 2. Niche down or stay broad? — direct answer

**Niche down. Start with House. Then DnB. Then Trap. Hip-Hop is mostly a re-skin of Boom-Bap-flavoured Trap.**

Reasons, ranked:

1. **You already feel the sameness.** Going broader without a deeper template just multiplies sameness across more genres.
2. **House is your strongest existing data.** The chord/bass/lead patterns are most idiomatic for House (your `HOUSE` profile and Disclosure-flavoured UK Garage). Polish what's already closest to working.
3. **The fix is architectural, not data-entry.** Once Vibelton has a working "House family" (sub-genre selector, multi-bar pattern variation, section-aware reharmonisation, transitions library), the same template copies into DnB and Trap with mostly data swaps.
4. **Sub-genre is how producers actually search and brief.** "Make me a Deep House track" is what you'd say. "Make me a House track" is what nobody says.

[Inference] The risk of going broad first is locking in "1 pattern per genre" forever, because the cost of adding sub-genres later goes up the more genres exist. Better to set the precedent now.

---

## 3. The three foundational fixes (do these first, before sub-genre work)

These are the 80% wins. They apply to every genre. Build them before you touch sub-genres.

### Fix 1 — Multi-bar pattern variation engine

**Problem:** every part plays one pattern for the whole section.

**What to build:**
- For each part (kick, snare, hat, bass, chord, lead), each genre profile defines a small *bank* of pattern variants (typically 2-6, which already partly exists for kick/snare/hat).
- Add a **mutation schedule** that says, for each bar of a section: "use variant A for 2 bars, B for 2 bars, drop the pattern entirely on bar 7, fill on bar 8". Bars 9-16 mirror with one variant swap.
- Each variant in the bank is tagged: `base`, `dropout`, `fill`, `pickup`, `accent`, `ghost`, `roll`. The mutation schedule picks tags, not specific patterns, so it generalises across genres.
- Default schedules (per genre or sub-genre): "AABB+fill", "ABAC", "AAAA+ghost", "AAAB", "intro reduce", "build add". One schedule per energy section.

**Why it matters:** instantly stops the "looped clip" feel without needing more sophisticated music theory.

[Inference] This alone will get rid of about half the "robotic" perception.

### Fix 2 — Section-aware reharmonisation

**Problem:** the chord progression is identical in intro, drop, break, and outro.

**What to build:**
- Each genre/sub-genre defines **section-specific progressions**, not one progression for the whole track:
  - `intro` — minimal: hold root chord, or root + IV.
  - `verse` — main progression (full 4-chord cycle).
  - `build` — last 2 bars reharmonise to V (or bVII for modal genres), priming the drop.
  - `drop` — often reduces to fewer chords (House: 2 chords; Trap: 1 chord pad; DnB: sustained Reese root + bVI bloom).
  - `break` — borrow from parallel mode (parallel minor in a major key, or vice versa), or use a IVmaj7 / bVImaj7 substitution for "lift".
  - `drop 2` — same as drop, optionally transposed +2 semitones for "lift" (very common in House and Trance).
  - `outro` — resolve on tonic, hold.
- Tie this to your `CuratedGenreDNA.structure` so each section gets a different chord intent.

**Why it matters:** even with identical drums, the perceived song narrative jumps from flat to dynamic. Listeners hear "lift" and "release", not just "louder".

### Fix 3 — Transitions library (fills, risers, sweeps, kick-drops)

**Problem:** sections stop and start without connective tissue.

**What to build:**
- A small library of *transition events* that get inserted at section boundaries:
  - `snare_roll` — last 2 bars of build, accelerating 8th → 16th → 32nd snares with velocity ramp.
  - `kick_drop` — final 1 bar of build, kick muted, leaves space for impact.
  - `reverse_cymbal` — final 1 beat of build (single negative-time hit).
  - `riser` — 4 or 8 bar white-noise sweep, encoded as a single high-pitched note with velocity ramp on a "Riser" track.
  - `crash` — bar 1 beat 1 of every drop and drop 2.
  - `tom_fill` — last 2 beats of every 8th bar.
  - `kick_choke` — final 1/4 bar of break, lone kick on the "and" before the drop.
- The arranger picks transitions per section type and per genre profile. House gets `kick_drop + riser + crash`. DnB gets `snare_roll + reverse_cymbal + crash`. Trap gets `808_pitch_bend + hi_hat_roll_to_drop`.
- The Finisher already has Riser and Crash clip generation — promote that logic into a shared `transitions.py` module that the Song Maker also calls.

**Why it matters:** transitions are how producers say "watch out, here comes the drop". Without them, every section is a flat plateau.

---

## 4. Sub-genre expansion — Phase 1: House family

Once Fixes 1-3 are in place, expand House into a family.

### 4.1 Sub-genres to ship for House

| Sub-genre | BPM | Swing | Signature kick | Signature bass | Chords | Hat/perc |
|---|---|---|---|---|---|---|
| **Deep House** | 118-124 | 52-58 | Soft 4-on-floor, low-passed | Dub/sub root + 5th, sparse | Rhodes 7th/9th pads | Soft shaker, congas |
| **Tech House** | 124-128 | 50-54 | Punchy 4-on-floor | Punchy octave-jumping, syncopated | Stab-only, no pads | Tribal perc, offbeat clave |
| **Garage House** | 122-126 | 56-62 | 4-on-floor with shuffle | Bouncing octaves | Soulful 9th stabs | Skippy 16ths |
| **Afro House** | 118-124 | 52-58 | 4-on-floor + log drum | Melodic, riff-based | Suspended, modal | Layered shakers, talking drum, claves |
| **Bass House / Future House** | 124-128 | 50 | Hard 4-on-floor | Talky/vocal-style synth bass with movement | Sidechained supersaw stabs | Tight closed hats, snare on 2 and 4 |
| **Disco House** | 118-124 | 50-54 | 4-on-floor + open hat on offbeat | Walking octaves, 7ths | Strings + brass-style stabs | Closed/open hat groove, tambourine |
| **Progressive House** | 126-130 | 50 | 4-on-floor, long builds | Sustained root drone | Long arpeggios, suspended → resolved | Steady 16ths, ride |

[Unverified] BPM and swing ranges are typical mainstream conventions, drawn from production tutorials and DJ tools. Verify against Beatport/Camelot-Wheel charts if precision matters.

### 4.2 Sub-genre selection logic (for the assistant to build)

- Each sub-genre is a **named profile that inherits from a House base profile** and overrides specific fields (kick alternatives, bass tag set, swing, chord palette, hat density, allowed instruments).
- Detection priority:
  1. Explicit sub-genre word in prompt ("deep house", "tech house", "afro house").
  2. Vibe-word match → most-likely sub-genre ("soulful" → Deep, "tribal" → Tech, "Rhodes" → Deep, "log drum" → Afro House, "supersaw" → Future House).
  3. BPM match → sub-genres in that range.
  4. Fallback: classic House.
- Sub-genre also picks arrangement template: Deep House gets longer intros (32 bars); Future House gets shorter (8-16 bars) with bigger drops.

### 4.3 Per sub-genre, the assistant must populate (the "intelligence checklist")

For *every* sub-genre, regardless of family, the data must include:

1. **BPM default + range.**
2. **Swing percent.**
3. **Kick variants** (4-8 tagged: `base`, `dropout`, `pickup`, `fill`).
4. **Snare/clap variants** (4-6 tagged: `backbeat`, `ghost`, `roll`, `dropout`).
5. **Hat variants** (4-6 tagged: `closed`, `open`, `roll`, `dropout`, `pedal`).
6. **Bass patterns** (4-6 tagged: `base`, `walk`, `slide`, `drone`, `fill`, `dropout`).
7. **Chord progressions per section** (intro, verse, build, drop, break, drop 2, outro).
8. **Chord voicing rule** (triad / 7th / 9th / sus2 / sus4 / parallel-motion vs smooth inversion).
9. **Lead phrase shapes** (3-6 motifs of 1-4 bars: `call`, `response`, `hook`, `tag`, `silence`).
10. **Arrangement template** (sections + bar lengths + which tracks are active per section).
11. **Transition recipe** (which transitions fire at which section boundary).
12. **Instrument candidates** (stock Ableton browser searches + suggested VST queries per role).
13. **Mixing defaults** (per-track dB levels, pan, send hints).
14. **Vibe words and rule-breakers** (for prompt detection + LLM context).

That's the checklist. If a sub-genre profile doesn't fill all 14, it gets flagged as incomplete and falls back to the family base.

### 4.4 Verification gate for House family

Before moving to DnB, the following must pass:

- Generate 8 tracks per sub-genre (different prompts, different keys). Listen to all 56. Each pair from the same sub-genre should sound clearly different across bars. Each sub-genre should sound clearly different from the others when played back to back.
- Manual listening panel (Jim + 2 producer friends from `LISTENING_NOTES.md`). Pass criterion: every panelist correctly identifies the intended sub-genre at least 70% of the time.

[Speculation] If you can't tell Tech House from Bass House blindfolded, the data still needs work.

---

## 5. Phase 2 — DnB family

Same checklist, different sub-genres:

| Sub-genre | BPM | Notes |
|---|---|---|
| **Liquid** | 170-176 | Smooth chords, Rhodes/strings, vocal samples, melodic bass |
| **Neurofunk** | 172-178 | Reese bass, dark pads, technical drum edits |
| **Jump-Up** | 172-176 | Cartoonish wobble bass, simple snare patterns, hooky drops |
| **Minimal/Tech DnB** | 170-174 | Sparse, dub-influenced, deep sub, very little melody |
| **Half-Time DnB** | 170-176 | Snare on beat 3 only, 808-style sub, trap crossover |
| **Ragga Jungle** | 160-175 | Chopped Amen break, dancehall vocal samples, sub drone |

[Inference] If you've built sub-genre infrastructure for House, DnB should take ~30% of the time House did. Most of the work is data, not architecture.

---

## 6. Phase 3 — Trap + Hip-Hop family

| Sub-genre | BPM | Notes |
|---|---|---|
| **Atlanta Trap** | 130-150 | Half-time snare on 3, long 808 slides, triplet hi-hats |
| **Drill (UK / NY)** | 140-148 | Sliding 808s, syncopated snare, dark minor melodies |
| **Phonk** | 130-150 | Memphis-style cowbell, distorted 808, lo-fi |
| **Plug / Cloud Trap** | 130-145 | Detuned bell leads, dreamy pads, sparse drums |
| **Boom-Bap Hip-Hop** | 85-95 | MPC swing, sample-style chops, simple kick/snare |
| **Lo-Fi Hip-Hop** | 70-90 | Filtered drums, Rhodes/Wurli chords, vinyl crackle |
| **West Coast** | 90-100 | G-funk synth lead, talkbox, P-Funk-flavoured chords |
| **Rage / Hyperpop Trap** | 145-160 | Distorted 808s, aggressive synths, BPM at upper edge |

---

## 7. Cross-cutting improvements (apply everywhere)

These are not phase-gated. The assistant should build them into the shared infrastructure used by all genres.

### 7.1 Wire the CURATED_GENRES rules into the local generator

Right now `rules` and `rule_breakers` are LLM-only context. Convert each rule into a **post-generation validator** the local generator runs:

- "Kick avoids a straight four-on-the-floor pulse" → after generating UK Garage drums, assert kick pattern is not `[0, 1, 2, 3]`. If it is, swap to the 2-step variant.
- "Sub bass below 100 Hz must be monophonic" → after generating any bass, walk the notes and remove any overlap below MIDI 43.

`MUSIC_THEORY_GUIDE.md` already lists these as **constraints** — make them executable.

### 7.2 Section-aware velocity *and* density curves, not just one

Each energy section already adjusts velocity. Add density curves per part:

- Intro: 30% of pattern hits.
- Build: density ramps 50% → 100% over 8 bars; hat subdivision halves every 2 bars (8th → 16th → 32nd).
- Drop: 100%.
- Break: drums fall to 40%, lead silent or sparse, chord pad on.
- Drop 2: 100%, often +12 dB perceived energy through layer additions.
- Outro: density falls back to intro level over 8-16 bars.

### 7.3 Differential humanisation per part

Real drummers play kicks tighter than hi-hats. Add a per-role humanisation multiplier so kick jitter is ~30% of the genre's profile, snare 70%, hat 100%, ghost notes 130%.

### 7.4 Key-fit, length-fit, and tempo-fit the MIDI library

Right now the library returns a pattern as-is. Make the loader:

- Transpose to the requested key.
- Loop or truncate to the requested bar length.
- Reject any clip whose source tempo is more than ±15% from the target (rather than warping all of them which always sounds wrong).
- Pick *different* clips for different sections of the same track (don't reuse the same drum loop for intro, drop, drop 2).

### 7.5 Phrase development for the lead

Instead of `lead_phrases` being a flat list of motifs, define each motif with a role tag: `antecedent`, `consequent`, `hook`, `tag`, `silence`. The lead generator then picks an antecedent for bar 1-2, a consequent (resolves up or down) for bar 3-4, and a contrasting motif for bar 5-8.

This is classical *period* structure ([Verifiable] standard music theory), and it's how 4 / 8 / 16 bar phrases sound less robotic.

### 7.6 Per-section "what plays" matrix

Already partially there in the Finisher. Promote it into the Song Maker so:

- Intro: drums (kick + hat), no bass, pad only.
- Build: + bass, + lead snippets, + riser layer.
- Drop: + full drums, + lead hook, + chord stabs.
- Break: drums minimal, full pad, lead hook.
- Drop 2: same as drop, often +1 layer (vocal chop, FX).
- Outro: reverse of intro.

### 7.7 Modulation between sections (advanced, optional)

After Phase 1, experiment with a +2 semitone shift on the final drop. This is the "modulation chorus" trick used in pop/EDM. Cheap to implement (one transpose action on the relevant tracks), measurable lift in perceived energy.

---

## 8. Suggested timeline & checkpoints

Per Jim's accountability rules: deadlines upfront, checkpoints at roughly 90 minutes of work.

| Phase | Scope | Suggested elapsed effort | Checkpoint |
|---|---|---|---|
| 0a | Multi-bar variation engine (Fix 1) | ~90 min spec + ~1 day build | Generate same prompt twice and confirm 8 bars of drums and bass have at least 4 distinct variations |
| 0b | Section-aware reharmonisation (Fix 2) | ~90 min spec + ~1 day build | Listen to intro / drop / break of one House sketch and confirm chord palette differs |
| 0c | Transitions library (Fix 3) | ~90 min spec + ~1 day build | Confirm every section boundary has at least one transition event |
| 1 | House family — 4 sub-genres (Deep, Tech, Garage, Afro) | ~1 week per sub-genre, batched | Listening panel test in §4.4 passes |
| 1.5 | Wire CURATED rules into local generator | ~half day | Run unit tests asserting each rule fires |
| 2 | DnB family — 4 sub-genres | ~3-4 days per sub-genre (template exists) | Panel test |
| 3 | Trap + Hip-Hop family — 4-6 sub-genres | ~2-3 days per sub-genre | Panel test |

[Speculation] Estimates assume one full-time builder using AI assistance and a working test loop. Pad if you're part-time.

---

## 9. What NOT to do (anti-patterns to avoid)

- **Don't add more genres without finishing the variation engine.** That's the trap you're worried about.
- **Don't over-rely on the OpenAI planner for musical intelligence.** Most users won't have an API key. The local generator must be musically credible on its own.
- **Don't randomise for the sake of variety.** Use musical structure (period, antecedent/consequent, energy arc) so variation has direction. Pure randomness sounds disordered, not human.
- **Don't try to model every micro-genre.** Drill is a real thing; UK Drill vs NY Drill vs Bronx Drill is detail you can ship later. Keep 4-6 sub-genres per family, well executed.
- **Don't break the deterministic seed.** Producers will want "same prompt = same result" for reproducibility. Variation should be deterministic from the prompt + bar index.

---

## 10. Open questions to answer before coding starts

1. **Storage shape for sub-genres.** New file per sub-genre, or extend the existing `GenreDNA` dataclass with an optional `parent` field? [Inference] The parent-pointer approach lets sub-genres inherit and override without duplicating data.
2. **Where does the mutation schedule live?** Per-genre, per-section, or one global "house style" of schedule (AABB+fill etc.) that gets weighted differently per genre?
3. **MIDI library — re-scan now?** If the user adds new MIDI packs to populate the new sub-genres, the cache needs an explicit re-scan UI button.
4. **Listening panel commitment.** Who, how often, what tracks? Without a panel the qualitative gain will be hard to validate. Your `LISTENING_NOTES.md` template is already set up for this.
5. **VST mapping per sub-genre.** Should each sub-genre have a recommended VST query list, or stay generic? Recommended: per sub-genre, with a sensible stock-Ableton fallback.

Answer these before starting Phase 0, otherwise the assistant will make assumptions that you'll need to undo.

---

## 11. Honest caveats

- [Unverified] I have not listened to any output from Vibelton. This critique is based entirely on reading the code, the manual, and your music theory guide. If something here contradicts what you're actually hearing, trust your ears.
- [Inference] The "robotic" feeling almost always comes from repetition and lack of transition, not from chord choice. That's why §3 is ordered the way it is. If you implement §3 and it still sounds robotic, the next suspect is humanisation timing per part (§7.3).
- [Unverified] My BPM / swing ranges in §4.1, §5, §6 are typical conventions. They are not guaranteed to match Beatport's current charts or any specific reference track.
- [Speculation] My timeline estimates in §8 should be treated as order-of-magnitude. If you're new to one of these sub-genres, double the estimate for that sub-genre.
- I haven't fabricated any specific paper titles, artist quotes, or URLs. Where I named artists by sub-genre (e.g. in the Music Theory Guide reference column), those names already exist in your repo's `MUSIC_THEORY_GUIDE.md`. I did not introduce any new artist attributions.

---

## 12. The brief for the AI coding assistant — one paragraph

> Read `MUSICAL_INTELLIGENCE_CRITIQUE.md`. Implement Phase 0 in order: first the multi-bar variation engine (Fix 1), then section-aware reharmonisation (Fix 2), then the transitions library (Fix 3). After each fix, run the existing test suite, then generate sample output for House and one other genre and present me the diffs in note lists for review. Do NOT start Phase 1 (sub-genres) until I have signed off on Phase 0 sounding noticeably less robotic. When you build Phase 1, build Deep House first, end-to-end, including the verification gate in §4.4 — that becomes the template for every other sub-genre.

End.
