# Vibelton Improvements Plan

Author: drafted for Jim, 2026-04-30
Status: planning document, no code changes attached
Scope: how to push Vibelton out of "AI-slop MIDI helper" territory and into a tool a working producer would pay for

A note on labels used below:
- [Inference] = reasoned from public material, not directly tested
- [Speculation] = a guess worth checking
- [Unverified] = no source confirmed
- Untagged claims are about your own files in this repo, which I read directly

---

## 1. What Vibelton currently is

Read directly from the repo (`VIBELTON_PRD.md`, `README.md`, `genre_dna.py`, `midi_library.py`, `planner.py`, `actions.py`, `server.py`, the remote scripts).

Working today:
- Natural-language chat to Ableton Live 12 over a file-queue bridge (`commands.jsonl`, `events.jsonl`, `state.json`).
- A deterministic local planner plus optional GPT planner (`planner.py`).
- A `GenreDNA` profile system covering House, UK Garage, DnB, Jungle, Techno, Trance, Trap, Hip-Hop, Reggaeton (and more in the file). Each genre defines kick/snare/hat patterns, bass patterns, chord style, lead phrases, swing, and BPM range.
- A real MIDI corpus loader (`midi_library.py`) that scans local folders (Cymatics, free-midi packs, GM Mapped) and caches drum patterns by detected style.
- Helpers already imported: `humanize_groove`, `add_ghost_notes`, `mutate_clones`, `finisher_mutation`. So humanisation is partly wired but is the obvious place to push.
- A SnapHost PRD for VST3/AU snapshot/morph/randomize control. Strong second-product idea, untouched here except where it intersects.

What this means for the "make it less generic" question: the bones are good. The weakness is in *musical intelligence per generation* and in the *finishing* stage, where DeSantis's book says producers usually fall over.

---

## 2. Why it currently risks sounding generic

Reading the genre DNA file end to end, here are the honest ceilings:

1. **Limited pattern pool per genre.** Most genres ship 2-3 bass patterns and 1-2 lead phrases. After a couple of generations, repeats are obvious.
2. **Velocity is mostly hand-set, not modelled.** Drummers don't accent the same way every bar. The ghost-notes helper is a start; no pattern of weak/strong cycle, no flam, no rim variation by bar.
3. **No microtiming model beyond a single `swing` float.** Real genres have characteristic *push and pull* (DnB hats lay back, UKG kicks land late, dembow has a specific tresillo lean). One swing number per genre flattens all of this.
4. **Chord progressions are 4-chord defaults per mode** (`I V vi IV` major, `i VI III VII` minor). No modal interchange, no secondary dominants, no voice-leading, no inversions chosen for smoothness.
5. **No dramatic arc.** Energy levels (`intro`, `build`, `main`, `break`) exist as labels but I don't see filtering automation, frequency masking decisions, or sidechain depth that would actually *do* the energy curve.
6. **No mix decisions.** Volume in dB is exposed; nothing models headroom, gain staging, sub clash, or mid-bandwidth crowding. A producer hearing the output through monitors will spot this in 30 seconds.
7. **MIDI library coverage skews toward drums** (`extract_drum_notes` is the only normaliser). Melodic packs in the same folder are skipped. That's a missed asset.
8. **No reference-track concept.** Producers work to a reference. There's no "match the feel of *track X*" loop.

None of those are showstoppers. They are exactly the gap between "tech demo" and "thing that earns its slot in a paid workflow."

---

## 3. The musicality plan

### 3.1 Humanisation that's actually genre-aware

[Inference] Real groove templates (Akai MPC60 Swing 54-66, Linn LM-1, J Dilla off-grid feel, amen-break micro-drift) are well-documented and ship with Ableton's Groove Pool. Importing the exact .agr files and applying them per genre is more convincing than a single swing scalar. (See Sample Focus and Splice articles in §7.)

