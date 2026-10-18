# 16 House Subgenres: MIDI Role To Ableton Sound Map

This document maps 16 house subgenres to the sound choices Vibelton should use when assigning Ableton-native instruments and presets to generated MIDI parts. It is written as an implementation reference: the listed Ableton entries should be treated as browser search candidates, then filtered by the user's installed library scan.

## Source Notes

- Ableton's Live 12 manual describes the core stock instruments this map leans on: Analog for warm modeled subtractive synth tones, Drift for fast subtractive bass/lead design, Operator for FM/sub/organ-like tones, Wavetable for evolving modulation, Electric for electric piano keys, Tension/Collision for physical-model plucks and mallets, and Drum Rack for kits.
- Ableton's Drum Machines pack documentation confirms classic 606/707/808/909-style Drum Racks, effects macros, and MIDI-pattern-oriented drum-machine presets.
- Ableton's Electronik Drums documentation confirms house/electronica-oriented analog drum rack material including CR78, DX, RX, TR-505, 606, 707, 808, and 909 sources.
- Ableton's Synth Essentials documentation confirms presets for Wavetable, Operator, Analog, Tension, Collision, and Instrument Racks using Live's filters/effects.
- Local scan source: `/Users/standard/Music/Ableton/Factory Packs/**/*.adg|*.adv`. Useful installed names found include `Kit-909 Classic`, `Kit-909 Tresor`, `Kit-808 Classic`, `Kit-707 Classic`, `Kit-606 Classic`, `Kit-606 Cathode`, `Kit-Carbonized`, `Kit-Minimum`, `Kit-Ethno`, `Kit-Wood`, `Kit-Largeness`, `Swang Bap Kit`, `Otari Bounce Kit`, `Ninja Drums`, `Static Kit (Glitch)`, `Gooey Sub Rubber`, `Warm Bass`, `Curt Bass`, `Percu Bass`, `Whose Organ`, `TX Piano`, `Slow Motion Pad`, `Slow 5th Pad`, `sawbass`, `synth. bass`, `elec. piano`, `elec. organ`, `synth. strings`, `Grand Piano Classic LA Stack`, `Grand Piano Pad`, `Guitar-Chopper Chords`, and `Guitar-French Guitar Pad`.

## Global Role Rules

- `bass`: Prefer monophonic MIDI. Choose Analog/Drift/Operator for synthesized bass; Electric Bass or Guitar and Bass racks for disco/funk variants; Operator/Analog-style organ bass for garage.
- `chords`: Prefer voicing density by genre. Deep/Chicago/Garage use seventh/ninth chords and Electric/piano/organ sounds. Tech/Bass/G-House use short stabs or single-note chord triggers.
- `riff`: Short repeated motif. Acid uses a resonant 303-like line; Tech/Minimal use one- or two-note synthetic motifs; Disco/French use sample-like guitar/string/piano chops.
- `hook`: Lead melody, vocal chop, or short signature sound. Progressive/Electro/Bass House need stronger leads; Ambient/Minimal need understated motifs.
- `ambience`: Pads, noise beds, field-like texture, long reverbs, filtered background movement, or transitional FX.
- `drums`: Use the installed drum-kit scanner first. Only fall back to named Core/Drum Machines kits when no local kit match exists. Do not use bare `Drum Rack` as a sound choice.

## 1. Acid House

