const promptLibrary = [
  {
    id: "arrangement",
    name: "Arrangement",
    meta: "Arrangement prompts",
    title: "Build the structure fast",
    prompts: [
      {
        label: "Dance Mainstage",
        tags: ["dance", "mainstage", "festival"],
        text: "Create an expanded Dance and Mainstage arrangement with euphoric chord progressions, massive tension builds, hands-up pre-drop, a pounding main drop, atmospheric breakdown, massive second build, final drop, and outro. Features parallel chord lock, driving four-on-the-floor energy, and separate tracks for chords, pad, riff, hook, bass, kick, hats, snare / clap, percussion, and ambience.",
      },
      {
        label: "Downtempo",
        tags: ["downtempo", "chill", "arrangement"],
        text: "Create an expanded Downtempo arrangement featuring lush, jazzy, neo-soul chord voicings, a soft texture intro, relaxed groove entrance, warm melodic themes, stripped middle breakdown, organic return, and slow fading outro. Keeps the drum patterns laid-back and syncopated, leaving spacious room for warm pads, ambient textures, deep bass, and elegant riffs.",
      },
      {
        label: "Drum n Bass",
        tags: ["drum n bass", "breaks", "172 bpm"],
        text: "Create an expanded 172 BPM Drum n Bass arrangement featuring a dark atmospheric intro, rolling sub / Reese basslines, fast breakbeat drum rolls, building snare risers, melodic drops, breakdowns, and high-energy final sections. Uses separate tracks for kick, snare / clap, busy hats, syncopated ghost percussion, bass, pad, riff, hook, and ambience.",
      },
      {
        label: "Hip Hop",
        tags: ["hip hop", "verse", "hook"],
        text: "Create an expanded Hip Hop arrangement with classic 90 BPM boom-bap elements, dusty soulful chord structures, intro, verse, hook, verse two, emotional bridge, final hook, and clean outro. Keep the track vocal-friendly with solid low-end pocket bass, crisp snare / clap, organic percussion shuffles, and distinct chords, pad, riff, hook, and ambient soundscapes.",
      },
      {
        label: "House",
        tags: ["house", "club", "125 bpm"],
        text: "Create an expanded House arrangement featuring classic 125 BPM four-on-the-floor kick grids, driving offbeat open hi-hats, bouncy syncopated basslines, parallel chord motion, DJ-friendly intro/outro, a main drop, and lush melodic breakdown. Keeps chords, pads, plucky riffs, lead hooks, and percussion separated on dedicated tracks.",
      },
      {
        label: "90s Jungle",
        tags: ["jungle", "90s", "breakbeat"],
        text: "Create an expanded 90s Jungle arrangement with warm tape-saturated pad intro, chopped Amen breakbeat teases, deep dub-wise sub bass melodies, ragga-style vocal cuts, atmospheric breakdowns, and high-tempo drum edits. Features dedicated tracks for rides / hats, kick, snare / clap, percussion, bass, pad, riff, hook, and ambience.",
      },
      {
        label: "Modern Pop",
        tags: ["pop", "chorus", "radio"],
        text: "Create an expanded Modern Pop arrangement with clean-voiced, highly expressive chord sequences, intro, verse, pre-chorus, a soaring chorus, verse two, bridge, final chorus, and clean radio outro. Uses separate, polished tracks for chords, warm sustained pads, melodic riffs, catch-heavy lead hooks, pop bass, kick, hats, clap, percussion, and background ambience.",
      },
      {
        label: "Reggae Dance Hall",
        tags: ["reggae", "dance hall", "offbeat"],
        text: "Create an expanded Reggae and Dance Hall arrangement featuring classic offbeat bubble chords, deep warm sub basslines, loose shuffled percussion, a groove-filled verse, hook, percussion breakdown, and clean outro. Separate tracks for clap, hats, chords, pad, riff, hook, and ambience.",
      },
      {
        label: "Reggaeton",
        tags: ["reggaeton", "dembow", "latin"],
        text: "Create an expanded Reggaeton arrangement utilizing the infectious syncopated Dembow clave rhythm, sliding basslines, warm minor chord progressions, intro, pre-hook, main hook, club breakdown, final lift, and outro. Uses dedicated kick, clap, hats, percussion, bass, chords, pad, riff, hook, and ambience tracks.",
      },
      {
        label: "Rock Country",
        tags: ["rock", "country", "song"],
        text: "Create an expanded Rock and Country arrangement with acoustic chord beds, intro electric riffs, verse, pre-chorus, driving chorus, bridge, soaring guitar-style lead hook, and outro. Features separate tracks for chords, pad, riff, hook, bass, kick, snare / clap, hats, percussion, and ambience.",
      },
      {
        label: "Techno",
        tags: ["techno", "hypnotic", "club"],
        text: "Create an expanded 130 BPM Techno arrangement featuring driving hypnotic kick foundations, dark single-note modal basslines, industrial synth sweeps, industrial claps, relentless offbeat hats, tension breaks, and raw peak-time final drives. Includes dedicated tracks for kick, hats, clap, percussion, bass, riff, pad, hook, ambience, and chords.",
      },
      {
        label: "Trance",
        tags: ["trance", "uplifting", "138 bpm"],
        text: "Create an expanded 138 BPM Trance arrangement featuring euphoric arpeggiated melodic builds, lush sustained pad layers, emotional breakdown hook reveals, huge snare build risers, and soaring main drops. Separate tracks for chords, pad, riff, hook, rolling bass, kick, hats, clap, percussion, and cinematic ambience.",
      },
      {
        label: "Trap",
        tags: ["trap", "808", "dark"],
        text: "Create an expanded 140 BPM Trap arrangement with dark detuned minor progressions, gliding 808 sub bass lines, fast hi-hat rolls with triplet variations, half-time snare placement, atmospheric verses, breakdowns, and hard drops. Separate tracks for chords, pad, riff, hook, bass, kick, hats, snare, percussion, and spacey ambience.",
      },
      {
        label: "Ambient Cinematic",
        tags: ["ambient", "cinematic", "slow"],
        text: "Create an expanded Ambient Cinematic arrangement with wide evolving textures, low drone sub bass, minimal melodic motifs, sparse breakdowns, emotional chord blooms, and long trailing fades. Uses separate tracks for pad, ambience, chords, bass pulse, subtle percussion, hook, and riff layers.",
      },
      {
        label: "Hyperpop",
        tags: ["hyperpop", "bright", "glitch"],
        text: "Create an expanded Hyperpop arrangement featuring instant hook intros, neon-bright plucks, frantic glitch breakdown stutters, maximum energy drops, and abrupt endings. Separate tracks for chords, pad, riff, hook, glitch bass, kick, hats, snare / clap, percussion, and bright ambience.",
      },
      {
        label: "UK Garage",
        tags: ["uk garage", "shuffle", "club"],
        text: "Create an expanded UK Garage arrangement with bouncy 132 BPM skippy 2-step groove grids, offbeat swung hi-hats, jazzy rhodes chord stab syncopations, vocal chops, and deep sub basslines. Uses separate tracks for kick, snare / clap, hats, percussion, bass, chords, pad, riff, hook, and ambience.",
      },
      {
        label: "45 Second Clip",
        tags: ["short", "social", "hook"],
        text: "Create a highly engaging 45-second arrangement for short-form social content, featuring an instant high-impact hook, quick driving groove, rapid riser tension build, memorable drop, and clean ending. Keeps all track parts separate for full production later.",
      },
    ],
  },
  {
    id: "drums",
    name: "Drums",
    meta: "Grooves, fills, and variations",
    title: "Shape the pocket",
    prompts: [
      {
        label: "Trap Drums",
        tags: ["trap", "drums", "hi-hats", "fills"],
        text: "Create a hard trap drum pattern with punchy kicks, sharp snares, rolling hi-hats, triplet variations, and occasional snare fills.",
      },
      {
        label: "Boom Bap Swing",
        tags: ["boom bap", "drums", "swing", "90 bpm"],
        text: "Create a 90 BPM boom bap drum groove with a dusty swing feel, tight kick placement, crisp snare, ghost notes, and subtle vinyl-style percussion.",
      },
      {
        label: "House Groove",
        tags: ["house", "drums", "club", "125 bpm"],
        text: "Create a 125 BPM house drum groove with four-on-the-floor kick, offbeat open hats, layered claps, shuffled percussion, and a steady club feel.",
      },
      {
        label: "Four Fill Pack",
        tags: ["drum fills", "transition", "variation"],
        text: "Create four drum fills for transitioning between sections: one subtle fill, one snare build, one tom fill, and one glitch-style fill.",
      },
      {
        label: "Percussion Builder",
        tags: ["percussion", "energy", "build", "shaker"],
        text: "Add percussion layers that gradually increase energy over 16 bars using shakers, rides, claps, hats, and syncopated accents.",
      },
      {
        label: "Verse to Drop Drums",
        tags: ["drums", "variation", "verse", "drop"],
        text: "Create three variations of the current drum pattern: a minimal verse version, a fuller chorus version, and a high-energy drop version.",
      },
    ],
  },
  {
    id: "bass",
    name: "Bass",
    meta: "Bassline starters",
    title: "Lock the low end",
    prompts: [
      {
        label: "Hip-Hop Sub",
        tags: ["sub", "hip-hop", "bass", "90 bpm"],
        text: "Create a deep 90 BPM hip-hop sub bassline that follows the root notes, leaves space for vocals, and adds subtle slides at the end of phrases.",
      },
      {
        label: "House Bounce",
        tags: ["house", "bass", "groove", "kick"],
        text: "Create a 125 BPM house bassline with a bouncy offbeat rhythm, warm low-end tone, and groove that locks tightly with the kick.",
      },
      {
        label: "EDM Drop Bass",
        tags: ["edm", "drop", "bass", "energy"],
        text: "Create a high-energy EDM drop bassline with rhythmic movement, octave jumps, syncopation, and a powerful call-and-response pattern.",
      },
      {
        label: "Funk Bass",
        tags: ["funk", "bass", "syncopated", "octaves"],
        text: "Create a funky bassline with syncopated rhythms, short note stabs, octave movement, and a playful groove.",
      },
      {
        label: "Cinematic Low Pulse",
        tags: ["cinematic", "dark", "bass", "tension"],
        text: "Create a dark cinematic bass part using long sustained low notes, subtle movement, tension-building intervals, and gradual intensity changes.",
      },
      {
        label: "Three Bass States",
        tags: ["bass", "variation", "verse", "drop"],
        text: "Create three bassline variations for verse, buildup, and drop while keeping the same key and main groove identity.",
      },
    ],
  },
  {
    id: "melody",
    name: "Melody",
    meta: "Chords, hooks, and leads",
    title: "Find the memorable part",
    prompts: [
      {
        label: "Emotional Chords",
        tags: ["chords", "minor", "pop", "emotional"],
        text: "Create an emotional four-chord progression in a minor key with a modern pop feel, smooth voice leading, and room for a vocal melody.",
      },
      {
        label: "Catchy Lead Hook",
        tags: ["lead", "hook", "melody", "catchy"],
        text: "Create a catchy lead melody hook that repeats clearly, uses simple rhythmic variation, and works well as the main identity of the track.",
      },
      {
        label: "Counter-Melody",
        tags: ["counter melody", "support", "lead"],
        text: "Create a counter-melody that supports the main melody without overpowering it. Use a different rhythm and register.",
      },
      {
        label: "Ambient Pads",
        tags: ["ambient", "pad", "chords", "cinematic"],
        text: "Create a slow ambient pad progression with evolving chords, suspended tones, and a cinematic emotional feel.",
      },
      {
        label: "Bright Arp",
        tags: ["arpeggio", "synth", "16th notes"],
        text: "Create a 16th-note arpeggio pattern based on the current chord progression with subtle rhythmic variation and a bright synth tone.",
      },
      {
        label: "Melody Variations",
        tags: ["melody", "variation", "hook"],
        text: "Create three variations of the current melody: one simpler, one more energetic, and one more emotional.",
      },
    ],
  },
  {
    id: "mixing",
    name: "Mixing",
    meta: "Mix decisions",
    title: "Clean up the session",
    prompts: [
      {
        label: "Basic Mix Cleanup",
        tags: ["mixing", "cleanup", "mud", "harsh"],
        text: "Analyze the mix and suggest cleanup moves for muddy frequencies, harsh highs, clashing instruments, and unnecessary low-end buildup.",
      },
      {
        label: "EQ Balance",
        tags: ["eq", "mixing", "frequency"],
        text: "Suggest EQ moves for each major element so the kick, bass, drums, vocals, synths, and effects have clearer frequency space.",
      },
      {
        label: "Compression Map",
        tags: ["compression", "mixing", "dynamics"],
        text: "Suggest compression settings for drums, bass, vocals, and synths, including attack, release, ratio, and gain reduction targets.",
      },
      {
        label: "Reverb Plan",
        tags: ["reverb", "space", "mixing"],
        text: "Create a reverb plan for the track using short room, plate, hall, and atmospheric reverbs while keeping the mix clear.",
      },
      {
        label: "Stereo Width",
        tags: ["stereo", "width", "mixing"],
        text: "Suggest stereo width improvements while keeping kick, bass, snare, and lead vocal centered.",
      },
      {
        label: "Gain Staging",
        tags: ["gain", "headroom", "mixing"],
        text: "Set up a gain staging plan so all tracks have clean headroom before mixing and the master bus is not overloaded.",
      },
    ],
  },
  {
    id: "effects",
    name: "Effects",
    meta: "Transitions and sound design",
    title: "Add movement",
    prompts: [
      {
        label: "Riser Into Drop",
        tags: ["riser", "drop", "transition", "noise"],
        text: "Create a riser effect leading into the drop using pitch rise, noise sweep, increasing reverb, and a short silence before impact.",
      },
      {
        label: "Reverse Transition",
        tags: ["reverse", "transition", "reverb"],
        text: "Create a reverse transition effect using reversed cymbals, reversed reverb tails, and filtered noise before the next section.",
      },
      {
        label: "Drop Impact",
        tags: ["impact", "drop", "sub", "crash"],
        text: "Create a powerful drop impact using layered sub hit, noise burst, crash, short reverb tail, and transient punch.",
      },
      {
        label: "Filter Build",
        tags: ["filter", "automation", "build"],
        text: "Add filter automation over 16 bars to build tension, gradually opening the sound before the next section.",
      },
      {
        label: "Delay Throws",
        tags: ["delay", "throws", "vocal", "melody"],
        text: "Add delay throws to selected melody or vocal phrases at the end of every 4 or 8 bars for movement and space.",
      },
      {
        label: "Glitch Details",
        tags: ["glitch", "stutter", "pitch", "sound design"],
        text: "Create glitch-style effects using stutters, short repeats, pitch shifts, and chopped audio moments.",
      },
    ],
  },
  {
    id: "instruments",
    name: "Instruments",
    meta: "Genre-aware sound palettes",
    title: "Choose stronger sounds",
    prompts: [
      {
        label: "Quick EDM Defaults",
        tags: ["genre-aware instruments", "edm", "playback", "fast"],
        text: "Create an expanded song sketch with genre-aware Ableton instruments so I can hear something fast. Use dedicated tracks for Chords, Hh / Sh / Rd, Pad, Riff, Hook, Percussion, Snare / Clap, Ambience, Hh / Sh / Rd +, Bd, and Bass. Copy the clips to Arrangement View and start playback.",
      },
      {
        label: "Load EDM Sounds",
        tags: ["instruments", "edm", "load sounds"],
        text: "Load genre-aware Ableton instruments for the current EDM tracks: chords, bass, drums, and lead.",
      },
      {
        label: "Four Track Starter",
        tags: ["instruments", "chords", "bass", "drums"],
        text: "Create an expanded song sketch with genre-aware Ableton instruments using separate musical parts instead of one generic drum track. Add MIDI clips for chords, pad, riff, hook, bass, kick, hats, percussion, clap, and ambience, then start playback.",
      },
      {
        label: "House Defaults",
        tags: ["house", "genre-aware instruments", "125 bpm"],
        text: "Create an expanded 125 BPM house song sketch with genre-aware Ableton instruments: warm chords, bouncy bass, club kick, open hats, percussion, clap, pad, riff, ambience, and a simple lead hook. Copy it to Arrangement View and start playback.",
      },
      {
        label: "Dark Minor Defaults",
        tags: ["dark", "minor", "genre-aware instruments"],
        text: "Create a quick dark minor-key idea with genre-aware Ableton instruments: moody chords, deep bass, punchy drums, and a sparse lead. Copy it to Arrangement View and start playback.",
      },
      {
        label: "Audition Current Idea",
        tags: ["instruments", "current tracks", "playback"],
        text: "Load genre-aware Ableton instruments onto the current generated tracks, balance the track volumes, and start playback so I can audition the idea quickly.",
      },
    ],
  },
  {
    id: "genres",
    name: "Genres",
    meta: "Style starters",
    title: "Pick a sound world",
    prompts: [
      {
        label: "Dance and Mainstage",
        tags: ["dance", "mainstage", "festival"],
        text: "Create an expanded Dance and Mainstage song sketch with genre-aware Ableton instruments, a festival-sized hook, wide chords, bright riff, rolling percussion, big kick, bass, ambience, and a clear intro-build-drop-break-final-drop structure.",
      },
      {
        label: "Downtempo",
        tags: ["downtempo", "chill", "textural"],
        text: "Create an expanded Downtempo song sketch with genre-aware Ableton instruments, warm chords, slow drums, soft percussion, deep bass, hazy pad, subtle riff, emotional hook, ambience, and a relaxed arrangement.",
      },
      {
        label: "Drum n Bass",
        tags: ["drum n bass", "breaks", "bass"],
        text: "Create an expanded Drum n Bass song sketch with genre-aware Ableton instruments, fast break-inspired hats, separate kick and snare tracks, rolling bass, atmospheric pad, riff, hook, percussion, ambience, and high-energy sections.",
      },
      {
        label: "90s Jungle",
        tags: ["jungle", "90s", "breakbeat"],
        text: "Create an expanded 90s Jungle song sketch with genre-aware Ableton instruments, chopped break-style top drums, separate kick and clap tracks, sub bass, airy pad, rave riff, hook, percussion, ambience, and a raw club arrangement.",
      },
      {
        label: "Hip Hop",
        tags: ["hip hop", "beat", "groove"],
        text: "Create an expanded Hip Hop song sketch with genre-aware Ableton instruments, dusty chords, pad, bass, kick, snare, hats, percussion, hook, riff, ambience, and sections for intro, verse, hook, verse two, final hook, and outro.",
      },
      {
        label: "Modern Pop",
        tags: ["pop", "hook", "radio"],
        text: "Create an expanded Modern Pop song sketch with genre-aware Ableton instruments, emotional chords, pad, clean bass, programmed drums, percussion, hook melody, supporting riff, ambience, and a verse-pre-chorus-chorus style arc.",
      },
      {
        label: "Reggae and Dance Hall",
        tags: ["reggae", "dance hall", "offbeat"],
        text: "Create an expanded Reggae and Dance Hall song sketch with genre-aware Ableton instruments, offbeat chords, warm bass, kick, clap, hats, percussion, pad, riff, hook, ambience, and a relaxed but danceable arrangement.",
      },
      {
        label: "Reggaeton",
        tags: ["reggaeton", "dembow", "latin"],
        text: "Create an expanded Reggaeton song sketch with genre-aware Ableton instruments, dembow-inspired drum parts, separate kick, clap, hats, percussion, bass, chords, pad, riff, hook, ambience, and a catchy club structure.",
      },
      {
        label: "Rock and Country",
        tags: ["rock", "country", "song"],
        text: "Create an expanded Rock and Country song sketch with genre-aware Ableton instruments, chord bed, bass, kick, snare, hats, percussion, pad, riff, hook melody, ambience, and a verse-chorus arrangement.",
      },
      {
        label: "Techno",
        tags: ["techno", "hypnotic", "club"],
        text: "Create an expanded Techno song sketch with genre-aware Ableton instruments, hypnotic riff, dark pad, driving kick, separate hats, clap, percussion, bass, ambience, minimal hook, and a DJ-friendly arrangement.",
      },
      {
        label: "Trance",
        tags: ["trance", "uplifting", "supersaw"],
        text: "Create an expanded Trance song sketch with genre-aware Ableton instruments, uplifting chords, rolling bass, bright riff, memorable hook, separate kick, clap, hats, percussion, pad, ambience, and a long emotional build.",
      },
      {
        label: "Trap",
        tags: ["trap", "808", "dark"],
        text: "Create an expanded Trap song sketch with genre-aware Ableton instruments, dark chords, deep bass, separate kick, snare / clap, hats, percussion, pad, riff, hook, ambience, and sections for intro, verse, hook, verse two, and outro.",
      },
      {
        label: "Afrobeats",
        tags: ["afrobeats", "syncopated", "rhythm"],
        text: "Create an expanded Afrobeats song sketch with genre-aware Ableton instruments, syncopated 'clave' rhythms, warm chords, catchy pentatonic hook, melodic bass, separated drums, percussion, ambience, and a rhythmic arrangement.",
      },
      {
        label: "Amapiano",
        tags: ["amapiano", "log drum", "south africa"],
        text: "Create an expanded Amapiano song sketch with genre-aware Ableton instruments, 113 BPM, log-drum bass rolls, steady kick, deep pads, percussive synth hook, constant shakers, separated drums, and a club-focused arrangement.",
      },
    ],
  },
  {
    id: "artist-references",
    name: "Artist References",
    meta: "Producer references",
    title: "Borrow direction, not copies",
    prompts: [
      {
        label: "Fred again..",
        tags: ["emotional", "house", "vocal chops"],
        text: "Create an original expanded song sketch using Fred again.. only as a loose reference for intimate vocal-chop energy, emotional house chords, simple repeating motifs, live-feeling transitions, and warm club drums. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Four Tet",
        tags: ["organic", "micro-samples", "leftfield"],
        text: "Create an original expanded song sketch using Four Tet only as a loose reference for organic percussion, small textured loops, warm chords, evolving arrangement, and hypnotic details. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Skrillex",
        tags: ["bass", "drops", "sound design"],
        text: "Create an original expanded song sketch using Skrillex only as a loose reference for aggressive bass movement, sharp drum edits, high-contrast drops, vocal-style chops, and bold sound-design moments. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Flume",
        tags: ["future bass", "glitch", "texture"],
        text: "Create an original expanded song sketch using Flume only as a loose reference for wonky drums, textured synths, warped hooks, unusual transitions, and wide emotional chords. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Disclosure",
        tags: ["house", "garage", "groove"],
        text: "Create an original expanded song sketch using Disclosure only as a loose reference for tight house drums, UK garage swing, punchy bass, clean chord stabs, and vocal-friendly hook sections. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Kaytranada",
        tags: ["groove", "funk", "swing"],
        text: "Create an original expanded song sketch using Kaytranada only as a loose reference for syncopated drums, warm bass, funky chords, laid-back swing, and danceable pocket. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Burial",
        tags: ["garage", "ambient", "dark"],
        text: "Create an original expanded song sketch using Burial only as a loose reference for dark UK garage mood, ghostly ambience, shuffled drums, distant vocal-like textures, and rainy-night atmosphere. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Aphex Twin",
        tags: ["idm", "experimental", "drums"],
        text: "Create an original expanded song sketch using Aphex Twin only as a loose reference for unusual rhythms, strange melodic fragments, textured synths, leftfield arrangement changes, and experimental energy. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "deadmau5",
        tags: ["progressive", "house", "melodic"],
        text: "Create an original expanded song sketch using deadmau5 only as a loose reference for long progressive builds, arpeggiated motifs, clean club drums, evolving chords, and patient arrangement movement. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Madeon",
        tags: ["pop", "electro", "bright"],
        text: "Create an original expanded song sketch using Madeon only as a loose reference for bright electronic-pop chords, uplifting hooks, energetic drums, clean synth layers, and polished transitions. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Porter Robinson",
        tags: ["emotional", "electronic", "anthem"],
        text: "Create an original expanded song sketch using Porter Robinson only as a loose reference for emotional electronic chords, nostalgic lead hooks, big dynamic contrast, bright textures, and euphoric arrangement arcs. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Bicep",
        tags: ["breakbeat", "melodic", "club"],
        text: "Create an original expanded song sketch using Bicep only as a loose reference for melodic breakbeat energy, warm pads, repeating synth motifs, club drums, and emotional builds. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Bonobo",
        tags: ["downtempo", "organic", "cinematic"],
        text: "Create an original expanded song sketch using Bonobo only as a loose reference for organic downtempo percussion, warm bass, lush pads, cinematic ambience, and gradual arrangement evolution. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Floating Points",
        tags: ["jazz", "electronic", "evolving"],
        text: "Create an original expanded song sketch using Floating Points only as a loose reference for jazz-influenced harmony, evolving synth layers, patient groove development, and detailed texture. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Jamie xx",
        tags: ["sample feel", "club", "minimal"],
        text: "Create an original expanded song sketch using Jamie xx only as a loose reference for minimal club drums, spacious hooks, chopped texture ideas, warm bass, and restrained emotional lift. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Overmono",
        tags: ["breaks", "uk club", "bass"],
        text: "Create an original expanded song sketch using Overmono only as a loose reference for UK club breaks, punchy bass, vocal-like chops, emotional pads, and sharp arrangement edits. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Arca",
        tags: ["experimental", "sound design", "deconstructed"],
        text: "Create an original expanded song sketch using Arca only as a loose reference for deconstructed rhythms, expressive sound design, unstable textures, dramatic contrast, and unconventional arrangement. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "SOPHIE",
        tags: ["hyperpop", "plastic", "sound design"],
        text: "Create an original expanded song sketch using SOPHIE only as a loose reference for glossy synthetic percussion, bold bass design, bright hyperpop hooks, and playful high-impact transitions. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Metro Boomin",
        tags: ["trap", "dark", "808"],
        text: "Create an original expanded song sketch using Metro Boomin only as a loose reference for dark trap mood, spacious drums, deep 808 bass, eerie melodic loops, and dramatic section changes. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Timbaland",
        tags: ["rhythm", "pop", "percussion"],
        text: "Create an original expanded song sketch using Timbaland only as a loose reference for unusual percussion pockets, vocal-friendly rhythm, syncopated bass, and playful hook movement. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "The Neptunes",
        tags: ["minimal", "funk", "pop"],
        text: "Create an original expanded song sketch using The Neptunes only as a loose reference for minimal drum programming, funky bass, sparse hooks, clean chord stabs, and lots of negative space. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Daft Punk",
        tags: ["house", "funk", "disco"],
        text: "Create an original expanded song sketch using Daft Punk only as a loose reference for funky house rhythm, disco-inspired bass, filtered chord movement, robotic precision, and strong hook repetition. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Calvin Harris",
        tags: ["dance pop", "club", "hook"],
        text: "Create an original expanded song sketch using Calvin Harris only as a loose reference for clean dance-pop structure, bright chord hooks, radio-friendly drops, punchy club drums, and polished arrangement. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Avicii",
        tags: ["progressive", "folk", "anthem"],
        text: "Create an original expanded song sketch using Avicii only as a loose reference for uplifting progressive-house arrangement, folk-like melodic shapes, bright chords, and anthem-style build/drop energy. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Nia Archives",
        tags: ["jungle", "vocals", "breaks"],
        text: "Create an original expanded song sketch using Nia Archives only as a loose reference for modern jungle energy, soulful hook space, fast break-inspired drums, warm bass, and intimate atmosphere. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Chase & Status",
        tags: ["drum n bass", "festival", "bass"],
        text: "Create an original expanded song sketch using Chase & Status only as a loose reference for festival drum n bass energy, heavy bass, sharp drums, vocal-hook sections, and high-impact drops. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Burial x Four Tet",
        tags: ["uk garage", "ambient", "textural"],
        text: "Create an original expanded song sketch using a broad Burial and Four Tet reference only for shuffled UK rhythm, organic texture, warm pads, distant ambience, and evolving club atmosphere. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Disclosure x Kaytranada",
        tags: ["house", "funk", "groove"],
        text: "Create an original expanded song sketch using a broad Disclosure and Kaytranada reference only for tight house swing, funky bass, warm chord stabs, crisp drums, and danceable pocket. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
      {
        label: "Skrillex x Fred again..",
        tags: ["bass", "emotional", "club"],
        text: "Create an original expanded song sketch using a broad Skrillex and Fred again.. reference only for emotional vocal-chop energy, bold bass contrast, intimate build sections, and explosive club moments. Do not copy melodies, samples, lyrics, or signature sounds.",
      },
    ],
  },
  {
    id: "full-track",
    name: "Full Track Ideas",
    meta: "Complete starting points",
    title: "Start with a finished direction",
    prompts: [
      {
        label: "Dark Trap Starter",
        tags: ["trap", "dark", "140 bpm", "full track"],
        text: "Create a dark 140 BPM trap track idea in a minor key with heavy drums, deep 808 bass, eerie melodies, sparse arrangement, and aggressive transitions.",
      },
      {
        label: "Melodic House",
        tags: ["house", "melodic", "124 bpm", "full track"],
        text: "Create a 124 BPM melodic house track with warm chords, emotional lead melody, rolling bassline, clean drums, atmospheric breakdown, and euphoric drop.",
      },
      {
        label: "Hyperpop Blast",
        tags: ["hyperpop", "150 bpm", "full track"],
        text: "Create a 150 BPM hyperpop track with bright synths, distorted drums, playful vocal chops, fast transitions, glitch effects, and a chaotic but catchy structure.",
      },
      {
        label: "Ambient Film Cue",
        tags: ["ambient", "cinematic", "film", "full track"],
        text: "Create a cinematic ambient track idea with evolving pads, soft piano, distant textures, subtle pulses, and a slow emotional arc.",
      },
      {
        label: "Radio Pop Demo",
        tags: ["pop", "radio", "100 bpm", "full track"],
        text: "Create a 100 BPM radio pop demo with verse, pre-chorus, chorus, bridge, catchy lead hook, simple chords, clean drums, and polished production direction.",
      },
      {
        label: "Lo-Fi Beat",
        tags: ["lo-fi", "82 bpm", "beat", "full track"],
        text: "Create an 82 BPM lo-fi beat with dusty drums, warm keys, mellow bass, vinyl texture, relaxed swing, and a simple nostalgic melody.",
      },
      {
        label: "Techno Tool",
        tags: ["techno", "132 bpm", "club", "full track"],
        text: "Create a 132 BPM techno club track with driving kick, rolling bass, hypnotic synth loop, gradual automation, tension-building effects, and DJ-friendly structure.",
      },
    ],
  },
];

const finisherPromptLibrary = [
  {
    id: "mutators",
    name: "Mutators",
    meta: "Create safe variations",
    title: "Mutate without destroying",
    prompts: [
      {
        label: "Mutate Clones",
        tags: ["mutation", "variation", "sibling"],
        text: "Duplicate the current track, mute the original to keep it safe, and generate a variation of its MIDI clip using the Mutation of Clones strategy.",
      },
      {
        label: "Humanize Groove",
        tags: ["humanize", "groove", "velocity", "timing"],
        text: "Duplicate the current track, mute the original, and apply humanization to the new clip's MIDI notes by gently randomizing velocities and timing.",
      },
      {
        label: "Add Ghost Notes",
        tags: ["ghost notes", "drums", "syncopation"],
        text: "Duplicate the current drum track, mute the original, and add rhythmic ghost notes to fill out the pocket.",
      },
    ],
  },
  {
    id: "arrangement-finisher",
    name: "Structure",
    meta: "Carving arrangements",
    title: "Subtractive Arrangement",
    prompts: [
      {
        label: "Maximal Density Intro",
        tags: ["intro", "subtract", "arrangement"],
        text: "Assuming the loop is at maximal density, duplicate the tracks, mute the originals, and carve out an Intro section by removing the drums, bass, and lead.",
      },
      {
        label: "Carve Breakdown",
        tags: ["breakdown", "subtract", "arrangement"],
        text: "Duplicate the maximal density section, mute originals, and carve a breakdown by muting high-energy drums and bass while keeping pads and melodic elements.",
      },
    ],
  },
  {
    id: "full-arrangers",
    name: "Song Sketch",
    meta: "Full song templates",
    title: "Session Loop Arrangers",
    prompts: [
      {
        label: "House Arrangement",
        tags: ["house", "groove", "drop", "dj tool"],
        text: "Finish my existing Session View loops into a progressive house arrangement with natural drop building.",
      },
      {
        label: "Techno DJ Tool",
        tags: ["techno", "hypnotic", "gradual", "drop"],
        text: "Finish my existing Session View loops into a techno DJ tool structure with hypnotic tension building.",
      },
      {
        label: "Trap Beat Structure",
        tags: ["trap", "verse", "hook", "808"],
        text: "Finish my existing Session View loops into a trap beat with an intro, verse, pre-hook, hook, and outro.",
      },
      {
        label: "Pop Song Arc",
        tags: ["pop", "chorus", "bridge", "verse"],
        text: "Finish my existing Session View loops into a pop song structure with a verse-pre-chorus-chorus arc.",
      },
      {
        label: "Drum & Bass Rollout",
        tags: ["dnb", "drum n bass", "rollout", "buildup"],
        text: "Finish my existing Session View loops into a fast drum n bass arrangement with tension builds and massive drops.",
      },
      {
        label: "Ambient Soundscape",
        tags: ["ambient", "cinematic", "texture", "slow bloom"],
        text: "Finish my existing Session View loops into a cinematic ambient arrangement with slow-building textures.",
      },
    ],
  },
];

let activeLibrary = promptLibrary;

const songMakerMeta = {
  meta: "Inspiration builder",
  title: "Shape a track from ideas",
};

const expandedGenrePrompts = {
  drums: [
    ["Dance Mainstage Drums", ["dance", "mainstage", "drums"], "Create Dance and Mainstage drums with a big four-on-the-floor kick, wide clap, bright offbeat hats, energetic rides, percussion lifts, snare rolls, and separate Bd, Snare / Clap, Hh / Sh / Rd, Hh / Sh / Rd +, and Percussion tracks."],
    ["Downtempo Drums", ["downtempo", "drums", "chill"], "Create Downtempo drums with a relaxed pocket, soft kick, brushed hats, loose claps, organic percussion, and subtle ghost movement across separate Bd, Snare / Clap, Hh / Sh / Rd, and Percussion tracks."],
    ["Drum n Bass Drums", ["drum n bass", "breaks", "drums"], "Create Drum n Bass drums with fast break-inspired hats, punchy kick movement, sharp snare / clap, rolling ghost hits, ride energy, and separate Bd, Snare / Clap, Hh / Sh / Rd, Hh / Sh / Rd +, and Percussion tracks."],
    ["Hip Hop Drums", ["hip hop", "drums", "swing"], "Create Hip Hop drums with a head-nod kick pattern, tight snare, swung hats, subtle percussion, fill variations, and separate Bd, Snare / Clap, Hh / Sh / Rd, and Percussion tracks."],
    ["House Drums", ["house", "club", "drums"], "Create House drums with steady club kick, offbeat open hats, layered clap, shuffled percussion, ride lift, 8-bar fills, and separate Bd, Snare / Clap, Hh / Sh / Rd, Hh / Sh / Rd +, and Percussion tracks."],
    ["90s Jungle Drums", ["jungle", "breakbeat", "drums"], "Create 90s Jungle drums with chopped break-style top loops, hard snare accents, sub-friendly kick placement, ride splashes, percussion edits, and separate drum-part tracks."],
    ["Modern Pop Drums", ["pop", "drums", "chorus"], "Create Modern Pop drums with restrained verse groove, bigger chorus drums, crisp clap, tight hats, small fills into each chorus, and separated kick, snare / clap, hats, and percussion tracks."],
    ["Reggae Dance Hall Drums", ["reggae", "dance hall", "drums"], "Create Reggae and Dance Hall drums with laid-back kick, offbeat hat feel, rim/clap accents, hand percussion, loose fills, and separated drum-part tracks."],
    ["Reggaeton Drums", ["reggaeton", "dembow", "drums"], "Create Reggaeton drums with a dembow-inspired kick and snare / clap pattern, syncopated hats, club percussion, small transition fills, and separated drum-part tracks."],
    ["Rock Country Drums", ["rock", "country", "drums"], "Create Rock and Country drums with a verse groove, chorus lift, backbeat snare, steady hats, simple fills, and separated kick, snare / clap, hats, and percussion tracks."],
    ["Techno Drums", ["techno", "drums", "club"], "Create Techno drums with a driving kick, hypnotic hats, tight clap, rolling percussion, ride pressure, long-build variations, and separated drum-part tracks."],
    ["Trance Drums", ["trance", "drums", "uplifting"], "Create Trance drums with steady kick, open-hat lift, clap/snare builds, rolling percussion, ride energy, pre-drop snare rolls, and separated drum-part tracks."],
    ["Trap Drums Expanded", ["trap", "808", "drums"], "Create Trap drums with hard kick accents, crisp snare / clap, rolling hats, triplet hat fills, sparse percussion, and separated Bd, Snare / Clap, Hh / Sh / Rd, and Percussion tracks."],
    ["Ambient Cinematic Perc", ["ambient", "cinematic", "percussion"], "Create Ambient Cinematic percussion with sparse low pulses, soft ticks, distant cymbal swells, subtle hand percussion, and lots of space around the pad and ambience tracks."],
    ["Hyperpop Drums", ["hyperpop", "glitch", "drums"], "Create Hyperpop drums with punchy kicks, bright claps, chopped hats, glitch edits, sudden fills, stutter moments, and separated drum-part tracks."],
    ["UK Garage Drums", ["uk garage", "shuffle", "drums"], "Create UK Garage drums with shuffled kick placement, skippy hats, tight snare / clap, syncopated percussion, and separated drum-part tracks."],
    ["Afrobeats Drums", ["afrobeats", "rhythm", "syncopated"], "Create Afrobeats drums with syncopated 'clave' patterns, separate kick and snare / clap tracks, 16th note hats, organic percussion layers, and a danceable rhythm."],
    ["Amapiano Drums", ["amapiano", "shakers", "drums"], "Create Amapiano drums with a steady four-on-the-floor kick, late snare stabs, constant 16th note shakers, and percussive rim fills."],
  ],
  bass: [
    ["Dance Mainstage Bass", ["dance", "mainstage", "bass"], "Create a Dance and Mainstage bass part with sidechain-friendly rhythm, octave movement, pre-drop tension notes, and a strong drop groove that locks with Bd."],
    ["Downtempo Bass", ["downtempo", "warm", "bass"], "Create a Downtempo bassline with warm long notes, gentle syncopation, tasteful passing tones, and space for pad, chords, and ambience."],
    ["Drum n Bass Bass", ["drum n bass", "rolling", "bass"], "Create a Drum n Bass bassline with rolling low movement, call-and-response mids, sub pressure, and variation between drop and breakdown."],
    ["Hip Hop Bass", ["hip hop", "sub", "bass"], "Create a Hip Hop bassline that follows the chord roots, leaves space for vocals, adds tasteful slides, and supports the kick pattern."],
    ["House Bass", ["house", "club", "bass"], "Create a House bassline with bouncy offbeat movement, warm low end, simple hook identity, and tight lock with the four-on-the-floor kick."],
    ["90s Jungle Sub", ["jungle", "sub", "bass"], "Create a 90s Jungle sub bassline with long low notes, quick answering hits, dubby movement, and tension before the drop."],
    ["Modern Pop Bass", ["pop", "clean", "bass"], "Create a Modern Pop bassline with clean root movement, chorus lift, verse restraint, and small rhythmic hooks that support the vocal-style hook."],
    ["Reggae Dance Hall Bass", ["reggae", "dance hall", "bass"], "Create a Reggae and Dance Hall bassline with warm low-end weight, offbeat pocket, melodic movement, and relaxed groove."],
    ["Reggaeton Bass", ["reggaeton", "latin", "bass"], "Create a Reggaeton bassline that follows the dembow pulse, uses simple catchy movement, and supports club-friendly low end."],
    ["Rock Country Bass", ["rock", "country", "bass"], "Create a Rock and Country bassline with root-fifth motion, chorus lift, walking touches, and a steady song-supporting groove."],
    ["Techno Bass", ["techno", "hypnotic", "bass"], "Create a Techno bassline with a hypnotic repeating motif, subtle filter-style movement, and evolving variation every 8 bars."],
    ["Trance Rolling Bass", ["trance", "rolling", "bass"], "Create a Trance rolling bassline with 16th-note drive, chord-following root movement, octave lift in the build, and drop energy."],
    ["Trap 808 Bass", ["trap", "808", "bass"], "Create a Trap 808 bassline with deep sustained notes, slides, octave drops, sparse rhythm, and strong kick interaction."],
    ["Ambient Bass Pulse", ["ambient", "cinematic", "bass"], "Create an Ambient Cinematic low pulse with long sustained bass notes, slow tension movement, and subtle rhythmic entrances."],
    ["Hyperpop Bass", ["hyperpop", "distorted", "bass"], "Create a Hyperpop bassline with distorted octave jumps, playful rhythmic cuts, fast transitions, and energetic hook support."],
    ["UK Garage Bass", ["uk garage", "shuffle", "bass"], "Create a UK Garage bassline with syncopated low movement, swung rhythm, short stabs, and a catchy club bounce."],
    ["Afrobeats Bass", ["afrobeats", "melodic", "bass"], "Create an Afrobeats bassline with melodic movement that follows the syncopated kick, uses warm tones, and supports the groove."],
    ["Amapiano Log Drum", ["amapiano", "log drum", "bass"], "Create an Amapiano 'log drum' bassline with 16th note rolls, deep sub slides, and a distinctive percussive bounce."],
  ],
  melody: [
    ["Dance Mainstage Hook", ["dance", "mainstage", "hook"], "Create a Dance and Mainstage chord, riff, and hook idea with wide festival chords, a bright singable lead, and a simple riff that can build into a drop."],
    ["Downtempo Theme", ["downtempo", "melody", "chill"], "Create a Downtempo melodic idea with warm chords, hazy pad, sparse hook motif, gentle counter-riff, and a reflective emotional tone."],
    ["Drum n Bass Lead", ["drum n bass", "lead", "riff"], "Create a Drum n Bass melodic idea with atmospheric pad, minor chords, urgent riff, short hook motif, and tension-building counter-melody."],
    ["Hip Hop Sample Feel", ["hip hop", "chords", "hook"], "Create a Hip Hop melodic idea with dusty chords, a short loopable riff, simple hook motif, and space for a vocal."],
    ["House Piano Hook", ["house", "piano", "hook"], "Create a House melodic idea with warm chord stabs, a catchy piano or synth hook, simple pad support, and a riff that works over a club groove."],
    ["90s Jungle Rave Riff", ["jungle", "rave", "riff"], "Create a 90s Jungle melodic idea with airy pad, rave-style riff, short hook stab, and atmospheric ambience."],
    ["Modern Pop Chorus", ["pop", "chorus", "melody"], "Create a Modern Pop melodic idea with emotional chords, verse restraint, a clear chorus hook, supporting riff, and smooth counter-melody."],
    ["Reggae Dance Hall Skank", ["reggae", "dance hall", "chords"], "Create a Reggae and Dance Hall melodic idea with offbeat chord skanks, warm pad, simple hook phrase, and relaxed riff movement."],
    ["Reggaeton Hook", ["reggaeton", "hook", "latin"], "Create a Reggaeton melodic idea with catchy minor-key hook, rhythmic chord stabs, warm pad, and a simple riff that leaves space for vocals."],
    ["Rock Country Topline", ["rock", "country", "melody"], "Create a Rock and Country melodic idea with chord bed, memorable chorus hook, guitar-like riff, and supportive pad texture."],
    ["Techno Motif", ["techno", "motif", "riff"], "Create a Techno melodic idea with a hypnotic one-bar riff, dark pad, minimal hook motif, and subtle chord tension."],
    ["Trance Lead", ["trance", "lead", "uplifting"], "Create a Trance melodic idea with uplifting chords, emotional pad, rolling arpeggio riff, and a big lead hook for the drop."],
    ["Trap Dark Melody", ["trap", "dark", "melody"], "Create a Trap melodic idea with eerie chords, sparse bell-like hook, dark pad, and a simple riff that leaves space for 808s."],
    ["Ambient Theme", ["ambient", "cinematic", "theme"], "Create an Ambient Cinematic melodic idea with evolving pad chords, a slow hook motif, soft counter-melody, and wide ambience."],
    ["Hyperpop Hook", ["hyperpop", "bright", "hook"], "Create a Hyperpop melodic idea with bright chords, playful hook, glitchy riff, and a high-energy counter-melody."],
    ["UK Garage Chords", ["uk garage", "chords", "hook"], "Create a UK Garage melodic idea with swung chord stabs, vocal-like hook motif, syncopated riff, and soft pad support."],
    ["Afrobeats Hook", ["afrobeats", "pentatonic", "hook"], "Create an Afrobeats melodic idea with rhythmic chord stabs, a catchy pentatonic hook, and supportive pad textures."],
    ["Amapiano Theme", ["amapiano", "percussive", "theme"], "Create an Amapiano melodic idea with deep house pads, a percussive synth hook, and minimal atmospheric riff."],
  ],
  mixing: [
    ["Dance Mainstage Mix", ["dance", "mainstage", "mix"], "Create a Dance and Mainstage mix plan: big centered kick and bass, wide chords and hook, bright hats, controlled clap, clean low end, and drop-focused gain staging."],
    ["Downtempo Mix", ["downtempo", "warm", "mix"], "Create a Downtempo mix plan: warm low end, soft transients, wide pad and ambience, tucked percussion, gentle compression, and relaxed headroom."],
    ["Drum n Bass Mix", ["drum n bass", "mix", "bass"], "Create a Drum n Bass mix plan: tight kick/snare, controlled sub, bright but smooth hats, separated pad/riff/hook space, and loud clean drum energy."],
    ["Hip Hop Mix", ["hip hop", "mix", "vocal"], "Create a Hip Hop mix plan: kick and bass relationship, crisp snare, controlled hats, dusty chords, vocal space, and simple bus balance."],
    ["House Mix", ["house", "club", "mix"], "Create a House mix plan: punchy kick, warm bass, offbeat hats, clap presence, wide chords, percussion depth, and DJ-friendly headroom."],
    ["Jungle Mix", ["jungle", "breakbeat", "mix"], "Create a 90s Jungle mix plan: break clarity, sub weight, controlled snare bite, airy pads, rave riff focus, and raw but balanced energy."],
    ["Modern Pop Mix", ["pop", "mix", "polished"], "Create a Modern Pop mix plan: vocal-style hook space, clean drums, controlled bass, polished chords and pads, chorus width, and smooth master headroom."],
    ["Reggae Dance Hall Mix", ["reggae", "dance hall", "mix"], "Create a Reggae and Dance Hall mix plan: warm bass forward, relaxed drums, offbeat chord clarity, percussion space, and vocal-friendly mids."],
    ["Reggaeton Mix", ["reggaeton", "mix", "club"], "Create a Reggaeton mix plan: dembow kick/clap punch, bass control, bright percussion, hook focus, and clean club loudness."],
    ["Rock Country Mix", ["rock", "country", "mix"], "Create a Rock and Country mix plan: clear chord bed, steady bass, natural snare, controlled hats, hook presence, and song-focused balance."],
    ["Techno Mix", ["techno", "mix", "club"], "Create a Techno mix plan: dominant kick, hypnotic bass control, crisp hats, restrained riff, dark pad width, and club translation."],
    ["Trance Mix", ["trance", "mix", "wide"], "Create a Trance mix plan: rolling bass clarity, wide pad/chords, bright lead hook, energetic drums, controlled build noise, and drop headroom."],
    ["Trap Mix", ["trap", "808", "mix"], "Create a Trap mix plan: 808 and kick balance, crisp snare, bright hats, dark melody space, controlled distortion, and vocal room."],
    ["Ambient Mix", ["ambient", "cinematic", "mix"], "Create an Ambient Cinematic mix plan: wide pads, soft low pulse, deep ambience, gentle percussion, long tails, and plenty of dynamic range."],
    ["Hyperpop Mix", ["hyperpop", "mix", "bright"], "Create a Hyperpop mix plan: bright hook control, distorted bass management, punchy drums, glitch effects clarity, and loud but not harsh energy."],
    ["UK Garage Mix", ["uk garage", "mix", "shuffle"], "Create a UK Garage mix plan: shuffled drum clarity, bouncy bass, chord stab width, vocal-hook space, and tight club low end."],
    ["Afrobeats Mix", ["afrobeats", "mix", "percussion"], "Create an Afrobeats mix plan: punchy syncopated kick, warm melodic bass, crisp percussion, vocal-friendly hook space, and balanced mid-range."],
    ["Amapiano Mix", ["amapiano", "mix", "club"], "Create an Amapiano mix plan: dominant log-drum bass, steady kick, shaker clarity, wide pads, and percussive hook focus."],
  ],
  effects: [
    ["Dance Mainstage FX", ["dance", "mainstage", "fx"], "Create Dance and Mainstage effects with risers, snare builds, white-noise sweeps, pre-drop silence, impact hits, delay throws, and final-drop lift automation."],
    ["Downtempo FX", ["downtempo", "fx", "space"], "Create Downtempo effects with tape-style delays, soft reverse swells, filtered transitions, warm reverb throws, and subtle ambience movement."],
    ["Drum n Bass FX", ["drum n bass", "fx", "transition"], "Create Drum n Bass effects with bass-drop impacts, break edits, fast risers, filtered drum fills, atmospheric reverses, and tension before the second drop."],
    ["Hip Hop FX", ["hip hop", "fx", "fills"], "Create Hip Hop effects with vinyl stops, short delay throws, reverse cymbals, subtle filter drops, hook impacts, and tasteful transition fills."],
    ["House FX", ["house", "fx", "club"], "Create House effects with filter sweeps, risers, clap fills, reverb throws, crash impacts, and DJ-friendly build automation."],
    ["Jungle FX", ["jungle", "fx", "breaks"], "Create 90s Jungle effects with dub delays, breakbeat chops, rave stabs, reverse cymbals, filtered drops, and raw transition hits."],
    ["Modern Pop FX", ["pop", "fx", "transition"], "Create Modern Pop effects with vocal-style delay throws, chorus lifts, reverse transitions, soft impacts, risers, and bridge-to-final-chorus automation."],
    ["Reggae Dance Hall FX", ["reggae", "dance hall", "fx"], "Create Reggae and Dance Hall effects with dub delays, spring-style reverb throws, percussion drops, filtered chord moments, and relaxed transitions."],
    ["Reggaeton FX", ["reggaeton", "fx", "club"], "Create Reggaeton effects with dembow fills, vocal-style throws, risers, club impacts, filter drops, and pre-hook transitions."],
    ["Rock Country FX", ["rock", "country", "fx"], "Create Rock and Country effects with drum fills, subtle swells, chorus lifts, short slap delays, bridge transition impacts, and final chorus width."],
    ["Techno FX", ["techno", "fx", "automation"], "Create Techno effects with long filter automation, noise risers, impact hits, tension loops, delay feedback, and stripped-break transitions."],
    ["Trance FX", ["trance", "fx", "build"], "Create Trance effects with long risers, snare rolls, uplifters, downlifters, reverb blooms, pre-drop silence, and huge drop impacts."],
    ["Trap FX", ["trap", "fx", "dark"], "Create Trap effects with 808 drops, reverse bells, risers, snare rolls, dark impacts, chopped transitions, and hook-entry moments."],
    ["Ambient FX", ["ambient", "cinematic", "fx"], "Create Ambient Cinematic effects with long swells, reverse reverb, evolving noise beds, distant impacts, shimmer-like tails, and slow automation."],
    ["Hyperpop FX", ["hyperpop", "fx", "glitch"], "Create Hyperpop effects with glitch stutters, pitch throws, chopped transitions, sudden mutes, digital risers, and playful impact edits."],
    ["UK Garage FX", ["uk garage", "fx", "club"], "Create UK Garage effects with filtered chord throws, shuffled drum fills, short delays, reverse hits, bass mutes, and hook-entry impacts."],
    ["Afrobeats FX", ["afrobeats", "fx", "delays"], "Create Afrobeats effects with subtle delay throws, percussion rolls, filtered transitions, and rhythmic impacts."],
    ["Amapiano FX", ["amapiano", "fx", "rolls"], "Create Amapiano effects with log-drum rolls, shaker builds, filtered reverb throws, and deep club impacts."],
  ],
  instruments: [
    ["Dance Mainstage Setup", ["dance", "mainstage", "instruments"], "Create a Dance and Mainstage genre-aware sound setup with Chords, Pad, Riff, Hook, Bass, Bd, Snare / Clap, Hh / Sh / Rd, Hh / Sh / Rd +, Percussion, and Ambience tracks, then add MIDI clips and start playback."],
    ["Downtempo Setup", ["downtempo", "instruments", "warm"], "Create a Downtempo genre-aware sound setup with warm Chords, soft Pad, subtle Riff, mellow Hook, rounded Bass, gentle drums, Percussion, and Ambience, then add MIDI clips and start playback."],
    ["Drum n Bass Setup", ["drum n bass", "instruments", "fast"], "Create a Drum n Bass genre-aware sound setup with atmospheric Pad, urgent Riff, Hook, rolling Bass, separated Bd, Snare / Clap, fast Hh / Sh / Rd, Percussion, and Ambience, then start playback."],
    ["Hip Hop Setup", ["hip hop", "instruments", "beat"], "Create a Hip Hop genre-aware sound setup with dusty Chords, Pad, Riff, Hook, sub Bass, separated kick, snare, hats, percussion, and ambience, then add clips and start playback."],
    ["House Setup", ["house", "instruments", "club"], "Create a House genre-aware sound setup with chord stabs, Pad, Riff, Hook, bouncy Bass, club Bd, Clap, Hats, Percussion, and Ambience, then add clips and start playback."],
    ["Jungle Setup", ["jungle", "instruments", "breakbeat"], "Create a 90s Jungle genre-aware sound setup with airy Pad, rave Riff, Hook, sub Bass, break-style separated drum tracks, Percussion, and Ambience, then start playback."],
    ["Modern Pop Setup", ["pop", "instruments", "song"], "Create a Modern Pop genre-aware sound setup with clean Chords, Pad, Riff, Hook, Bass, separated drums, Percussion, and Ambience, then add verse/chorus clips and start playback."],
    ["Reggaeton Setup", ["reggaeton", "instruments", "dembow"], "Create a Reggaeton genre-aware sound setup with Chords, Pad, Riff, Hook, Bass, dembow-separated drum tracks, Percussion, and Ambience, then add clips and start playback."],
    ["Techno Setup", ["techno", "instruments", "club"], "Create a Techno genre-aware sound setup with dark Pad, hypnotic Riff, minimal Hook, Bass, driving Bd, Hats, Clap, Percussion, and Ambience, then add clips and start playback."],
    ["Trance Setup", ["trance", "instruments", "uplifting"], "Create a Trance genre-aware sound setup with uplifting Chords, wide Pad, arpeggio Riff, lead Hook, rolling Bass, separated drums, Percussion, and Ambience, then start playback."],
    ["Trap Setup", ["trap", "instruments", "808"], "Create a Trap genre-aware sound setup with dark Chords, Pad, Riff, Hook, 808 Bass, separated Bd, Snare / Clap, Hh / Sh / Rd, Percussion, and Ambience, then start playback."],
    ["UK Garage Setup", ["uk garage", "instruments", "shuffle"], "Create a UK Garage genre-aware sound setup with shuffled chords, Pad, Riff, Hook, bouncy Bass, separated drum tracks, Percussion, and Ambience, then add clips and start playback."],
    ["Afrobeats Setup", ["afrobeats", "instruments", "rhythmic"], "Create an Afrobeats genre-aware sound setup with rhythmic Chords, Pad, Riff, Hook, Bass, syncopated kick, snare / clap, hats, and organic percussion."],
    ["Amapiano Setup", ["amapiano", "instruments", "club"], "Create an Amapiano genre-aware sound setup with deep Pads, percussive Riff, synth Hook, log-drum Bass, four-on-the-floor kick, late snare, and shaker tracks."],
  ],
  "full-track": [
    ["Dance Mainstage Track", ["dance", "mainstage", "full track"], "Create a complete Dance and Mainstage song sketch with genre-aware Ableton instruments, 128 BPM, festival-sized chords, bright riff, memorable hook, rolling bass, separated drums, percussion, ambience, intro-build-drop-break-final-drop arrangement, and start playback."],
    ["Downtempo Track", ["downtempo", "full track", "chill"], "Create a complete Downtempo song sketch with genre-aware Ableton instruments, 92 BPM, warm chords, hazy pad, mellow hook, subtle riff, deep bass, relaxed drums, percussion, ambience, slow emotional arrangement, and start playback."],
    ["Drum n Bass Track", ["drum n bass", "full track", "172 bpm"], "Create a complete Drum n Bass song sketch with genre-aware Ableton instruments, 172 BPM, atmospheric pad, urgent riff, hook motif, rolling bass, separated fast drums, percussion, ambience, intro-drop-break-second-drop arrangement, and start playback."],
    ["Hip Hop Track", ["hip hop", "full track", "beat"], "Create a complete Hip Hop song sketch with genre-aware Ableton instruments, 90 BPM, dusty chords, pad, short riff, hook motif, sub bass, separated drums, percussion, ambience, intro-verse-hook-verse-final-hook arrangement, and start playback."],
    ["House Track", ["house", "full track", "club"], "Create a complete House song sketch with genre-aware Ableton instruments, 125 BPM, chord stabs, warm pad, simple hook, bouncy bass, separated club drums, percussion, ambience, DJ intro, drops, breakdown, and outro, then start playback."],
    ["90s Jungle Track", ["jungle", "full track", "breakbeat"], "Create a complete 90s Jungle song sketch with genre-aware Ableton instruments, 170 BPM, airy pad, rave riff, hook stabs, sub bass, chopped-break drum feel across separated drum tracks, percussion, ambience, raw intro-drop-break-second-drop arrangement, and start playback."],
    ["Modern Pop Track", ["pop", "full track", "radio"], "Create a complete Modern Pop song sketch with genre-aware Ableton instruments, 104 BPM, emotional chords, clean pad, supporting riff, strong chorus hook, bass, separated drums, percussion, ambience, verse-pre-chorus-chorus-bridge-final-chorus arrangement, and start playback."],
    ["Reggae Dance Hall Track", ["reggae", "dance hall", "full track"], "Create a complete Reggae and Dance Hall song sketch with genre-aware Ableton instruments, 96 BPM, offbeat chords, warm pad, relaxed hook, melodic bass, loose separated drums, percussion, ambience, verse-hook-percussion-break arrangement, and start playback."],
    ["Reggaeton Track", ["reggaeton", "full track", "dembow"], "Create a complete Reggaeton song sketch with genre-aware Ableton instruments, 96 BPM, catchy minor hook, rhythmic chords, pad, riff, bass, dembow-separated drum tracks, percussion, ambience, intro-verse-pre-hook-hook-break-final-hook arrangement, and start playback."],
    ["Rock Country Track", ["rock", "country", "full track"], "Create a complete Rock and Country song sketch with genre-aware Ableton instruments, 108 BPM, chord bed, pad, riff, chorus hook, bass, separated drums, percussion, ambience, intro-verse-chorus-bridge-final-chorus arrangement, and start playback."],
    ["Techno Track", ["techno", "full track", "club"], "Create a complete Techno song sketch with genre-aware Ableton instruments, 132 BPM, hypnotic riff, dark pad, minimal hook, driving bass, separated drums, percussion, ambience, DJ intro, tension break, final drive, and outro, then start playback."],
    ["Trance Track", ["trance", "full track", "uplifting"], "Create a complete Trance song sketch with genre-aware Ableton instruments, 138 BPM, uplifting chords, wide pad, arpeggio riff, big lead hook, rolling bass, separated drums, percussion, ambience, long build, breakdown, main drop, final lift, and start playback."],
    ["Trap Track", ["trap", "full track", "808"], "Create a complete Trap song sketch with genre-aware Ableton instruments, 140 BPM, dark chords, eerie pad, sparse riff, hook motif, 808 bass, separated drums, percussion, ambience, intro-verse-hook-break-verse-final-hook arrangement, and start playback."],
    ["Ambient Cinematic Track", ["ambient", "cinematic", "full track"], "Create a complete Ambient Cinematic song sketch with genre-aware Ableton instruments, 78 BPM, evolving pad, slow chords, soft hook motif, low bass pulse, sparse percussion, deep ambience, texture-pulse-theme-drift-bloom arrangement, and start playback."],
    ["Hyperpop Track", ["hyperpop", "full track", "glitch"], "Create a complete Hyperpop song sketch with genre-aware Ableton instruments, 150 BPM, bright chords, playful pad, glitch riff, catchy hook, distorted bass, separated punchy drums, percussion, ambience, fast transitions, chaos-to-hook arrangement, and start playback."],
    ["UK Garage Track", ["uk garage", "full track", "shuffle"], "Create a complete UK Garage song sketch with genre-aware Ableton instruments, 132 BPM, shuffled chord stabs, soft pad, syncopated riff, vocal-like hook, bouncy bass, separated drums, percussion, ambience, intro-groove-break-final-hook arrangement, and start playback."],
    ["Afrobeats Track", ["afrobeats", "full track", "rhythmic"], "Create a complete Afrobeats song sketch with genre-aware Ableton instruments, 108 BPM, syncopated 'clave' rhythms, warm chords, catchy pentatonic hook, melodic bass, separated drums, percussion, ambience, and a rhythmic arrangement, then start playback."],
    ["Amapiano Track", ["amapiano", "full track", "club"], "Create a complete Amapiano song sketch with genre-aware Ableton instruments, 113 BPM, log-drum bass rolls, steady kick, deep pads, percussive synth hook, constant shakers, separated drums, and a club-focused arrangement, then start playback."],
  ],
};

expandPromptLibrary(expandedGenrePrompts);

const songFinderGroups = [
  {
    id: "feeling",
    label: "Emotion",
    options: ["lonely but expensive", "warm and hopeful", "dirty and physical", "sad but moving", "euphoric release", "tense and cinematic", "playful chaos", "calm and floating", "confident and minimal", "nostalgic glow", "dark pressure", "romantic afterparty"],
  },
  {
    id: "scene",
    label: "Scene",
    options: ["3am city drive", "warehouse basement", "sunset beach road", "festival mainstage", "bedroom headphones", "rainy train window", "summer rooftop", "empty club after close", "movie trailer moment", "late-night studio", "small smoky room", "internet-pop bedroom"],
  },
  {
    id: "genre",
    label: "World",
    options: ["Dance and Mainstage", "Downtempo", "Drum n Bass", "Hip Hop", "House", "90s Jungle", "Modern Pop", "Reggae and Dance Hall", "Reggaeton", "Rock and Country", "Techno", "Trance", "Trap", "Ambient Cinematic", "Hyperpop", "UK Garage", "Afrobeats", "Amapiano"],
  },
  {
    id: "energy",
    label: "Energy",
    options: ["slow burn", "steady head-nod", "club bounce", "hands-up peak", "rolling and fast", "minimal pressure", "explosive drop", "soft pulse", "anthemic lift", "aggressive switch-up"],
  },
  {
    id: "groove",
    label: "Groove",
    options: ["straight four-on-the-floor", "swung and shuffled", "broken beat", "dembow pulse", "half-time trap", "rolling breakbeat", "laid-back pocket", "driving techno pulse", "syncopated funk", "sparse cinematic pulse"],
  },
  {
    id: "texture",
    label: "Texture",
    options: ["glossy synths", "dusty sample feel", "warm analog pad", "metallic percussion", "wide ambience", "distorted bass", "clean piano chords", "rave stabs", "organic percussion", "digital glitches", "soft tape haze", "bright plucks"],
  },
  {
    id: "hook",
    label: "Hook Feel",
    options: ["simple chantable hook", "vocal-chop feeling", "tiny repeating motif", "big emotional lead", "call-and-response riff", "melancholy topline", "minimal hypnotic phrase", "chaotic catchy hook", "cinematic theme", "club stab hook"],
  },
  {
    id: "bass",
    label: "Bass Role",
    options: ["deep sub foundation", "rolling bass movement", "808 slides", "bouncy offbeat bass", "reese-style pressure", "warm live-style bass", "short plucky bass", "hypnotic one-note drive", "melodic bass answers", "clean pop low end"],
  },
  {
    id: "reference",
    label: "Loose Reference",
    options: ["Fred again.. intimacy", "Four Tet texture", "Skrillex impact", "Flume wonk", "Disclosure groove", "Kaytranada pocket", "Burial atmosphere", "Bicep emotion", "Bonobo warmth", "Jamie xx restraint", "Overmono club breaks", "Metro Boomin darkness"],
  },
];

const finderDefaults = {
  feeling: "lonely but expensive",
  scene: "3am city drive",
  genre: "House",
  energy: "club bounce",
  groove: "swung and shuffled",
  texture: "warm analog pad",
  hook: "vocal-chop feeling",
  bass: "bouncy offbeat bass",
  reference: "Disclosure groove",
};

let finderSelections = { ...finderDefaults };
let finderCustomValues = Object.fromEntries(songFinderGroups.map((group) => [group.id, ""]));

const form = document.querySelector("#composer");
const prompt = document.querySelector("#prompt");
const messages = document.querySelector("#messages");
const statusBadge = document.querySelector("#status");
const stateList = document.querySelector("#liveState");
const eventsList = document.querySelector("#events");
const tabs = document.querySelector("#tabs");
const promptGrid = document.querySelector("#promptGrid");
const search = document.querySelector("#search");
const genre = document.querySelector("#genre");
const bpm = document.querySelector("#bpm");
const key = document.querySelector("#key");
const mood = document.querySelector("#mood");
const reference = document.querySelector("#reference");
const activeMeta = document.querySelector("#activeMeta");
const activeTitle = document.querySelector("#activeTitle");
const resultCount = document.querySelector("#resultCount");
const clearPrompt = document.querySelector("#clearPrompt");
const copyPrompt = document.querySelector("#copyPrompt");
const makeSongPrompt = document.querySelector("#makeSongPrompt");

let activeTab = activeLibrary[0].id;
let currentMode = "inspiration"; // inspiration, songmaker, or finisher
let lastSentPrompt = "";

// --- VST scanning state ---
let scannedVstPlugins = [];
let vstRoleSelections = JSON.parse(localStorage.getItem("vstRoleSelections") || "{}");
let vstFavorites = JSON.parse(localStorage.getItem("vstFavorites") || "[]");
const vstSelects = document.querySelectorAll("#vstRoles select[data-role]");
const vstStatus = document.querySelector("#vstStatus");

function populateVstDropdowns(plugins) {
  vstSelects.forEach((sel) => {
    const role = sel.dataset.role;
    const savedValue = vstRoleSelections[role] || "";
    // Keep first "Stock Ableton" option, remove any previously added
    while (sel.options.length > 1) sel.remove(1);
    
    let baseFiltered = [];
    if (role === "drums") {
      baseFiltered = plugins.filter((name) => name.startsWith("BM-") || name.includes("Beatmaker"));
      // Clean up extensions
      baseFiltered = baseFiltered.map(name => name.replace(/\.(vst3|vst|component)$/i, ""));
      if (baseFiltered.length === 0) {
        baseFiltered = ["BM-HUSTLE", "BM-EDEN", "BM-DOPE", "BM-VICE"];
      }
    } else {
      // Melodic roles filter for Serum
      baseFiltered = plugins.filter((name) => name === "Serum2" || name === "Serum");
      if (baseFiltered.length === 0) {
        baseFiltered = ["Serum2"];
      }
    }

    // Identify favorites matching this role category (Drums vs Melodic)
    let roleFavorites = vstFavorites.filter(name => {
      const isDrum = name.startsWith("BM-") || name.toLowerCase().includes("beatmaker") || name.toLowerCase().includes("drum");
      return (role === "drums") ? isDrum : !isDrum;
    });

    // Combine them, placing favorites at the top (uniquely)
    let combined = [...roleFavorites.map(f => ({ name: f, isFav: true }))];
    baseFiltered.forEach(name => {
      if (!roleFavorites.includes(name)) {
        combined.push({ name: name, isFav: false });
      }
    });

    combined.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.name;
      opt.textContent = item.isFav ? `⭐ ${item.name}` : item.name;
      sel.appendChild(opt);
    });
    sel.value = savedValue || "";
  });
}

