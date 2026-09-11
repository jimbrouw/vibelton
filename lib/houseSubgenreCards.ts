export type HouseSubgenreCard = {
  label: string
  subline: string
  description: string
  prompt: string
  genreId: string
}

export const HOUSE_SUBGENRE_CARDS: HouseSubgenreCard[] = [
  {
    label: 'Classic, Chicago, and Jacking House',
    subline: '124-128 BPM / Raw / Jacking',
    description: 'Drum-machine swing, organ or piano stabs, short vocal shouts, and a body-led Chicago warehouse groove.',
    prompt:
      'Create a detailed Classic, Chicago, and Jacking House song sketch at 124-128 BPM with raw TR-707/TR-909-style drum-machine grooves, a jacking bassline, punchy claps on 2 and 4, swung open hats, short vocal shouts, gospel or disco piano stabs, organ bass movement, and a warehouse-friendly arrangement with a DJ intro, stripped groove sections, call-and-response hook moments, a piano or organ breakdown, a tough final jack section, and an outro. Keep it physical, repetitive, simple, and club-functional rather than overly polished.',
    genreId: 'classicChicagoJackingHouse',
  },
  {
    label: 'Acid House',
    subline: '122-128 BPM / 303 / Hypnotic',
    description: 'Squelchy 303 bass, raw drum machines, filter movement, delay, and repetitive warehouse-rave pressure.',
    prompt:
      'Create a detailed Acid House song sketch at 122-128 BPM with a Roland TB-303-style resonant bassline, squelchy filter automation, repetitive hypnotic riffing, raw machine-funk drums, tight claps, bright hats, psychedelic delay throws, and gradual mixer-style movement. Build a DJ-friendly structure with an acid intro, main 303 groove, filter-rise tension, sparse breakdown, louder acid jack drop, and extended outro. Make the 303 line the central hook and keep the arrangement hypnotic, ravey, and tactile.',
    genreId: 'acidHouse',
  },
  {
    label: 'Deep House',
    subline: '118-124 BPM / Warm / Soulful',
    description: 'Warm chords, subby bass, Rhodes keys, pads, subtle drums, and a restrained late-night club mood.',
    prompt:
      'Create a detailed Deep House song sketch at 118-124 BPM with warm seventh and ninth chords, soulful or jazzy harmony, understated drums, a subby syncopated bassline, soft pads, Rhodes-style keys, subtle percussion, and restrained emotional atmosphere. Arrange it with a soft drum intro, chord-and-bass groove, pad lift, intimate breakdown, deeper second groove, small melodic variation, and smooth DJ outro. Avoid obvious EDM drops; focus on warmth, groove, space, and late-night feeling.',
    genreId: 'deepHouse',
  },
  {
    label: 'Soulful, Gospel, and Garage House',
    subline: '122-126 BPM / Vocal / Swung',
    description: 'Gospel piano, organ bass, soulful vocals, garage swing, warm bass, and an emotional club release.',
    prompt:
      'Create a detailed Soulful, Gospel, and Garage House song sketch at 122-126 BPM with full vocal-hook energy, church-influenced piano and organ chords, gospel call-and-response phrases, R and B harmony, swung garage drums, warm bass, live-feeling keys, backing-vocal stabs, and an emotional club arrangement. Include a vocal or chopped-vocal intro, verse-like groove, uplifting piano breakdown, organ-led lift, chorus-style release, and extended club outro. Make it songful, human, and expressive while staying DJ-ready.',
    genreId: 'soulfulGospelGarageHouse',
  },
  {
    label: 'Disco, Funky, Filter, and French House',
    subline: '122-128 BPM / Funky / Filtered',
    description: 'Disco loops, funk bass, guitar chops, brass or strings, filter sweeps, and glossy French-house compression.',
    prompt:
      'Create a detailed Disco, Funky, Filter, and French House song sketch at 122-128 BPM with filtered disco or funk loops, bright house drums, live-style bass guitar movement, guitar chops, brass or string stabs, celebratory vocal snippets, sidechain pump, and dramatic filter sweeps. Arrange it with a looped DJ intro, filtered build, full disco-funk groove, breakdown with rising filter automation, compressed French-house style drop, short sample-cut variation, and clean outro. Make it upbeat, glossy, sample-driven, and dancefloor-friendly.',
    genreId: 'discoFunkyFilterFrenchHouse',
  },
  {
    label: 'Tech House, Minimal, and Deep Tech',
    subline: '124-130 BPM / Dry / Rolling',
    description: 'Rolling bass, dry drums, short vocal chops, micro-edits, and precise after-hours club pressure.',
    prompt:
      'Create a detailed Tech House, Minimal, and Deep Tech song sketch at 124-130 BPM with a punchy dry kick, rolling subby bassline, tight percussion loops, clipped vocal chops, small synth stabs, micro-edits, restrained effects, and a dark room tone. Arrange it with a DJ intro, bass-and-drum lock, reduced minimal breakdown, percussive rebuild, functional drop, subtle variation pass, and clean outro. Keep the groove precise, low-slung, repetitive, and club-tool focused.',
    genreId: 'techMinimalDeepTechHouse',
  },
  {
    label: 'Progressive, Melodic, and Organic House',
    subline: '120-126 BPM / Evolving / Emotional',
    description: 'Long builds, arps, pads, acoustic textures, and gradual melodic tension and release.',
    prompt:
      'Create a detailed Progressive, Melodic, and Organic House song sketch at 120-126 BPM with long-form arrangement, warm bass, emotional chord movement, evolving arps, atmospheric pads, acoustic or world-instrument textures, hand percussion, field-recording ambience, and gradual automation. Include a patient intro, motif reveal, deep groove, cinematic breakdown, melodic lift, restrained peak, and extended outro. Make it expansive, polished, and emotionally tense without becoming a mainstage EDM drop.',
    genreId: 'progressiveMelodicOrganicHouse',
  },
  {
    label: 'Electro, Complextro, Big-Room, and Festival House',
    subline: '126-130 BPM / Aggressive / Mainstage',
    description: 'Big synth riffs, compressed drums, bright toplines, rapid edits, and festival-scale drops.',
    prompt:
      'Create a detailed Electro, Complextro, Big-Room, and Festival House song sketch at 126-130 BPM with aggressive saw or square bass, punchy compressed drums, huge kick impact, sharp synth riffs, bright lead hooks, glitchy complextro fills, snare builds, rave stabs, and wide festival reverb. Arrange it with a vocal or synth intro, dramatic build, stripped pre-drop, explosive drop, short breakdown, second drop with edited bass variations, and final outro. Make it bold, loud, energetic, and mainstage-ready.',
    genreId: 'electroComplextroBigRoomFestivalHouse',
  },
  {
    label: 'Future House and Bass House',
    subline: '124-132 BPM / Plucky / Heavy',
    description: 'Plucky bass design, clipped vocals, wobble movement, tight drops, and modern mix density.',
    prompt:
      'Create a detailed Future House and Bass House song sketch at 124-132 BPM with metallic pluck bass, shuffled house groove, chopped vocal hooks, aggressive wobble or growl bass answers, crisp drums, tight fills, pop-friendly tension, and bass-music drop energy. Arrange it with a short hook intro, vocal-chop build, first drop, bass call-and-response section, breakdown, heavier second drop, and outro. Make the mix dense, punchy, modern, and drop-focused.',
    genreId: 'futureBassHouse',
  },
  {
    label: 'Tribal, Afro, Latin, and Global House',
    subline: '118-124 BPM / Percussive / Global',
    description: 'Percussion-led grooves, polyrhythms, chants, regional instruments, and call-and-response hooks.',
    prompt:
      'Create a detailed Tribal, Afro, Latin, and Global House song sketch at 118-124 BPM with congas, bongos, shakers, toms, polyrhythmic percussion, chant-like vocal phrases, call-and-response hooks, regional melodic instruments, warm deep bass, sparse chords, and a groove-first structure. Include a percussion intro, bass entry, vocal or chant section, drum-circle breakdown, layered rhythm rebuild, peak groove, and outro. Keep harmony simple and let rhythm, space, and human percussion drive the track.',
    genreId: 'tribalAfroLatinGlobalHouse',
  },
  {
    label: 'Ambient, Leftfield, Outsider, and Lo-Fi House',
    subline: '112-122 BPM / Textural / Dusty',
    description: 'Soft pulse, degraded samples, unusual structures, ambient pads, tape noise, and experimental edges.',
    prompt:
      'Create a detailed Ambient, Leftfield, Outsider, and Lo-Fi House song sketch at 112-122 BPM with softened house drums, dusty or muffled samples, tape hiss, vinyl noise, wide ambient pads, odd found-sound textures, minimal bass movement, degraded chord loops, and unconventional arrangement turns. Build a slow intro, hazy groove, texture drift, reduced breakdown, rough-edged return, and fading outro. Make it atmospheric, imperfect, experimental, and emotionally worn rather than polished.',
    genreId: 'ambientLeftfieldOutsiderLofiHouse',
  },
  {
    label: 'Jazz, Broken Beat, and Lounge House',
    subline: '115-124 BPM / Jazzy / Sophisticated',
    description: 'Jazz harmony, syncopated drums, Rhodes keys, horn stabs, live-feeling bass, and lounge polish.',
    prompt:
      'Create a detailed Jazz, Broken Beat, and Lounge House song sketch at 115-124 BPM with Rhodes or electric piano seventh and ninth chords, syncopated broken-beat accents, brushed or soft house drums, upright or electric bass movement, jazz horn or vibraphone stabs, subtle percussion, and polished lounge atmosphere. Arrange it with a smooth intro, chord-led groove, small solo-like riff, broken-beat breakdown, refined hook return, and outro. Make it musical, relaxed, harmonically rich, and sophisticated.',
    genreId: 'jazzBrokenBeatLoungeHouse',
  },
  {
    label: 'Hard, Rave, and High-Energy House',
    subline: '128-140 BPM / Rave / Peak',
    description: 'Hard kicks, rave stabs, piano riffs, hoovers, fast builds, and maximal club pressure.',
    prompt:
      'Create a detailed Hard, Rave, and High-Energy House song sketch at 128-140 BPM with harder kicks, fast hats, rave piano riffs, hoover-style synths, big diva or crowd vocal samples, aggressive bass, snare rolls, old-school stabs, and maximal peak-time pressure. Arrange it with a direct intro, rave-stab hook, high-energy drop, piano breakdown, long riser, harder final drop, and outro. Make it urgent, bright, physical, and built for a packed room.',
    genreId: 'hardRaveHighEnergyHouse',
  },
  {
    label: 'Club, Regional, and Footwork-Adjacent House',
    subline: '130-160 BPM / Chopped / Regional',
    description: 'Fast edits, chopped vocals, regional drum patterns, battle energy, and club-tool repetition.',
    prompt:
      'Create a detailed Club, Regional, and Footwork-Adjacent House song sketch at 130-160 BPM with chopped vocal callouts, fast repetitive edits, regional club drum language, sparse but heavy low end, syncopated percussion, short sample stabs, and dance-battle utility. Blend juke, footwork, ghetto-tech, Baltimore, Jersey, Philly, and ballroom-inspired energy while keeping the track DJ-functional. Arrange it with a quick intro, vocal-chop groove, drum-pattern switch, stripped battle break, harder return, and abrupt tool-style outro.',
    genreId: 'clubRegionalFootworkAdjacentHouse',
  },
  {
    label: 'Pop, Commercial, and Crossover House',
    subline: '115-126 BPM / Hooky / Polished',
    description: 'Radio vocals, short arrangements, clean drops, simple chords, and streaming-friendly hooks.',
    prompt:
      'Create a detailed Pop, Commercial, and Crossover House song sketch at 115-126 BPM with polished radio-ready vocals or vocal-chop hooks, simple emotional chords, clean pluck or piano motifs, accessible bass, tidy house drums, short builds, and compact streaming-friendly sections. Arrange it with intro, verse, pre-hook, chorus-style drop, second verse, bridge or breakdown, final hook, and clean ending. Make it catchy, direct, polished, and easy to understand on first listen.',
    genreId: 'popCommercialCrossoverHouse',
  },
  {
    label: 'Dub, Techno, and Machine-Soul Hybrids',
    subline: '118-128 BPM / Dubby / Machine-soul',
    description: 'Dub delay, techno chords, machine percussion, sparse vocals, and soulful futuristic restraint.',
    prompt:
      'Create a detailed Dub, Techno, and Machine-Soul Hybrids song sketch at 118-128 BPM with dub chords, echo sends, tape-delay throws, machine percussion, warm but futuristic bass, Detroit-style soulful chord color, sparse vocal fragments, filtered stabs, and restrained techno-influenced sound design. Arrange it with a spacious intro, dub-chord groove, delay-heavy breakdown, machine-soul motif, deeper second pass, and echoing outro. Make it hypnotic, spacious, warm, and mechanically elegant.',
    genreId: 'dubTechnoMachineSoulHouse',
  },
]