Core identity: Squidgy acid basslines, 909 drum-machine sounds, psychedelic synths, resonant automation, and repetitive machine funk.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Analog Bass`, `Operator Bass`, `Drift Bass`, `sawbass`, `Gooey Sub Rubber`, `Warm Bass` | 1/16 acid sequence, slides, octave jumps, minor-mode tension | Auto Filter or filter frequency automation, high resonance, Saturator, Delay, subtle Phaser-Flanger |
| Drums | `Kit-909 Classic`, `Kit-909 Tresor`, `Kit-909 Myrtle`, `Kit-909 Alteration`, `Kit-606 Cathode` | Four-on-floor kick, 909 clap, open hats, short ride lifts | Drum Buss, Saturator, short room reverb, overdrive on hats/percussion |
| Chords | `Analog Chords`, `Operator Chords`, `Whose Organ`, `TX Piano` | Sparse minor stabs, not too jazzy | Auto Filter, Echo, sidechain compression |
| Riff | `Acid Riff`, `Operator Pluck`, `Drift Pluck`, `Percu Tone` | Repeating 1-2 bar acid motif | Filter envelope, LFO to filter, Beat Repeat fills |
| Hook | `Analog Lead`, `Retro Steam Lead`, `Metal-o Feedbackisimo Lead` | Small psychedelic lead phrase | Ping-pong delay, reverb throws |
| Ambience | `Slow Motion Pad`, `Slow 5th Pad`, `MembUFORelease` | Background drone or breakdown haze | Grain Delay/Hybrid Reverb, filter sweeps |

## 2. Ambient House

Core identity: Calming pads, atmospheric synths, soft house pulse, gentle percussion, and low-pressure harmonic movement.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Warm Bass`, `Deep Sub`, `Operator Bass`, `Curt Bass` | Long held roots or soft offbeat pulses | Low-pass filtering, gentle sidechain, minimal saturation |
| Drums | `Kit-Wood`, `Kit-White`, `Acoustified Kit`, `Grounded Kit`, `Kindified Kit` | Soft kick, brushed hats, sparse percussion | Hybrid Reverb, low velocity, reduced transient with Drum Buss |
| Chords | `Grand Piano Pad`, `Grand Piano Lost Ship`, `elec. piano`, `TX Piano` | Slow 7th/9th chords and suspended voicings | Reverb, Chorus-Ensemble, Auto Filter |
| Riff | `Tension Pluck`, `Collision`, `Bell`, `FM Prayer Bell`, `TwoPluckedStrings` | Occasional bell/pluck motifs | Delay, high-pass reverb send |
| Hook | `Dreamy`, `SlowMotion`, `AirMembrane`, `AirPlate` | Very sparse melodic phrase | Long reverb, shimmer-like high feedback |
| Ambience | `Slow Motion Pad`, `Slow 5th Pad`, `sludgepad`, `bocpad`, `czpad`, `bellpad`, `MembUFORelease` | Main emotional layer | Grain Delay, Hybrid Reverb, LFO filter movement |

## 3. Bass House

Core identity: Heavy distorted basslines, trap/bass-music drum influence, aggressive growls, short drops, and tight mix density.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Wavetable Bass`, `Operator Bass`, `Drift Bass`, `Gooey Sub Rubber`, `MatrixBass`, `FMBass` | Syncopated bass drops, call-and-response growls | Saturator, Roar/Overdrive, Auto Filter, sidechain compression, Corpus for metallic growl |
| Drums | `Kit-808 Classic`, `Kit-808 Magnetikz`, `Kit-808 Babblebox`, `Kit-909 Mastodon`, `Electrified Kit` | Four-on-floor with trap hats/fills, heavy claps | Drum Buss, Saturator, transient shaping, clipped parallel bus |
| Chords | `Wavetable Chords`, `Meld Chords`, `BigChord` | Short tension stabs before drops | Sidechain, Auto Filter, reverb cutoff automation |
| Riff | `Glitch Machine 2`, `TheFMMachine`, `MegaSquare`, `Wavetable Pluck` | One-bar aggressive motif | Beat Repeat, Auto Pan, filter-gate |
| Hook | `Wavetable Lead`, `MegaSquare`, `VideoGameLead`, `Metal-o Feedbackisimo Lead` | Aggressive synthetic hook | Distortion, delay throws, pitch envelope |
| Ambience | `Noise FX`, `AllFX`, `KJ Sawka FX Swells`, `Cluster Sound FX - Grainer` | Rises, impacts, short atmospheres | Risers, reverb throws, reverse tails |

## 4. Chicago House

Core identity: Classic drum machines, jacking groove, jazzy piano chords, simple bass, soulful vocal chops, and raw club energy.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Curt Bass`, `Warm Bass`, `Analog Bass`, `Operator Bass` | Jacking octave bass or simple syncopated root pattern | Light Saturator, low-pass, subtle swing |
| Drums | `Kit-707 Classic`, `Kit-909 Classic`, `Kit-808 Classic`, `Kit-Trax Classic`, `Kit-DMX Classic` | 707/909 kick-clap-hat grid with shuffle | Drum Buss, short room, groove pool swing |
| Chords | `TX Piano`, `Grand Piano Classic LA Stack`, `elec. piano`, `Whose Organ` | Jazzy stabs, piano riffs, minor 7/9 voicings | Glue Compressor, Chorus, filtered delay |
| Riff | `Sine Keys`, `Whose Organ`, `Electric Piano` | Simple repeated organ/piano riff | Auto Filter, subtle drive |
| Hook | `Vocal Chop`, `Piano House`, `Whose Organ`, `TX Piano` | Short vocal call or piano motif | Delay send, reverb throw |
| Ambience | `Slow Motion Pad`, `Grand Piano Pad` | Minimal; mostly room tone and send FX | Short reverb, tape-style saturation |