function saveVstSelections() {
  vstRoleSelections = {};
  vstSelects.forEach((sel) => {
    if (sel.value) vstRoleSelections[sel.dataset.role] = sel.value;
  });
  localStorage.setItem("vstRoleSelections", JSON.stringify(vstRoleSelections));
}

function buildVstMap() {
  const map = {};
  vstSelects.forEach((sel) => {
    if (sel.value) map[sel.dataset.role] = sel.value;
  });
  return map;
}

vstSelects.forEach((sel) => sel.addEventListener("change", saveVstSelections));

// --- VST Explorer & Favorites Event Handlers ---
const toggleVstExplorerBtn = document.getElementById("toggleVstExplorerBtn");
const vstExplorerBody = document.getElementById("vstExplorerBody");
const vstSearchInput = document.getElementById("vstSearchInput");
const vstPluginList = document.getElementById("vstPluginList");
const vstContextMenu = document.getElementById("vstContextMenu");
const contextFavAction = document.getElementById("contextFavAction");
let activeContextPlugin = "";

toggleVstExplorerBtn.addEventListener("click", () => {
  vstExplorerBody.classList.toggle("hidden");
  const isHidden = vstExplorerBody.classList.contains("hidden");
  toggleVstExplorerBtn.textContent = isHidden ? "Show Scanned Plugins" : "Hide Scanned Plugins";
  if (!isHidden) {
    renderVstExplorerList();
  }
});