Concrete moves:
- Replace the single `swing` float in `GenreDNA` with a `groove_profile` object: `{position_jitter_ms, velocity_jitter, length_jitter, weak_beat_curve, push_pull_per_subdivision}`.
- Ship a small bundled set of groove templates derived from the public-domain Magenta Groove MIDI Dataset (Google released this under CC-BY 4.0; verify license before shipping). [Unverified license terms in current year]
- Per-genre humanise presets: hip-hop boom-bap = MPC swing 58-62 + late snare 8-15 ms; DnB = tight kicks, hats slightly behind on offbeats; UKG = the syncopation already in your patterns plus 7-12 ms shuffle on hats; trap = on-grid kicks, triplet hat rolls with velocity ramps.
- Velocity *curves* not jitter alone: model the strong-weak-mid-weak cycle for 16th hats (e.g. 90/72/80/68 repeating, with random ±4).

### 3.2 Better harmony engine

The current chord engine is degree-based with one preset progression per mode. That's where listeners say "yep, that's AI."

Concrete moves:
- Replace the static progression list with a small Markov / weighted-graph progression model per *style* (lo-fi leans on ii-V-i and iv-V/V-i; UKG loves ii-V-I with extensions and tritone subs; deep house repeats Imaj7-iiim7). Authors who codify this well: Dennis DeSantis (already in your repo as `MakingMusic_DennisDeSantis.md`), Hooktheory's *Theory Tab* dataset, Paul Davids and Adam Neely on YouTube.
- Use `music21` (BSD, mature) for chord-tone calculation, voice-leading minimisation, and Roman-numeral input/output. It does parallel-fifth checks and scale-aware spelling. See §6.
- Add inversion selection. The simplest helper: keep voice movement under 5 semitones average between adjacent chords. [Inference] this alone will lift perceived musicality more than any extra extension.
- Borrow chords by mode: minor iv in major keys, bVII, Picardy III. Expose as a `colour: "neutral" | "moody" | "cinematic" | "jazzy"` knob that re-weights the Markov model.
- Tension and release: track a numeric tension score per bar based on chord function and dissonance, and bias the planner so the second half of a 16-bar section rises before resolving. This is straight DeSantis (Strategy 39, Dramatic Arc).

### 3.3 Melody that has a shape

Current lead phrases are 4-8 note hand-written templates per genre.

Concrete moves:
- Keep the templates as *seeds*, but add a phrase-shaping pass:
  - Choose a contour (arch, descending, terraced, call-and-response) at the bar level.
  - Constrain to chord-tones on strong beats, scale-tones on weak beats, chromatic passing-tones only between specific intervals.
  - Vary by repetition rule: bar 1 = motif, bar 2 = exact repeat, bar 3 = transposed up a third, bar 4 = answer (DeSantis Strategy 18, "Variations").
- Add *rest* generation. AI-slop melodies fill every beat. Forcing a target note-density (notes per bar) per energy level is a big tell-fix.
- Phrase-end behaviour: melodies should land on chord-tone of the resolving chord. Easy rule, big impact.

### 3.4 Drums that aren't the same loop twice

You already have `mutate_clones` and `finisher_mutation` imported. Make them load-bearing.

Concrete moves:
- Every 4 bars: probability of variation. e.g. 8-bar section = identical bar 1, 90% bar 2, 70% bar 3, fill bar 4. Standard DnB / house structural rule.
- A dedicated `fill_generator(style, complexity)` that operates only on bar 4/8/16 boundaries.
- Hat density envelope: kick/snare stay constant, hats double up on the build, drop out at the drop, return on bar 5.
- Layer rules: house = clap doubles snare on beats 2 & 4 with -3 dB and 8 ms late; trap = open hat on the *and* of 4 in every other bar; hip-hop = ride bell only on the "a" of beat 4.

### 3.5 Arrangement, not just generation

This is the biggest single value-add and is exactly what the existing PRD calls out as "future" but only at the label level.