## 5. Deep House

Core identity: Mellow filtered synths, jazzy chord progressions, smooth bass, soft drums, soulful vocal feel, and restrained energy.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Warm Bass`, `Curt Bass`, `Analog Bass`, `Drift Bass`, `Electric Bass Palm` | Smooth syncopated bass, often offbeat or rolling | Low-pass, sidechain, soft Saturator |
| Drums | `Kit-707 Classic`, `Kit-606 Classic`, `Kit-909 Classic`, `Kit-Minimum`, `Grounded Kit` | Softer 4/4, shakers, claps with swing | Drum Buss low drive, groove swing, room reverb |
| Chords | `TX Piano`, `elec. piano`, `Grand Piano Equal Mellow Production`, `Analog Chords` | 7ths, 9ths, minor/major color chords | Auto Filter, Chorus-Ensemble, Echo |
| Riff | `Electric Riff`, `Drift Pluck`, `Tension Pluck` | Small soulful motif | Delay, filtered reverb |
| Hook | `Electric Lead`, `House Lead`, `Sine Keys` | Understated hook, not festival-sized | Chorus, gentle delay |
| Ambience | `Warm Pad`, `Slow Motion Pad`, `Grand Piano Pad`, `bocpad` | Wide, warm bed | Long reverb, sidechain, low-pass movement |

## 6. Disco House

Core identity: Funky basslines, disco string/guitar samples, bright drums, upbeat energy, and filter-swept loops.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Electric Bass`, `Electric Bass Slap`, `Electric Bass Open`, `Analog Bass` | Octave funk bass or walking disco loop | Compressor, Saturator, sidechain to kick |
| Drums | `Kit-707 Classic`, `Kit-909 Classic`, `Kit-DMX Classic`, `Kit-Trax Classic`, `Kit-Yellow` | Bright kick, clap, hats, tambourine-style top loops | Drum Buss, Glue Compressor, bus saturation |
| Chords | `Guitar-Chopper Chords`, `TX Piano`, `Grand Piano Classic LA Stack`, `synth. strings` | Chopped disco chords, piano stabs, strings | Auto Filter, sidechain, phaser/flanger |
| Riff | `Guitar-Chopper Chords`, `Guitar-French Guitar Pad`, `synth. strings` | Guitar/string sample-like riffs | Auto Filter sweeps, Beat Repeat for edits |
| Hook | `synth. strings`, `brass ens. 1`, `brass ens. 2`, `violin` | String/brass hook | Reverb, Chorus-Ensemble, filter opening |
| Ambience | `Guitar-French Guitar Pad`, `Grand Piano Pad` | Lush disco pad bed | Sidechain, tape-style compression |

## 7. Electro House

Core identity: Heavy synthesized leads, driving drums, robotic vocals, big drops, and sharper synth edges than classic house.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Wavetable Bass`, `MegaSquare`, `FMBass`, `Gooey Sub Rubber` | Pumping saw/square bass, octave drive | Saturator/Roar, sidechain, Auto Filter, multiband compression |
| Drums | `Kit-909 Mastodon`, `Kit-808 Magnetikz`, `Electrified Kit`, `Kit-Largeness`, `Kit-Meaty` | Loud four-on-floor, punchy snare/clap fills | Drum Buss, limiter, distortion bus |
| Chords | `Wavetable Chords`, `BigChord`, `Meld Chords` | Big stabs or build chords | Sidechain, reverb ducking |
| Riff | `MegaSquare`, `VideoGameLead`, `TheFMMachine` | Repeating drop riff | Pitch bend, filter envelope, gate |
| Hook | `Wavetable Lead`, `MegaSquare`, `Retro Steam Lead`, `Metal-o Feedbackisimo Lead` | Dominant synth lead | Delay, reverb throws, distortion |
| Ambience | `AllFX`, `Cluster Sound FX - Erosion Delay`, `KJ Sawka FX Swells` | Build FX, robotic vocal spaces | Vocoder, Beat Repeat, Redux |

## 8. French House

Core identity: Filter-swept disco samples, funky bass, lush texture, compression pump, guitar/string/piano chops, and glossy warmth.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Electric Bass Slap`, `Electric Bass Open`, `sawbass`, `Warm Bass` | Funky eighth-note bass, octave movement | Sidechain, Auto Filter, Compressor/Glue |
| Drums | `Kit-909 Classic`, `Kit-707 Classic`, `Kit-DMX Studio`, `Kit-Trax Deeptrax`, `Kit-Yellow` | Bright looped house drums | Glue Compressor, sidechain pump, light saturation |
| Chords | `Guitar-Chopper Chords`, `Guitar-French Guitar Pad`, `Grand Piano Classic LA Stack`, `synth. strings` | Loopable filtered chord/sample chops | Auto Filter, phaser, sidechain |
| Riff | `Guitar-Chopper Chords`, `synth. strings`, `TX Piano` | Disco loop riff | Filter automation, Beat Repeat micro-edits |
| Hook | `brass ens. 1`, `synth. strings`, `vibraphone`, `bell` | Bright sample-like hook | Chorus, compression, delay |
| Ambience | `Guitar-French Guitar Pad`, `Grand Piano Pad`, `Slow Motion Pad` | Glossy support layer | Sidechain, filtered reverb |