vstSearchInput.addEventListener("input", () => {
  renderVstExplorerList(vstSearchInput.value);
});

function renderVstExplorerList(filterText = "") {
  vstPluginList.innerHTML = "";
  
  // Use scanned plugins, fallback to standard popular list if folder is empty or not scanned
  let list = scannedVstPlugins.length > 0 ? scannedVstPlugins : [
    "Serum2", "Serum", "BM-HUSTLE", "BM-EDEN", "BM-DOPE", "BM-VICE", 
    "Omnisphere", "Kontakt", "Massive", "Sylenth1", "Spire", "Diva"
  ];
  
  // Clean extensions and eliminate duplicates
  list = list.map(name => name.replace(/\.(vst3|vst|component)$/i, ""));
  list = [...new Set(list)];
  
  if (filterText) {
    const q = filterText.toLowerCase();
    list = list.filter(name => name.toLowerCase().includes(q));
  }
  
  if (list.length === 0) {
    vstPluginList.innerHTML = `<li class="vst-plugin-item" style="color: var(--muted); cursor: default;">No plugins match search</li>`;
    return;
  }
  
  list.forEach(name => {
    const li = document.createElement("li");
    li.className = "vst-plugin-item";
    li.dataset.name = name;
    
    const isFav = vstFavorites.includes(name);
    
    li.innerHTML = `
      <span class="vst-plugin-name">${name}</span>
      <span class="vst-fav-star ${isFav ? 'active' : 'inactive'}">★</span>
    `;
    
    const star = li.querySelector(".vst-fav-star");
    star.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFavorite(name);
    });
    
    li.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      e.stopPropagation();
      showContextMenu(e.clientX, e.clientY, name);
    });
    
    vstPluginList.appendChild(li);
  });
}

