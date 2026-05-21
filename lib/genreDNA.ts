export type GenreDNA = {
  name: string
  bpmRange: [number, number]
  swingPercent: [number, number] // 50 = straight, 75 = heavy swing
  barGrid: string // "4/4 8-bar phrases"
  structure: string[] // ["intro 8", "build 16", "drop 16" ...]
  kickPattern: string // plain English description
  bassPattern: string
  hiHatPattern: string
  energyArc: string
  rules: string[] // the "grammar" of the genre
  ruleBreakers: string[] // where creativity lives
  blendsWith: string[] // natural fusion partners
  vibeWords: string[] // for matching user's natural language input
}

export const GENRES: Record<string, GenreDNA> = {
  ukGarage: {
    name: 'UK Garage',
    bpmRange: [130, 136],
    swingPercent: [58, 65],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'build 16', 'drop 16', 'break 8', 'drop 2 16', 'outro 8'],
    kickPattern: 'Skippy two-step kick: starts on beat 1, then jumps to the late offbeat before beat 4.',
    bassPattern: 'Sub bass ducks around the kick with syncopated offbeat stabs and short melodic slides.',
    hiHatPattern: 'Swung 16th-note hats with soft ghost hits and a clear bounce.',
    energyArc: 'tension-release',
    rules: [
      'Kick avoids a straight four-on-the-floor pulse.',
      'Snare or clap lands on 2 and 4.',
      'Pitched-up soulful vocal chops are a signature sound.',
      'Sub bass breathes around the kick instead of sitting underneath every beat.',
      'Filtered Rhodes, organ, or pluck stabs work well on offbeats.',
    ],
    ruleBreakers: [
      'Drop the kick for 4 bars and let bass plus snare carry the groove.',
      'Triple-time the hi-hat for a bar before the drop.',
      'Use a half-time snare in the break for breathing room.',
    ],
    blendsWith: ['afrobeats', 'amapiano', 'house', 'grime', 'drumAndBass'],
    vibeWords: ['skippy', 'bouncy', 'swung', 'soulful', 'london', '2-step', 'vocal chop', 'sunday club'],
  },

  house: {
    name: 'House',
    bpmRange: [120, 128],
    swingPercent: [50, 55],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build A 16', 'drop 32', 'breakdown 16', 'drop 2 32', 'outro 16'],
    kickPattern: 'Four-on-the-floor kick on every beat.',
    bassPattern: 'Rolling bass locks tightly with the kick, often repeating one or two notes.',
    hiHatPattern: 'Open hat on the offbeat between every kick.',
    energyArc: 'sustained',
    rules: [
      'Kick stays on every beat.',
      'Clap or snare lands on 2 and 4.',
      'Open hats create the lift between kicks.',
      'Bass and kick should feel glued together.',
      'Long intros and outros keep it DJ-friendly.',
    ],
    ruleBreakers: [
      'Drop the kick for 4 bars while bass and clap continue.',
      'Pitch-bend a vocal sample before the drop.',
      'Use a 3-bar phrase in the breakdown before snapping back to 4.',
    ],
    blendsWith: ['ukGarage', 'techno', 'afrobeats', 'amapiano'],
    vibeWords: ['four on the floor', 'pumping', 'club', 'classic', 'driving', 'groove', 'disco'],
  },

  techno: {
    name: 'Techno',
    bpmRange: [125, 135],
    swingPercent: [50, 52],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build 32', 'peak 32', 'reduction 16', 'peak 2 32', 'outro 16'],
    kickPattern: 'Relentless four-on-the-floor kick with minimal variation.',
    bassPattern: 'Repetitive single-note bass with movement from filter and tone changes, not many notes.',
    hiHatPattern: 'Straight offbeat hats with small texture changes over time.',
    energyArc: 'meditative',
    rules: [
      'Repeat patterns for long stretches.',
      'Use texture and filter movement instead of obvious melody.',
      'Keep the pulse steady and machine-like.',
      'Let small changes carry the arrangement.',
      'Use empty space as part of the groove.',
    ],
    ruleBreakers: [
      'Introduce one vocal or melodic phrase only once in the whole track.',
      'Layer a percussion rhythm that cycles against the main groove.',
      'Drop everything for 8 bars and return without warning.',
    ],
    blendsWith: ['house', 'drumAndBass', 'dubstep'],
    vibeWords: ['driving', 'hypnotic', 'minimal', 'industrial', 'dark', 'berlin', 'pulse', 'machine'],
  },

  drumAndBass: {
    name: 'Drum & Bass',
    bpmRange: [165, 180],
    swingPercent: [50, 55],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build 16', 'drop 32', 'break 16', 'drop 2 32', 'outro 16'],
    kickPattern: 'Fast broken kick pattern with the main hit on beat 1 and another strong hit around beat 3.',
    bassPattern: 'Rolling sub or Reese bass acts as the lead instrument with tone movement carrying the energy.',
    hiHatPattern: 'Busy 8th or 16th-note hats that keep the track racing forward.',
    energyArc: 'tension-release',
    rules: [
      'Fast breakbeat rhythm is central.',
      'Sub bass below the obvious low end needs real weight.',
      'Drops are usually large 32-bar sections.',
      'Breaks create contrast before the next impact.',
      'Bass design matters more than note count.',
    ],
    ruleBreakers: [
      'Half-time the snare for a bar before the drop.',
      'Use a detuned vocal as the lead instead of a synth.',
      'Use triplet hats for 2 bars in a build.',
    ],
    blendsWith: ['jungle', 'ukGarage', 'techno'],
    vibeWords: ['fast', 'rolling', 'sub bass', 'liquid', 'neurofunk', 'breakbeat', 'jungle'],
  },

  jungle: {
    name: 'Jungle',
    bpmRange: [160, 180],
    swingPercent: [50, 55],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'build 16', 'drop 32', 'break 16', 'drop 2 32', 'outro 8'],
    kickPattern: 'Chopped breakbeat kicks with ghost hits and edits that keep surprising the ear.',
    bassPattern: 'Dub-influenced sub bass plays riffs and melodies rather than only long single notes.',
    hiHatPattern: 'Fast breakbeat hats with edits, shuffle, and crunchy sample movement.',
    energyArc: 'wave',
    rules: [
      'Chopped breakbeats define the movement.',
      'Ragga or reggae vocal samples fit naturally.',
      'Bass can carry melody.',
      'Dub delay and reverb work well on vocal stabs.',
      'Energy comes from drum edits as much as tempo.',
    ],
    ruleBreakers: [
      'Drop the entire mix for half a bar of vocal.',
      'Reverse the break for 2 bars in the build.',
      'Pitch the whole track down slightly for the last 8 bars.',
    ],
    blendsWith: ['drumAndBass', 'dubstep', 'grime'],
    vibeWords: ['chopped', 'ragga', 'amen break', 'dub', 'rough', 'sub', '90s', 'breakneck'],
  },

  grime: {
    name: 'Grime',
    bpmRange: [138, 142],
    swingPercent: [50, 55],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'verse 1 16', 'bridge 8', 'verse 2 16', 'drop switch 16', 'outro 8'],
    kickPattern: 'Sparse 140 BPM kick pattern with lots of room for the MC.',
    bassPattern: 'Square, sine, or 808-style bass plays short raw riffs and sharp stabs.',
    hiHatPattern: 'Simple hats, often steady, leaving the main space open for vocal rhythm.',
    energyArc: 'tension-release',
    rules: [
      'Sparse percussion is part of the identity.',
      'Snare usually lands on beat 3 for a half-time feel.',
      'Square-wave and sine bass tones should feel direct and raw.',
      'Short icy melodic stabs are useful.',
      'Leave room for an MC at the front.',
    ],
    ruleBreakers: [
      'Drop into double-time for 4 bars, then return to half-time.',
      'Use a violin or string sample as the lead.',
      'Add a full bar of silence in the middle of a verse.',
    ],
    blendsWith: ['ukGarage', 'dubstep', 'drumAndBass', 'trap'],
    vibeWords: ['square wave', 'eski', 'mc', '140', 'east london', 'sparse', 'riddim', 'dark'],
  },

  dubstep: {
    name: 'Dubstep',
    bpmRange: [138, 142],
    swingPercent: [50, 55],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build 16', 'drop 16', 'break 16', 'drop 2 16', 'outro 16'],
    kickPattern: 'Half-time boom-clap pattern with kick on beat 1 and snare on beat 3.',
    bassPattern: 'Wobble or growl bass plays phrases and fills the midrange, with sub underneath.',
    hiHatPattern: 'Sparse offbeat hats that leave room for bass movement.',
    energyArc: 'tension-release',
    rules: [
      'Half-time feel at around 140 BPM is central.',
      'Bass design carries the song.',
      'Leave big spaces between drum hits.',
      'Sub bass supports the wobble or growl.',
      'Build tension before the drop with restraint.',
    ],
    ruleBreakers: [
      'Use 2 silent bars before the drop.',
      'Switch to triplet bass for one bar.',
      'Drop with no kick on beat 1, only bass and snare.',
    ],
    blendsWith: ['grime', 'drumAndBass', 'trap'],
    vibeWords: ['wobble', 'half-time', 'drop', 'sub', 'growl', 'bass music', 'riddim'],
  },

  afrobeats: {
    name: 'Afrobeats',
    bpmRange: [96, 115],
    swingPercent: [52, 58],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'verse 1 16', 'pre-chorus 4', 'chorus 8', 'verse 2 16', 'bridge 8', 'final chorus 16', 'outro 8'],
    kickPattern: 'Syncopated kick pattern that dances around the vocal instead of pounding every beat.',
    bassPattern: 'Melodic bass often anticipates the next bar and leaves gaps on the obvious downbeats.',
    hiHatPattern: 'Shaker-led 16th-note motion with a shuffled, human feel.',
    energyArc: 'sustained',
    rules: [
      'Layer percussion parts with different rhythms.',
      'Shaker motion carries the groove.',
      'Bass often lands before beat 1.',
      'Talking drum or log drum gives the track identity.',
      'Keep the vocal melody clear.',
    ],
    ruleBreakers: [
      'Drop everything except the shaker for 4 bars.',
      'Use a 3-bar phrase in the bridge.',
      'Pitch the talking drum melodically and make it the lead.',
    ],
    blendsWith: ['amapiano', 'ukGarage', 'house', 'trap'],
    vibeWords: ['groove', 'percussion', 'shaker', 'talking drum', 'polyrhythm', 'naija', 'lagos', 'feel-good'],
  },

  amapiano: {
    name: 'Amapiano',
    bpmRange: [110, 115],
    swingPercent: [55, 62],
    barGrid: '4/4 16-bar phrases',
    structure: ['intro 16', 'build 16', 'groove A 32', 'break 16', 'groove B 32', 'outro 16'],
    kickPattern: 'Slow swung four-on-the-floor kick with a relaxed, patient feel.',
    bassPattern: 'Log drum acts as the bass, playing deep wooden melodic riffs with pitch slides.',
    hiHatPattern: 'Layered shakers and soft hats create a busy but low-pressure top end.',
    energyArc: 'meditative',
    rules: [
      'Log drum bass is the core sound.',
      'Jazzy piano or Rhodes chords fit the feel.',
      'The groove should feel slow and swung.',
      'Percussion can be busy, but not harsh.',
      'Long sections let the track hypnotize.',
    ],
    ruleBreakers: [
      'Use a 3-over-4 percussion rhythm against the main groove.',
      'Drop the piano for an entire section.',
      'Pitch-shift the log drum down an octave for the final section.',
    ],
    blendsWith: ['afrobeats', 'house', 'ukGarage'],
    vibeWords: ['log drum', 'jazzy', 'south africa', 'rhodes', 'lazy', 'soulful', 'piano', 'shaker'],
  },

  trap: {
    name: 'Trap',
    bpmRange: [130, 150],
    swingPercent: [50, 55],
    barGrid: '4/4 8-bar phrases',
    structure: ['intro 8', 'verse 1 16', 'chorus hook 8', 'verse 2 16', 'bridge 8', 'final hook 16', 'outro 8'],
    kickPattern: 'Half-time kick pattern with sparse hits that leave room for the 808.',
    bassPattern: '808 bass is long, tuned, sliding, and usually acts as both bass and weight.',
    hiHatPattern: 'Fast hats with 16th, 32nd, and triplet rolls.',
    energyArc: 'wave',
    rules: [
      'Snare usually lands on beat 3 for a half-time feel.',
      '808 is the only bass voice.',
      'Hi-hat rolls create most of the motion.',
      'Keep the middle of the mix open.',
      'Use a simple atmospheric melody loop.',
    ],
    ruleBreakers: [
      'Switch triplet hats back to straight 16ths mid-bar.',
      'Pitch-bend the 808 down at the end of a phrase.',
      'Drop everything but the 808 for half a bar before the hook.',
    ],
    blendsWith: ['grime', 'dubstep', 'afrobeats'],
    vibeWords: ['808', 'hi-hat roll', 'half-time', 'atlanta', 'drill', 'spacey', 'melodic', 'dark'],
  },
}