## 9. Funky House

Core identity: Bouncy drums, funky basslines, brass/guitar/piano stabs, soulful vocal hooks, and high-energy groove.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Electric Bass Slap`, `Electric Bass`, `sawbass`, `Curt Bass` | Bouncy syncopated funk bass | Compressor, Saturator, envelope filter |
| Drums | `Kit-707 Freshen Up`, `Kit-909 Classic`, `Kit-DMX Classic`, `Kit-Yellow`, `Kit-Wood` | Upbeat claps, hats, percussion | Drum Buss, swing, room reverb |
| Chords | `Guitar-Chopper Chords`, `TX Piano`, `Whose Organ`, `brass ens. 1` | Short stabs and comping | Auto Filter, slap delay |
| Riff | `Guitar-Chopper Chords`, `Electric Riff`, `brass ens. 2` | Funk guitar/brass-style motif | Wah/filter, phaser |
| Hook | `brass ens. 1`, `Whose Organ`, `TX Piano`, `vibraphone` | Soulful hook or vocal-chop support | Delay throws, reverb sends |
| Ambience | `Grand Piano Pad`, `Guitar-French Guitar Pad` | Light, non-dominant bed | Short plate reverb |

## 10. Garage House

Core identity: Organ basslines, soulful vocals, upbeat drums, swung/shuffled groove, piano/organ stabs, and club warmth.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Whose Organ`, `elec. organ`, `Operator Bass`, `Warm Bass` | Organ bass riff or bouncy sub | Saturator, short decay, sidechain |
| Drums | `Kit-909 Classic`, `Kit-707 Classic`, `Kit-606 Classic`, `Kit-Trax Classic`, `Otari Bounce Kit` | 4x4 garage swing, shuffled hats, claps | Groove swing, Drum Buss, short room |
| Chords | `Whose Organ`, `elec. piano`, `TX Piano`, `Grand Piano Classic LA Stack` | Organ/piano stabs, soulful voicings | Chorus, Auto Filter, Echo |
| Riff | `Whose Organ`, `Sine Keys`, `elec. organ` | Organ riff with call-response | Delay, filter movement |
| Hook | `Vocal Chop`, `TX Piano`, `Whose Organ` | Vocal chop or piano hook | Beat Repeat/chop, reverb throws |
| Ambience | `Warm Pad`, `Grand Piano Pad` | Subtle pad or vocal-room bed | Low-pass, reverb send |

## 11. G-House

Core identity: Gritty rap/gangsta vocal samples, heavy trap-influenced drums, dark bass, sparse chords, and swaggering club pressure.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `808 Bass`, `Gooey Sub Rubber`, `Operator Bass`, `Drift Bass`, `MatrixBass` | Sparse dark bass hits, sliding sub, wobble motifs | Saturator, Auto Filter, sidechain, pitch glide |
| Drums | `Kit-808 Classic`, `Kit-DMX Tightdope`, `Kit-DMX Bust It`, `Kit-909 Mastodon`, `Swang Bap Kit` | Heavy kick/clap, trap hats, minimal percussion | Drum Buss, clipping, parallel distortion |
| Chords | `Analog Chords`, `Dark Pad`, `Whose Organ` | Sparse dark stabs | Low-pass, reverb, distortion |
| Riff | `Drift Pluck`, `Wavetable Pluck`, `Percu Bass` | Menacing short motif | Filter envelope, pitch bends |
| Hook | `Vocal Chop`, `MegaSquare`, `Trap Lead`, `Retro Steam Lead` | Rap sample or dark lead hook | Beat Repeat, formant/vocoder, delay |
| Ambience | `Slow Motion Pad`, `Cluster Sound FX - Grainer`, `AllFX` | Dark atmosphere and risers | Reverb, Redux, tape noise |