function toggleFavorite(name) {
  const index = vstFavorites.indexOf(name);
  if (index === -1) {
    vstFavorites.push(name);
  } else {
    vstFavorites.splice(index, 1);
  }
  localStorage.setItem("vstFavorites", JSON.stringify(vstFavorites));
  
  renderVstExplorerList(vstSearchInput.value);
  populateVstDropdowns(scannedVstPlugins);
}

function showContextMenu(x, y, pluginName) {
  activeContextPlugin = pluginName;
  const isFav = vstFavorites.includes(pluginName);
  contextFavAction.textContent = isFav ? "❌ Remove Favorite" : "⭐ Add to Favorites";
  
  vstContextMenu.style.left = `${x + window.scrollX}px`;
  vstContextMenu.style.top = `${y + window.scrollY}px`;
  vstContextMenu.classList.remove("hidden");
}

document.addEventListener("click", (e) => {
  if (!vstContextMenu.contains(e.target)) {
    vstContextMenu.classList.add("hidden");
  }
});

document.addEventListener("contextmenu", (e) => {
  if (!e.target.closest(".vst-plugin-item")) {
    vstContextMenu.classList.add("hidden");
  }
});

contextFavAction.addEventListener("click", () => {
  if (activeContextPlugin) {
    toggleFavorite(activeContextPlugin);
  }
  vstContextMenu.classList.add("hidden");
});