Concrete moves:
- Define an arrangement template DSL in JSON. Each section has: `bars`, `energy`, `active_tracks`, `fx_send_targets`, `automation_curves`. Genres ship default templates ("UKG 8-min DJ tool", "Lo-fi 2-min beat", "Trance breakdown-build-drop", "Pop ABABCB").
- The Arranger pass takes the Session-view sketch and copies clips with section-aware mutations, automation envelopes (filter cutoff, send to reverb, sidechain depth), and rests.
- Inspiration: Mr. Bill's *Sub Harmonic Alignment* and *Arrangement* breakdowns; Multiplier's "How limiters work" and chord-writing series; Cloudchord on lofi structure; Stranjah on DnB intros and second drops. Cited links in §7.

### 3.6 Sound, not just notes

Vibelton today is a MIDI generator. The complaint "AI slop" usually comes from the *sound*, not the notes. Two paths:

- **Stock-device chains per role.** Build a small library of Ableton stock-device chains as `.adv` presets, plus the macro mappings, that get loaded with each generated track. ("Lo-fi keys" = Operator + Cabinet + Auto Filter + Vinyl Distortion at known settings.) Keep them small and tasteful. Ship maybe 30. ELPHNT and AfroDJMac both publish free packs that map to this exact pattern.
- **SnapHost integration.** Your second PRD already plans this. Once SnapHost is hosting one VST3, send "morph 30% toward Snapshot 2" or "randomise lightly, lock cutoff" from the Vibelton chat.

### 3.7 Mix sanity

Concrete moves (all small, all visible in <30 minutes of listening):
- Default volumes per role: kick -8 dB, snare -10, sub -10, mid bass -14, pads -16, lead -12, FX -18. Treat as a starting fader staging the planner emits with every sketch.
- Auto-routing of every melodic element through a *Sub-Bass* return only filtered above 100 Hz to keep low end clean.
- One *Glue* compressor on Master, conservative settings (2:1, 6 ms attack, 100 ms release, 1-2 dB GR).
- Sidechain ducking from kick → bass and pads via a default *KickGhost* return track, depth scaled by genre (deep house = 6 dB, techno = 4 dB, trap = none).

---

## 4. Competitive landscape (what to be better than)

[Inference, mostly from public marketing pages — verify product behaviour before claiming parity]

| Product | Lives where | What it does | Where Vibelton can win |
|---|---|---|---|
| **VIXSOUND** | Native chat panel inside Ableton 12 | Generates editable MIDI for chords, drums, bass, melody. Stem split, audio→MIDI, BPM/key detection. Subscription $9-79/mo. | They are closest direct competitor. [Inference] Vibelton wins on arrangement automation and openness (no sub fee, your MIDI corpus, local LLM optional). Lose the file-queue jank — UI parity matters. |
| **Scaler 3** | VST/AU plugin | Chord progression building, key detection from audio, MIDI capture from input, song builder. Paid. | Scaler is harmony-only. Vibelton's whole-arrangement view is a clear gap they don't fill. |
| **Captain Plugins (Mixed In Key)** | VST suite | Captain Chords, Melody, Deep, Beat, Play. Strong UI for songwriters. | Same gap as Scaler — no real arrangement. Captain is plugin-bound, requires drag-drop. |
| **AudioCipher v4** | Standalone + plugin | Word-to-MIDI, melody and chord generation, voice leading. | Cute hook, narrow feature. Vibelton does more once arrangement ships. |
| **Magenta Studio** | M4L devices | Continue, Drumify, Generate, Groove, Interpolate. Free. | [Inference] appears low-maintenance / abandoned. Borrow design ideas, especially the "Groove" device's velocity humanisation model. Cite their dataset. |
| **Orb Producer Suite** | VST | Chord, bassline, arpeggio, melody plugins. Paid. | Orb is style-thin. Vibelton's genre DNA already goes deeper. |
| **Suno Studio** | Web-first DAW with AI generation, stems, MIDI export | Whole songs from prompts, 12-stem split, MIDI extraction. | Different category — Suno makes finished audio, you stay in a producer's editing workflow. The right framing is "Suno is a draft, Vibelton is your studio assistant." |
| **MIDI Agent** | Plugin | AI MIDI generation, marketed via comparison pages. | [Speculation] thin compared to genre DNA. Worth installing and benchmarking before any marketing claim. |
| **Bouncy Notes** | Plugin / app | MIDI generation in DAW. | [Unverified specifics]. Same — install and A/B before claiming. |