## 12. Minimal House

Core identity: Simple repetitive drums, subtle filtered percussion, tiny synth motifs, atmospheric reduction, and understated groove.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Operator Bass`, `Drift Bass`, `Warm Bass`, `Percu Bass` | One- or two-note clipped bass, very controlled | Short decay, low-pass, sidechain |
| Drums | `Kit-Minimum`, `Kit-606 Classic`, `Kit-606 Cathode`, `Kit-707 Studio`, `Grounded Kit` | Sparse kick, hats, micro-percussion | Drum Buss low drive, Utility width, small room |
| Chords | `Analog Chords`, `Sine Keys`, `Whose Organ` | Very short stabs or muted chord ticks | Auto Filter, delay sends |
| Riff | `Percu Tone`, `TwoPluckedStrings`, `Drift Pluck` | Minimal repeating click/pluck | Echo, Auto Pan, random velocity |
| Hook | `HypnoticFM`, `ElectricSeq`, `PureFMSequence` | Hypnotic micro-hook | Filter LFO, delay feedback |
| Ambience | `Slow 5th Pad`, `AirMembrane`, `Dreamy` | Quiet texture behind groove | High-pass reverb, granular delay |

## 13. Progressive House

Core identity: Epic leads, driving drums, long builds, melodic bass, soaring vocals or hook melodies, and evolving automation.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Wavetable Bass`, `Drift Bass`, `Warm Bass`, `MatrixBass` | Driving offbeat or rolling octave bass | Sidechain, low-pass opening through build |
| Drums | `Kit-909 Classic`, `Kit-909 Myrtle`, `Kit-Largeness`, `Electrified Kit`, `Kit-707 Studio` | Driving 4/4, big claps, build hats | Drum Buss, risers, reverb tails, crash layers |
| Chords | `Wavetable Chords`, `BigChord`, `Grand Piano Classic LA Stack`, `Analog Chords` | Big sustained progressions | Sidechain, reverb ducking, filter automation |
| Riff | `Wavetable Pluck`, `ElectricSeq`, `HypnoticFM` | Evolving arp/riff | Arpeggiator, Echo, Auto Filter |
| Hook | `Wavetable Lead`, `MegaSquare`, `SlowMotion`, `Retro Steam Lead` | Strong melodic topline | Delay, wide reverb, pitch bend |
| Ambience | `Slow Motion Pad`, `Grand Piano Pad`, `Dreamy`, `WarmStrings` | Wide breakdown pad | Hybrid Reverb, Chorus-Ensemble, automation lanes |

## 14. Tech House