(async function scanVstPlugins() {
  try {
    const res = await fetch("/api/vst-scan");
    if (!res.ok) throw new Error("scan failed");
    const data = await res.json();
    scannedVstPlugins = data.plugins || [];
    populateVstDropdowns(scannedVstPlugins);
    vstStatus.textContent = `${scannedVstPlugins.length} plugins found (Serum/Beatmaker filtered)`;
  } catch {
    vstStatus.textContent = "Could not scan VST folder (using Serum 2 fallback)";
    populateVstDropdowns([]);
  }
})();

const modeToggle = document.querySelector("#modeToggle");

modeToggle.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const newMode = button.dataset.mode;
  if (newMode === currentMode) return;

  if (newMode === "finisher") {
    const confirmSave = confirm("The Finisher uses destructive subtractive strategies. Please save a copy of your Live Set (File -> Save a Copy) before proceeding. Have you saved a copy?");
    if (!confirmSave) return;
  }

  // Remove all mode classes
  document.body.classList.remove("mode-finisher", "mode-songmaker");

  if (newMode === "finisher") {
    document.body.classList.add("mode-finisher");
    activeLibrary = finisherPromptLibrary;
  } else if (newMode === "songmaker") {
    document.body.classList.add("mode-songmaker");
    activeLibrary = promptLibrary; // not really used, but keeps state consistent
  } else {
    activeLibrary = promptLibrary;
  }

  currentMode = newMode;
  modeToggle.querySelectorAll("button").forEach(b => b.classList.remove("active"));
  button.classList.add("active");

  if (newMode !== "songmaker") {
    activeTab = activeLibrary[0].id;
  }
  renderTabs();
  renderPromptGrid();
});