The strategic gap that none of the above own: **opinionated, end-to-end, genre-faithful arrangements with humanised feel and mix sanity, controllable from chat, in your DAW, with your own MIDI library.**

---

## 5. Reference list (what to read and watch before iterating)

### Books
- **Dennis DeSantis, *Making Music: 74 Creative Strategies for Electronic Music Producers*.** Already in your repo as `MakingMusic_DennisDeSantis.md`. Sections to literally encode as planner heuristics: Variations, Maximal Density, Dramatic Arc, Tuning Everything, A Series of Bricks, Endings. (Free PDF on Ableton's CDN, citation in §7.)
- **Mike Senior, *Mixing Secrets for the Small Studio*.** For the mix-sanity defaults in §3.7. The Mix Rescue archive on Sound on Sound is the same author and free.
- **Aaron Karpinski-style pop songwriting books / Murphy *Murphy's Laws of Songwriting*.** [Inference] worth scanning for hook-shape rules.

### YouTube channels (cited in §7)
- **Ableton (official channel)** for Loop talks, especially anything by Tom Cosm and Cuckoo on workflow.
- **Mr. Bill** — sound design, sub-harmonic alignment, glitch, arrangement teardowns. Goldmine for unusual tricks that translate to deterministic rules.
- **Multiplier (Adam)** — limiter mechanics, chord writing, unusual approaches. Excellent for harmony rules.
- **ELPHNT** — clean Max for Live tutorials, modulation, lush spaces. Strong on aesthetic taste rules.
- **Cloudchord** — lofi, soul guitar, finishing.
- **Stranjah** — DnB-specific patterns and arrangement.
- **AfroDJMac (Brian Funk)** — practical Ableton tips, free packs.
- **Andrew Huang** — sound design tricks, sample flips.
- **Adam Neely** — music theory deep dives that stay practical.
- **You Suck at Producing (David Earl)** — old but still-relevant arrangement rules.
- **In The Mix / Busy Works Beats / Internet Money** — for trap and pop-trap structural conventions.
- **Loopop** — synth-by-synth sound-design vocabulary, useful for SnapHost preset descriptions.

### Datasets and references
- **Magenta Groove MIDI Dataset.** Real drummer microtiming on a metronome. Use for groove templates. Verify CC-BY 4.0 terms before bundling.
- **Lakh MIDI Dataset / MAESTRO** for melodic phrase shapes.
- **Hooktheory TheoryTab** for chord progression statistics by genre. Their API is paid but publicly documented.
- **MPC swing values 50-66%** are public. Akai's own manuals describe them.

---

## 6. Tools and libraries to evaluate

[Inference] none of these are in the repo today. All are popular enough that adoption shouldn't be a research project.

| Library | Why | License (verify) | Risk |
|---|---|---|---|
| `music21` | Voice leading, Roman numerals, scale logic, parallel-fifth checks. Maintained by Cuthbert at MIT. | BSD | Heavyweight. Optional dependency, isolate behind `harmony.py`. |
| `mido` or `pretty_midi` | Better MIDI parsing than the hand-rolled `parse_midi_notes`. Catches edge cases. | MIT | Tiny. |
| `partitura` | Score representation with expressive timing support — useful for generating performances, not just notes. | Apache 2.0 [Unverified] | Niche, but worth a look for the humanisation pass. |
| `numpy` (already common) | Vectorise the velocity-curve and microtiming generation. | BSD | None. |
| `scikit-learn` | A small Markov / weighted-graph chord model. Or just write it by hand — sklearn is overkill for n-gram. | BSD | Optional. |
| `librosa` | If you ever want to detect key/BPM from a reference audio drag-in. | ISC | Adds ffmpeg dependency. |
| `JUCE` | Already named in `SNAPPY_HOST_PRD.md` for SnapHost. Stick to it. | GPL/commercial | Licence cost when distributing closed-source. |
| `magenta` (TF) | Their Groove model and MusicVAE are open. [Inference] heavy for a Live remote-script context. Probably better as a pre-baked dataset import rather than a runtime dep. | Apache 2.0 | TF runtime is huge. |

What I would *not* add: nothing from the LangChain ecosystem, nothing from a model-zoo with unclear licensing, no proprietary "AI music API" that locks the project to a vendor. Vibelton's pitch is producer-owned MIDI; keep it that way.

---

## 7. Sources

Books and PDFs
- [Making Music. 74 Creative Strategies For Electronic Music Producers (Ableton-hosted PDF)](https://cdn-resources.ableton.com/resources/uploads/makingmusic/MakingMusic_DennisDeSantis.pdf)
- [Notes on DeSantis's "Making Music" (Brettworks)](https://brettworks.com/2016/01/20/notes-on-dennis-desantiss-making-music-74-creative-strategies-for-electronic-music-producers/)
- [Making Music — about the book (Ableton)](https://makingmusic.ableton.com/about)

Humanisation and groove
- [How to Humanize MIDI Like a True Professional (Unison)](https://unison.audio/how-to-humanize-midi/)
- [Swing, Shuffle, and Humanization (SampleFocus)](https://blog.samplefocus.com/blog/swing-shuffle-and-humanization-how-to-program-grooves/)
- [The Ultimate Guide to Humanizing MIDI Drums (MixElite)](https://mixelite.com/blog/humanizing-midi-drums/)
- [Humanizing MIDI Drums in Ableton (Production Music Live)](https://www.productionmusiclive.com/blogs/news/humanizing-midi-drums)
- [How to humanize your drums (Splice)](https://splice.com/blog/humanize-your-drums/)
- [MIDI Timing Truth (StrongMocha)](https://strongmocha.com/creator-sound-design/midi-timing/)

YouTube channel lists
- [Ableton Tutorials: Top 21 YouTube Channels (EDMProd)](https://www.edmprod.com/ableton-tutorials/)
- [38 Must-Follow YouTube Channels (I Am Ghost Producer)](https://iamghostproducer.com/blog/10-must-follow-youtube-channels-for-music-production/)
- [Best YouTube Channels for Music Production (Internet Tattoo)](https://www.internettattoo.com/blog/best-music-production-youtubers-beatmakers)
- [Music Production Tutorials on YouTube (Gravitas Create)](https://gravitascreate.com/best-youtube-channels-electronic-music-production-tutorials/)

Sound design references
- [How to Learn Sound Design — 13 Resources (ProducerAdvice)](https://produceradvice.com/how-to-learn-sound-design-13-resources-that-you-should-use/)
- [5 videos to learn sound design for minimal house (Distilled Noise)](https://distillednoise.com/5-videos-to-learn-sound-design-for-minimal-house/)
- [Tips from Mr. Bill's first 5 Ableton tutorials (Medium)](https://medium.com/@djsystemizer/tips-learned-from-first-5-tutorials-from-mr-bill-s-youtube-ableton-series-43610a16572a)

Competitor and AI landscape
- [Best AI VST Plugins 2026 (VIXSOUND)](https://vixsound.com/best/best-ai-vst-plugins)
- [VIXSOUND — AI Assistant for Ableton Live](https://vixsound.com/compare)
- [VIXSOUND vs Suno vs Udio (VIXSOUND blog)](https://vixsound.com/blog/vixsound-vs-suno-vs-udio)
- [Best AI Tools for Ableton 2026 (LIA Plugin)](https://liaplugin.com/blog/best-ai-tools-ableton-2026/)
- [6 Best AI MIDI Generator DAW Plugins (AudioCipher blog)](https://www.audiocipher.com/post/ai-midi-generators)
- [AI MIDI VST/AU Plugins Compared (MIDI Agent)](https://www.midiagent.com/compare)
- [Top 70+ AI Plugins for Music Producers (Production Music Live)](https://www.productionmusiclive.com/blogs/news/top-14-ai-plugins-and-tools-for-music-producers-in-2023-for-mixing-mastering-composition-sequencing-more)
- [Suno Studio announcement (Suno)](https://suno.com/blog/suno-studio)

Algorithmic composition libraries
- [music21 (project home, Cuthbert)](https://www.music21.org/music21docs/)
- [Algorithmic composition with music21 (A Touch of Music)](http://a-touch-of-music.blogspot.com/2013/08/algorithmic-composition-generating.html)
- [Tymoczko, MTO Review of music21](https://mtosmt.org/issues/mto.13.19.3/mto.13.19.3.tymoczko.html)
- [canon-generator (GitHub, music21)](https://github.com/shimpe/canon-generator)
- [midigen-lib (PyPI)](https://pypi.org/project/midigen-lib/)

---

## 8. Prioritised roadmap

I have grouped the work into four iterations. Each iteration ends with a listening test against a reference track and a written A/B note. Per your accountability needs, I have set hard deadlines and a 90-minute checkpoint inside each iteration.

[Inference] effort estimates assume one engineer-musician working evenings + weekends. Halve them if you go full-time.

### Iteration A — "Stop sounding like a metronome" (target: 1 week, by 2026-05-07)
Goal: every generated clip survives a blind listen against a reference loop in the same genre.

- A1. Replace `swing: float` with `groove_profile` dataclass on `GenreDNA`. **(half day)**
- A2. Bundle 6 groove templates derived from the Magenta Groove dataset (boom-bap, MPC swing 58/62, DnB tight, UKG shuffle, dembow, trap-triplet). License-check before bundling. **(1 day)**
- A3. Velocity *curve* generator per drum role, replacing flat 78-110. **(half day)**
- A4. Probability-based bar-to-bar drum mutation (90/70/fill rule). **(half day)**
- A5. Listening A/B against 3 reference tracks per genre, write notes. **(half day)**

90-min checkpoint at end of day 2: drums alone, side-by-side blind test, note which genres still fail.

Success exit: ≥3 of the bundled genres pass blind listening on at least one reviewer's ear (you).

### Iteration B — "Harmony with a brain" (target: 2 weeks after A, by 2026-05-21)
Goal: chord progressions feel chosen, not stamped.

- B1. Add `music21` as optional dep, isolate in `harmony.py`. **(half day)**
- B2. Genre-weighted progression model (Markov over Roman numerals, learnt by hand from Hooktheory style tables — not scraped). **(2-3 days)**
- B3. Voice-leading minimisation pass on chord pitches. **(1 day)**
- B4. Borrowed-chord "colour" knob exposed in chat. **(half day)**
- B5. Phrase-shape pass for melody (contour + rest density per energy). **(2 days)**
- B6. A/B listening against 3 reference tracks. **(half day)**

90-min checkpoint at the end of B3: write a chord progression by chat, paste into Captain Chords or Scaler for comparison. Note feel differences.

Success exit: a producer friend listens to 5 generated 8-bar loops and can't tell which two are AI without being told.

### Iteration C — "Real arrangement, not just labels" (target: 3 weeks after B, by 2026-06-11)
Goal: the Arrangement view on first listen reads as a song, not a sketch.

- C1. Arrangement template DSL, JSON. Three default templates per genre family. **(2 days)**
- C2. Section-aware mutation in the Arranger pass (rests, fills, hat-density envelopes). **(3 days)**
- C3. Automation generation: filter cutoff opens through builds, sidechain depth on the drop, reverb send rises into breakdowns. **(3 days)**
- C4. Default mix staging (§3.7) emitted with every sketch. **(1 day)**
- C5. Listening test over a full 3-min arrangement. Compare against a curated reference per template. **(1 day)**

90-min checkpoint at end of week 1 of C: render a single 3-min arrangement, compare to a reference DJ tool, note three biggest deltas.

Success exit: a 3-min arrangement is mixable in <30 minutes of human work to release-ready.

### Iteration D — "Sound, not just notes" (target: 4 weeks after C, by 2026-07-09)
Goal: the audio coming out of the speakers is recognisable as the genre at first listen, not just at first transcription.

- D1. Bundle 30 stock-device chains (`.adv`) covering one to three sounds per role per genre. **(3 days)**
- D2. Wire SnapHost client (the second-PRD path) so chat can morph and randomise hosted plugins. **(1-2 weeks)**
- D3. Reference-track ingestion: drag an audio file into the chat, BPM/key detection via `librosa`, lock generation to it. **(3 days)**
- D4. Final A/B against the original VIXSOUND/Scaler/Captain comparison set; write a 1-page memo on what's still missing. **(1 day)**

90-min checkpoint at end of D1: load 5 randomly-chosen chains, listen, throw out any that sound off-the-shelf preset-y.

Success exit: a producer who has never seen Vibelton can listen and identify the genre with the speakers behind a curtain.

---

## 9. Smaller wins worth doing alongside

These don't need their own iteration but each one improves the "vibe" of the tool.

- Rename queue files to something less clinical — `~/Library/Application Support/Vibelton/...` on macOS rather than dotfile in `$HOME`. Just professional polish.
- Web UI tone pass: drop the "Snowball from zero" line in `README.md` for a clearer one-liner. [Speculation] something like "A producer's chat seat in Ableton Live."
- Logging: `events.jsonl` is rich. Add a `vibelton history` command that prints the last 10 prompts + outcomes. Useful for the "iterate relentlessly" muscle in your preferences.
- Ship a curated example library: 10 prompts + the .als files they produce. This is the single best onboarding move you can make and costs a weekend.
- Add a *don't generate* mode: chat that *suggests* what to do next based on the current state (`state.json` already has it). DeSantis Strategy 1 ("Set the tempo and just play"). This is non-trivial differentiation versus VIXSOUND.

---

## 10. What this is *not*

To stay honest:

- This plan does not change any code. You explicitly asked for that.
- I cannot verify product features for VIXSOUND, MIDI Agent, Bouncy Notes from the marketing pages alone. Install + A/B before claiming parity in any public copy. Correction-readiness: if anything in §4 reads as confident product knowledge, it is [Inference] from public marketing.
- I have not audited Magenta Groove dataset licensing for 2026. Do that before bundling.
- I have not benchmarked the proposed `music21` import against the file-queue latency requirements. [Speculation] it should be fine because the planner runs server-side, not in the Live process.
- The roadmap deadlines are aggressive. If you slip past Iteration A by a week, that's a signal to halve scope, not push harder.

---

## 11. One paragraph summary

Vibelton has the right architecture and the right second-product (SnapHost) on its roadmap. Where it currently leaks "AI slop" is in the *feel* of the MIDI it ships: one-swing-fits-all, thin chord vocabulary, no dynamic arc, no mix sanity, no real arrangement automation. The fix is not more AI — it is encoding the kind of taste that producers like Mr. Bill, ELPHNT, and Stranjah already teach for free, plus the structural strategies in DeSantis's *Making Music*, into deterministic generators backed by `music21` and a real groove-template library. Do iteration A, get a blind listen test passing, and the rest of the path is fundable.