export function findGenresByVibe(words: string[]): GenreDNA[] {
  const lowered = words.map((word) => word.toLowerCase())

  return Object.values(GENRES)
    .map((genre) => ({
      genre,
      score: genre.vibeWords.filter((vibeWord) =>
        lowered.some((word) => vibeWordMatches(word, vibeWord))
      ).length,
    }))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((result) => result.genre)
}

function vibeWordMatches(word: string, vibeWord: string): boolean {
  if (!word || !vibeWord) return false
  if (vibeWord.includes(' ')) return word === vibeWord
  return word === vibeWord || word.replace(/s$/, '') === vibeWord.replace(/s$/, '')
}

export function buildPromptContext(genreId: string): string {
  const genre = GENRES[genreId]
  if (!genre) return ''

  return `
GENRE: ${genre.name}
TEMPO: ${genre.bpmRange[0]}-${genre.bpmRange[1]} BPM
SWING: ${genre.swingPercent[0]}-${genre.swingPercent[1]}% (50 = straight, 75 = heavy swing)
BAR GRID: ${genre.barGrid}
ENERGY ARC: ${genre.energyArc}

STRUCTURE:
${genre.structure.map((section) => `  - ${section}`).join('\n')}

KICK: ${genre.kickPattern}
BASS: ${genre.bassPattern}
HI-HAT: ${genre.hiHatPattern}

RULES:
${genre.rules.map((rule) => `  - ${rule}`).join('\n')}

CREATIVE RULE-BREAKERS:
${genre.ruleBreakers.map((rule) => `  - ${rule}`).join('\n')}
  `.trim()
}