tabs.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  activeTab = button.dataset.tab;
  renderTabs();
  renderPromptGrid();
});

search.addEventListener("input", renderPromptGrid);

[genre, bpm, key, mood, reference].forEach((field) => {
  field.addEventListener("change", () => {
    if (prompt.value.trim()) prompt.value = customizePrompt(prompt.value);
  });
});

promptGrid.addEventListener("click", (event) => {
  const finderChip = event.target.closest("[data-finder-chip]");
  if (finderChip) {
    finderSelections[finderChip.dataset.group] = finderChip.dataset.value;
    finderCustomValues[finderChip.dataset.group] = "";
    renderPromptGrid();
    return;
  }

  const finderAction = event.target.closest("[data-finder-action]");
  if (finderAction) {
    handleFinderAction(finderAction.dataset.finderAction);
    return;
  }

  const button = event.target.closest("button");
  if (!button) return;
  const selected = findPrompt(button.dataset.prompt);
  if (!selected) return;
  prompt.value = customizePrompt(selected.text);
  prompt.focus();
  // Song Sketch session arrangers auto-submit directly to Ableton
  if (activeTab === "full-arrangers") {
    form.requestSubmit();
  }
});

promptGrid.addEventListener("input", (event) => {
  const customInput = event.target.closest("[data-finder-custom]");
  if (!customInput) return;
  finderCustomValues[customInput.dataset.group] = customInput.value;
  customInput.closest(".finder-group").classList.toggle("custom-active", Boolean(customInput.value.trim()));
  renderFinderSummary();
});