Core identity: Heavy/rolling basslines, minimalist drum patterns, dry percussion, futuristic textures, short vocal chops, and DJ-tool structure.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Operator Bass`, `Drift Bass`, `Analog Bass`, `Percu Bass`, `Gooey Sub Rubber` | Rolling 1/16 bass, offbeat gaps, tight envelope | Saturator, sidechain, low-pass, Mono Utility |
| Drums | `Kit-909 Classic`, `Kit-909 Tresor`, `Kit-606 Cathode`, `Kit-707 Smasher`, `Kit-Minimum` | Dry kick, clap, hats, percussion loop | Drum Buss, short room, swing, transient focus |
| Chords | `Analog Chords`, `Operator Chords`, `Whose Organ` | Small stabs, often single-note chord triggers | Echo, Auto Filter, reverb send |
| Riff | `Acid Riff`, `Operator Pluck`, `Drift Pluck`, `ElectricSeq` | Short percussive synth riff | Delay, filter envelope, Auto Pan |
| Hook | `Minimal Hook`, `Operator Lead`, `Drift Lead`, `HypnoticFM` | One phrase or vocal chop | Beat Repeat, delay throw, filter gating |
| Ambience | `Dark Pad`, `Meld Pad`, `ClusterDelay`, `AllFX` | Futuristic background movement | Grain delay, low reverb, high-pass |

## 15. Tribal House

Core identity: Percussion-led groove, congas/toms/shakers, darker synths, hypnotic repetition, sparse harmony, and rhythmic call-response.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Warm Bass`, `Operator Bass`, `Curt Bass`, `Analog Bass` | Repetitive root bass, often sparse | Sidechain, low-pass, minimal distortion |
| Drums | `Kit-Ethno`, `Kit-Wood`, `Kit-C78 Classic`, `Kit-808 Classic`, `AfroBars1`, `AfroBars2`, `Grounded Kit` | Congas, bongos, toms, shakers, four-on-floor kick | Drum Buss, groove swing, reverb room |
| Chords | `Analog Chords`, `Slow 5th Pad`, `Whose Organ` | Minimal drone/stabs rather than full progressions | Filtered reverb, delay |
| Riff | `AfroBars1`, `AfroBars2`, `Percu Tone`, `Bongo`, `Conga` | Percussive melodic loop | Auto Pan, Echo, velocity variation |
| Hook | `brass ens. 1`, `flute`, `Metal Agogo`, `Dynamic Klang` | Chant-like motif or percussion melody | Delay, reverb, resonator |
| Ambience | `Slow Motion Pad`, `AirMembrane`, `MembUFORelease` | Dark ritual bed | Long reverb, low-pass, noise layers |

## 16. Tropical House

Core identity: Bright sunny synths, upbeat drums, soft plucks, natural/organic soundscapes, relaxed bass, and melodic toplines.

| Role | Ableton instrument/preset candidates | Pattern fit | Effects and automation |
| --- | --- | --- | --- |
| Bass | `Warm Bass`, `Curt Bass`, `Electric Bass Open`, `Drift Bass` | Clean offbeat bass or simple syncopated root | Gentle sidechain, light compression |
| Drums | `Kit-Wood`, `Kit-Yellow`, `Kit-707 Freshen Up`, `Acoustified Kit`, `Kindified Kit` | Light kick, clap, shaker, hand percussion | Room reverb, soft Drum Buss, swing |
| Chords | `elec. piano`, `TX Piano`, `Grand Piano Equal Bright Production`, `Guitar-Soft Tremolo Room` | Bright major/minor 7 chords | Chorus, reverb, high-pass |
| Riff | `Tension Pluck`, `Collision`, `vibraphone`, `crispy xylophone`, `bell` | Marimba/kalimba-like pluck pattern | Delay, reverb, Auto Pan |
| Hook | `flute`, `bell`, `vibraphone`, `fairy tale`, `Wavetable Lead` | Simple sunny melody | Delay, wide reverb |
| Ambience | `Guitar-French Guitar Pad`, `Grand Piano Thin Air`, `Slow Motion Pad`, natural field-like FX | Beach/air/nature-like bed | High-pass, reverb, filtered noise |

## Implementation Matching Rules

1. Detect the subgenre first. Do not collapse all entries to `house`, `deep_house`, or `tech_house` once these 16 categories are added to the style detector.
2. For every generated MIDI role, emit 5-12 browser candidates ordered by:
   - exact installed preset/kit match,
   - subgenre role match,
   - prompt keyword match,
   - broader stock instrument fallback.
3. Prefer installed `.adg`/`.adv` names over generic instrument names. Example: choose `Kit-909 Tresor`, `Whose Organ`, or `Slow Motion Pad` before `Drum Rack`, `Operator`, or `Analog`.
4. Keep generic devices as final fallback only: `Analog Bass`, `Wavetable Lead`, `Operator Bass`, `Electric Piano`, `Drift Pluck`.
5. Treat effects as chain hints, not load requirements, until device insertion is verified in the Ableton bridge.
6. Use different drum candidate pools for `Bd`, `Snare / Clap`, `Hh / Sh / Rd`, `Percussion`, and `Drum Instrument`, but let consolidated drums use the broadest kit-level match.

## References

- [Ableton Live 12 Instrument Reference](https://www.ableton.com/en/live-manual/12/live-instrument-reference/)
- [Ableton Drum Machines](https://www.ableton.com/en/packs/drum-machines/)
- [Ableton Electronik Drums](https://www.ableton.com/en/packs/electronik-drums/)
- [Ableton Synth Essentials](https://www.ableton.com/en/packs/synth-essentials/)
- [Ableton Analog](https://www.ableton.com/packs/analog/)