export function buildBlendPromptContext(
  genreAId: string,
  genreBId: string,
  bias: number = 0.5
): string {
  const genreA = GENRES[genreAId]
  const genreB = GENRES[genreBId]
  if (!genreA || !genreB) return ''

  const bpmA = (genreA.bpmRange[0] + genreA.bpmRange[1]) / 2
  const bpmB = (genreB.bpmRange[0] + genreB.bpmRange[1]) / 2
  const bpm = Math.round(bpmA * (1 - bias) + bpmB * bias)

  const swingA = (genreA.swingPercent[0] + genreA.swingPercent[1]) / 2
  const swingB = (genreB.swingPercent[0] + genreB.swingPercent[1]) / 2
  const swing = Math.round(swingA * (1 - bias) + swingB * bias)

  const dominant = bias < 0.5 ? genreA : genreB
  const flavour = bias < 0.5 ? genreB : genreA

  return `
BLEND: ${genreA.name} x ${genreB.name}
BIAS: ${Math.round((1 - bias) * 100)}% ${genreA.name} / ${Math.round(bias * 100)}% ${genreB.name}
TARGET TEMPO: ${bpm} BPM
TARGET SWING: ${swing}%

STRUCTURE:
Use ${dominant.name}'s arrangement:
${dominant.structure.map((section) => `  - ${section}`).join('\n')}

RHYTHMIC FLAVOUR:
Borrow from ${flavour.name}:
  - KICK: ${flavour.kickPattern}
  - BASS: ${flavour.bassPattern}
  - HI-HAT: ${flavour.hiHatPattern}

COMBINED RULES:
${dominant.rules.slice(0, 3).map((rule) => `  - [${dominant.name}] ${rule}`).join('\n')}
${flavour.rules.slice(0, 2).map((rule) => `  - [${flavour.name}] ${rule}`).join('\n')}
  `.trim()
}

export function findGenresByTempo(bpm: number, tolerance: number = 5): GenreDNA[] {
  return Object.values(GENRES).filter(
    (genre) => bpm >= genre.bpmRange[0] - tolerance && bpm <= genre.bpmRange[1] + tolerance
  )
}

export function getBlendSuggestions(genreId: string): GenreDNA[] {
  const genre = GENRES[genreId]
  if (!genre) return []

  return genre.blendsWith
    .slice(0, 3)
    .map((partnerId) => GENRES[partnerId])
    .filter((partner): partner is GenreDNA => Boolean(partner))
}