clearPrompt.addEventListener("click", () => {
  prompt.value = "";
  prompt.focus();
});

copyPrompt.addEventListener("click", async () => {
  const text = prompt.value.trim();
  if (!text) return;
  await navigator.clipboard.writeText(text);
  copyPrompt.textContent = "Copied";
  setTimeout(() => {
    copyPrompt.textContent = "Copy";
  }, 1100);
});

makeSongPrompt.addEventListener("click", () => {
  prompt.value = buildFinderPrompt();
  prompt.focus();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = prompt.value.trim();
  if (!text) return;
  lastSentPrompt = text;

  addMessage("user", text);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, vst_map: buildVstMap() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");

    addMessage("assistant", data.reply, data.command && data.command.actions);
    renderEvents(data.events || []);
    refreshStatus();
  } catch (error) {
    addMessage("assistant", error.message);
  }
});

function renderTabs() {
  tabs.innerHTML = "";
  if (currentMode === "songmaker") return;
  activeLibrary.forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.tab = category.id;
    button.className = category.id === activeTab ? "active" : "";
    button.textContent = category.name;
    tabs.appendChild(button);
  });
}

function renderPromptGrid() {
  // Song Maker mode: render the finder UI directly
  if (currentMode === "songmaker") {
    activeMeta.textContent = songMakerMeta.meta;
    activeTitle.textContent = songMakerMeta.title;
    resultCount.textContent = `${Object.keys(finderSelections).length} ingredients`;
    renderSongFinder();
    return;
  }

  const category = activeLibrary.find((item) => item.id === activeTab);

  const query = search.value.trim().toLowerCase();
  const prompts = category.prompts.filter((item) => {
    const haystack = [item.label, item.text, ...item.tags].join(" ").toLowerCase();
    return !query || haystack.includes(query);
  });

  activeMeta.textContent = category.meta;
  activeTitle.textContent = category.title;
  resultCount.textContent = `${prompts.length} prompt${prompts.length === 1 ? "" : "s"}`;
  promptGrid.innerHTML = "";

  prompts.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-button";
    button.dataset.prompt = item.label;
    button.innerHTML = `
      <span>${item.label}</span>
      <small>${item.tags.slice(0, 3).join(" / ")}</small>
    `;
    promptGrid.appendChild(button);
  });

  if (!prompts.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No prompts match that search.";
    promptGrid.appendChild(empty);
  }
}

function renderSongFinder() {
  promptGrid.innerHTML = "";
  const finder = document.createElement("div");
  finder.className = "finder";
  const summary = document.createElement("section");
  summary.className = "finder-summary";
  summary.id = "finderSummary";
  summary.innerHTML = `
    <p class="eyebrow">Current idea</p>
    <h3>${escapeHtml(finderValue("feeling"))}</h3>
    <p>${escapeHtml(finderValue("genre"))} / ${escapeHtml(finderValue("scene"))} / ${escapeHtml(finderValue("energy"))} / ${escapeHtml(finderValue("groove"))}</p>
    <div class="finder-actions">
      <button class="secondary-button" type="button" data-finder-action="random">Surprise Me</button>
      <button class="secondary-button" type="button" data-finder-action="reset">Reset</button>
    </div>
  `;
  finder.appendChild(summary);

  songFinderGroups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "finder-group";
    if (finderCustomValues[group.id].trim()) section.classList.add("custom-active");
    const chips = group.options
      .map((option) => {
        const active = !finderCustomValues[group.id].trim() && finderSelections[group.id] === option ? " active" : "";
        return `<button class="finder-chip${active}" type="button" data-finder-chip="true" data-group="${group.id}" data-value="${escapeAttribute(option)}">${escapeHtml(option)}</button>`;
      })
      .join("");
    section.innerHTML = `
      <h3>${group.label}</h3>
      <div class="finder-chips">${chips}</div>
      <label class="finder-other">
        <span>Other ${group.label}</span>
        <input type="text" data-finder-custom="true" data-group="${group.id}" value="${escapeAttribute(finderCustomValues[group.id])}" placeholder="Write your own ${escapeAttribute(group.label.toLowerCase())}" />
      </label>
    `;
    finder.appendChild(section);
  });

  promptGrid.appendChild(finder);
}

function renderFinderSummary() {
  const summary = document.querySelector("#finderSummary");
  if (!summary) return;
  summary.querySelector("h3").textContent = finderValue("feeling");
  summary.querySelector("p:not(.eyebrow)").textContent = `${finderValue("genre")} / ${finderValue("scene")} / ${finderValue("energy")} / ${finderValue("groove")}`;
}

function handleFinderAction(action) {
  if (action === "random") {
    finderSelections = Object.fromEntries(songFinderGroups.map((group) => [group.id, randomItem(group.options)]));
    finderCustomValues = Object.fromEntries(songFinderGroups.map((group) => [group.id, ""]));
    renderPromptGrid();
    return;
  }
  if (action === "reset") {
    finderSelections = { ...finderDefaults };
    finderCustomValues = Object.fromEntries(songFinderGroups.map((group) => [group.id, ""]));
    renderPromptGrid();
    return;
  }
  if (action === "build") {
    prompt.value = buildFinderPrompt();
    prompt.focus();
  }
}

function buildFinderPrompt() {
  const selected = {
    feeling: finderValue("feeling"),
    scene: finderValue("scene"),
    genre: finderValue("genre"),
    energy: finderValue("energy"),
    groove: finderValue("groove"),
    texture: finderValue("texture"),
    hook: finderValue("hook"),
    bass: finderValue("bass"),
    reference: finderValue("reference"),
  };
  return `Create an original expanded ${selected.genre} song sketch with genre-aware Ableton instruments.

Artist-facing brief: make it feel ${selected.feeling}, like ${selected.scene}. The energy should be ${selected.energy}. The groove should feel ${selected.groove}. The texture palette should lean toward ${selected.texture}. The hook should feel like ${selected.hook}. The bass should act as ${selected.bass}. Use ${selected.reference} only as a loose production reference, without copying melodies, samples, lyrics, or signature sounds.

Translate this into Ableton Live with separated tracks for Chords, Hh / Sh / Rd, Pad, Riff, Hook, Percussion, Snare / Clap, Ambience, Hh / Sh / Rd +, Bd, and Bass. Create section variations, copy the clips to Arrangement View, and start playback.`;
}

function finderValue(groupId) {
  const custom = finderCustomValues[groupId]?.trim();
  return custom || finderSelections[groupId];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function randomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function findPrompt(label) {
  for (const category of [...promptLibrary, ...finisherPromptLibrary]) {
    if (!category.prompts) continue;
    const item = category.prompts.find((entry) => entry.label === label);
    if (item) return item;
  }
  return null;
}

function expandPromptLibrary(expansions) {
  Object.entries(expansions).forEach(([categoryId, promptRows]) => {
    const category = promptLibrary.find((item) => item.id === categoryId);
    if (!category) return;
    const existingLabels = new Set(category.prompts.map((item) => item.label));
    promptRows.forEach(([label, tags, text]) => {
      if (existingLabels.has(label)) return;
      category.prompts.push({ label, tags, text });
    });
  });
}

function customizePrompt(text) {
  const additions = [];
  if (genre.value.trim()) additions.push(`Make it a ${genre.value.trim()} song sketch.`);
  if (bpm.value.trim()) additions.push(`Use ${bpm.value.trim()} BPM.`);
  if (key.value.trim()) additions.push(`Use ${key.value.trim()} as the key or tonal center.`);
  if (mood.value.trim()) additions.push(`Aim for a ${mood.value.trim()} mood.`);
  if (reference.value.trim()) additions.push(`Use ${reference.value.trim()} as a loose creative reference, without copying it.`);
  return additions.length ? `${text}\n\nCustom direction: ${additions.join(" ")}` : text;
}

function addMessage(role, text, actions) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  article.appendChild(paragraph);
  if (actions) {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(actions, null, 2);
    article.appendChild(pre);
  }
  if (role === "assistant") {
    const feedback = document.createElement("div");
    feedback.className = "feedback-actions";
    feedback.innerHTML = `
      <button type="button" data-feedback="up">Useful</button>
      <button type="button" data-feedback="down">Not useful</button>
    `;
    feedback.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      sendFeedback(button.dataset.feedback, text, feedback);
    });
    article.appendChild(feedback);
  }
  messages.prepend(article);
  return article;
}

async function sendFeedback(rating, reply, container) {
  try {
    const response = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, prompt: lastSentPrompt, reply }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Feedback failed");
    container.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    container.dataset.sent = "true";
    renderEvents(data.events || []);
  } catch (error) {
    container.dataset.error = error.message;
  }
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    const state = data.state || {};
    statusBadge.classList.toggle("connected", Boolean(state.connected));
    statusBadge.querySelector("b").textContent = state.connected ? "Live connected" : "Waiting for Live";
    stateList.innerHTML = `
      <div><dt>Connection</dt><dd>${state.connected ? "Connected" : "Not connected"}</dd></div>
      <div><dt>Tempo</dt><dd>${state.tempo ? Number(state.tempo).toFixed(1) : "Unknown"}</dd></div>
      <div><dt>Tracks</dt><dd>${state.track_count ?? "Unknown"}</dd></div>
    `;
    renderEvents(data.events || []);
  } catch (error) {
    statusBadge.classList.remove("connected");
    statusBadge.querySelector("b").textContent = "Server offline";
  }
}

function renderEvents(events) {
  eventsList.innerHTML = "";
  events.slice().reverse().forEach((event) => {
    const item = document.createElement("li");
    const title = document.createElement("b");
    title.textContent = event.type || "event";
    const body = document.createElement("span");
    body.textContent = event.message || "";
    item.append(title, body);
    eventsList.appendChild(item);
  });
}

renderTabs();
renderPromptGrid();
refreshStatus();
setInterval(refreshStatus, 2500);
