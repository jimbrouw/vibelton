/**
 * Vibleton - The Finisher API Route
 *
 * POST /api/finisher
 *
 * Takes what the user has (loops, vibe, tempo) and returns a complete track
 * arrangement as structured MIDI data, ready to convert to .mid files.
 *
 * Default env:
 *   LLM_API_KEY=<OpenRouter API key>
 *   LLM_MODEL=google/gemini-2.5-flash
 *   LLM_BASE_URL=https://openrouter.ai/api/v1
 *
 * Optional:
 *   LLM_PROVIDER=openrouter | openai-compatible | anthropic
 */

import { NextRequest, NextResponse } from 'next/server'
import {
  GENRES,
  buildBlendPromptContext,
  buildPromptContext,
} from '../../../lib/genreDNA'

type FinisherRequest = {
  genreId: string
  blendWith?: string
  blendBias?: number
  tempo?: number
  userInput: string
  testMode?: boolean
}

type MidiNote = {
  pitch: number
  start: number
  duration: number
  velocity: number
}

type Track = {
  name: string
  instrument: 'drum' | 'bass' | 'pad' | 'lead' | 'vocal-chop' | 'fx'
  notes: MidiNote[]
}

type Section = {
  name: string
  startBar: number
  bars: number
  intensity: number
  description: string
}

type FinisherResponse = {
  tempo: number
  barCount: number
  narrative: string
  sections: Section[]
  tracks: Track[]
}

type ChatProvider = 'openrouter' | 'openai-compatible' | 'anthropic'

type TextContentBlock = {
  type: string
  text?: string
}

type AnthropicResponse = {
  content?: TextContentBlock[]
}

type OpenAICompatibleResponse = {
  choices?: Array<{
    message?: {
      content?: string | Array<TextContentBlock>
    }
    finish_reason?: string
  }>
  usage?: {
    completion_tokens?: number
    prompt_tokens?: number
    total_tokens?: number
  }
  error?: {
    message?: string
  }
}

const PROVIDER = (process.env.LLM_PROVIDER ?? 'openrouter') as ChatProvider
const MODEL =
  process.env.LLM_MODEL ??
  (PROVIDER === 'anthropic' ? 'claude-sonnet-4-6' : 'google/gemini-2.5-flash')
const OPENAI_COMPATIBLE_BASE_URL =
  process.env.LLM_BASE_URL ??
  (PROVIDER === 'openrouter' ? 'https://openrouter.ai/api/v1' : 'https://api.openai.com/v1')
const MAX_TOKENS = Number(process.env.LLM_MAX_TOKENS ?? '3000')
const REPAIR_MAX_TOKENS = Number(process.env.LLM_REPAIR_MAX_TOKENS ?? '3000')

const SYSTEM_PROMPT = `You are Vibleton - an Ableton Live assistant for producers who work by vibe, not music theory.

Your job is The Finisher: the user has loops they made, you generate the missing pieces of their track. Drums, bass, transitions, full arrangement. Everything you generate is editable MIDI.

CRITICAL RULES:
- Never use music theory jargon in any text the user will read (no "tonic", "dominant", "diminished", "circle of fifths"). In narrative and section descriptions, speak like a knowledgeable producer friend.
- Never mention AI, machine learning, or any technical term related to how you work.
- Use plain English: "the feeling underneath" instead of "chord progression", "the journey" instead of "arrangement", "the pulse" instead of "rhythm".
- You return ONLY valid JSON matching the schema. No prose outside the JSON.
- Use the genre context as your constraint set, but trust your taste - break the rules where it makes the track better.

OUTPUT SCHEMA (return JSON exactly matching this shape):
{
  "tempo": <number>,
  "barCount": <number, total bars in the full track>,
  "narrative": "<2-3 sentences in plain English describing the track journey>",
  "sections": [
    {
      "name": "<section name>",
      "startBar": <0-indexed>,
      "bars": <number>,
      "intensity": <0-10>,
      "description": "<plain English, what happens here>"
    }
  ],
  "tracks": [
    {
      "name": "<e.g. 'Kick', 'Sub Bass', 'Pluck Lead'>",
      "instrument": "<drum | bass | pad | lead | vocal-chop | fx>",
      "notes": [
        { "pitch": <MIDI note 0-127>, "start": <beats from track start>, "duration": <beats>, "velocity": <0-127> }
      ]
    }
  ]
}

MIDI NOTE CONVENTIONS:
- Drum notes use the General MIDI map: kick = 36, snare = 38, clap = 39, closed hat = 42, open hat = 46, ride = 51, crash = 49, low tom = 41, mid tom = 47, hi tom = 50, rim = 37, shaker = 70.
- Bass tracks must be strictly monophonic (one note at a time, never chords) and sit in a low register (MIDI note numbers 24 to 55). Never write chords or high-pitched melodies for the bass track.
- Bass and melodic instruments: pick a key that fits the vibe and stay diatonic unless the genre context says otherwise. Default to F minor if uncertain - it's a forgiving key.
- 1 bar in 4/4 = 4 beats. So a 16-bar section spans beats 0-64.
- Velocity: kicks 100-115, snares 95-110, hi-hats 70-90 (with variation for human feel), bass 95-110, pads 60-80.

GENERATE A FULL TRACK:
- Include at minimum: kick, snare/clap, hi-hat, bass.
- For appropriate genres add: pad, lead, vocal-chop, fx.
- Vary patterns across sections - don't just loop the same bar. Add fills, drops, variations.
- The user already has loops - your job is the scaffold they can drop their loops into. Leave room for what they made.`

function buildUserPrompt(req: FinisherRequest): string {
  const genre = GENRES[req.genreId]
  if (!genre) throw new Error(`Unknown genre: ${req.genreId}`)

  const context =
    req.blendWith && GENRES[req.blendWith]
      ? buildBlendPromptContext(req.genreId, req.blendWith, req.blendBias ?? 0.5)
      : buildPromptContext(req.genreId)

  const tempo = req.tempo ?? Math.round((genre.bpmRange[0] + genre.bpmRange[1]) / 2)

  const scope = req.testMode
    ? `
TEST MODE:
Generate a compact 16-bar sketch only. Use 2 sections of 8 bars each. Keep each track to 8-16 notes maximum so the JSON stays small.`
    : ''

  const finalInstruction = req.testMode
    ? 'Now generate the compact test arrangement as JSON matching the schema. Return ONLY the JSON object, nothing else.'
    : 'Now generate the full track arrangement as JSON matching the schema. Return ONLY the JSON object, nothing else.'

  return `${context}

USER'S TARGET TEMPO: ${tempo} BPM

WHAT THE USER HAS:
${req.userInput}
${scope}

${finalInstruction}`
}

function extractJson(text: string): FinisherResponse {
  const cleaned = text
    .replace(/^```(?:json)?\s*/m, '')
    .replace(/\s*```\s*$/m, '')
    .trim()

  const parsed: unknown = JSON.parse(cleaned)
  if (!isFinisherResponse(parsed)) {
    throw new Error('Response missing required fields')
  }

  return parsed
}

function isFinisherResponse(value: unknown): value is FinisherResponse {
  if (!isRecord(value)) return false

  return (
    typeof value.tempo === 'number' &&
    typeof value.barCount === 'number' &&
    typeof value.narrative === 'string' &&
    Array.isArray(value.sections) &&
    value.sections.every(isSection) &&
    Array.isArray(value.tracks) &&
    value.tracks.every(isTrack)
  )
}

function isSection(value: unknown): value is Section {
  return (
    isRecord(value) &&
    typeof value.name === 'string' &&
    typeof value.startBar === 'number' &&
    typeof value.bars === 'number' &&
    typeof value.intensity === 'number' &&
    typeof value.description === 'string'
  )
}

function isTrack(value: unknown): value is Track {
  return (
    isRecord(value) &&
    typeof value.name === 'string' &&
    isInstrument(value.instrument) &&
    Array.isArray(value.notes) &&
    value.notes.every(isMidiNote)
  )
}

function isMidiNote(value: unknown): value is MidiNote {
  return (
    isRecord(value) &&
    typeof value.pitch === 'number' &&
    typeof value.start === 'number' &&
    typeof value.duration === 'number' &&
    typeof value.velocity === 'number'
  )
}

function isInstrument(value: unknown): value is Track['instrument'] {
  return (
    value === 'drum' ||
    value === 'bass' ||
    value === 'pad' ||
    value === 'lead' ||
    value === 'vocal-chop' ||
    value === 'fx'
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

async function generateFinisherText(userPrompt: string, systemPrompt: string = SYSTEM_PROMPT): Promise<string> {
  if (PROVIDER === 'anthropic') {
    return generateAnthropicText(userPrompt, systemPrompt, MAX_TOKENS)
  }

  return generateOpenAICompatibleText(userPrompt, systemPrompt, MAX_TOKENS)
}

async function generateOpenAICompatibleText(
  userPrompt: string,
  systemPrompt: string,
  maxTokens: number
): Promise<string> {
  const apiKey = process.env.LLM_API_KEY ?? process.env.OPENROUTER_API_KEY ?? process.env.OPENAI_API_KEY
  if (!apiKey) {
    throw new Error('Missing LLM_API_KEY')
  }

  const response = await fetch(`${OPENAI_COMPATIBLE_BASE_URL.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      ...(PROVIDER === 'openrouter'
        ? {
            'HTTP-Referer': process.env.OPENROUTER_SITE_URL ?? 'http://localhost:3000',
            'X-Title': process.env.OPENROUTER_APP_NAME ?? 'Vibleton',
          }
        : {}),
    },
    body: JSON.stringify({
      model: MODEL,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: maxTokens,
      response_format: { type: 'json_object' },
    }),
  })

  const data = (await response.json()) as OpenAICompatibleResponse
  if (!response.ok) {
    throw new Error(data.error?.message ?? `LLM request failed with ${response.status}`)
  }

  const content = data.choices?.[0]?.message?.content
  if (typeof content === 'string') {
    if (!content.trim()) {
      throw new Error(
        `Model returned empty content. finish_reason=${data.choices?.[0]?.finish_reason ?? 'unknown'}`
      )
    }
    return content
  }
  if (Array.isArray(content)) {
    const text = content.find((block) => block.type === 'text')?.text
    if (text) return text
  }

  throw new Error(`No text response from model. finish_reason=${data.choices?.[0]?.finish_reason ?? 'unknown'}`)
}

async function generateAnthropicText(
  userPrompt: string,
  systemPrompt: string,
  maxTokens: number
): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY ?? process.env.LLM_API_KEY
  if (!apiKey) {
    throw new Error('Missing ANTHROPIC_API_KEY or LLM_API_KEY')
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: maxTokens,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  })

  const data = (await response.json()) as AnthropicResponse & { error?: { message?: string } }
  if (!response.ok) {
    throw new Error(data.error?.message ?? `Anthropic request failed with ${response.status}`)
  }

  const text = data.content?.find((block) => block.type === 'text')?.text
  if (!text) {
    throw new Error('No text response from model')
  }

  return text
}

async function repairJsonText(brokenJson: string, parseError: string): Promise<string> {
  const repairPrompt = `The following text was intended to be one JSON object matching the FinisherResponse schema, but JSON.parse failed with this error:
${parseError}

Return ONLY a corrected valid JSON object. Do not add markdown. Do not explain anything.

BROKEN JSON:
${brokenJson}`

  const repairSystemPrompt = `You repair malformed JSON. Return only valid JSON. Preserve as much data as possible.`

  if (PROVIDER === 'anthropic') {
    return generateAnthropicText(repairPrompt, repairSystemPrompt, REPAIR_MAX_TOKENS)
  }

  return generateOpenAICompatibleText(repairPrompt, repairSystemPrompt, REPAIR_MAX_TOKENS)
}

function postProcessBassTrack(track: Track): Track {
  if (!track.notes || track.notes.length === 0) {
    return track
  }

  // 1. Enforce monophony: group by start time, keep lowest pitch
  const byStart: { [key: number]: MidiNote } = {}
  for (const note of track.notes) {
    const start = note.start
    if (byStart[start] === undefined) {
      byStart[start] = note
    } else {
      if (note.pitch < byStart[start].pitch) {
        byStart[start] = note
      }
    }
  }

  const monophonic = Object.values(byStart).sort((a, b) => a.start - b.start)

  if (monophonic.length === 0) {
    return { ...track, notes: [] }
  }

  // 2. Enforce register: average pitch between 28 and 45. Shift by octaves.
  const averagePitch = monophonic.reduce((sum, note) => sum + note.pitch, 0) / monophonic.length

  let semitoneShift = 0
  while (averagePitch + semitoneShift > 45) {
    semitoneShift -= 12
  }
  while (averagePitch + semitoneShift < 28) {
    semitoneShift += 12
  }

  const processedNotes = monophonic.map((note) => {
    let newPitch = note.pitch + semitoneShift
    // Clamp strictly between 24 and 55
    while (newPitch > 55) {
      newPitch -= 12
    }
    while (newPitch < 24) {
      newPitch += 12
    }
    return {
      ...note,
      pitch: newPitch,
    }
  })

  return {
    ...track,
    notes: processedNotes,
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as FinisherRequest

    if (!body.genreId || !GENRES[body.genreId]) {
      return NextResponse.json({ error: 'Invalid or missing genreId' }, { status: 400 })
    }
    if (!body.userInput || typeof body.userInput !== 'string') {
      return NextResponse.json({ error: 'Missing userInput' }, { status: 400 })
    }
    if (body.blendWith && !GENRES[body.blendWith]) {
      return NextResponse.json({ error: 'Invalid blendWith genre' }, { status: 400 })
    }

    const text = await generateFinisherText(buildUserPrompt(body))
    try {
      const responseObj = extractJson(text)
      responseObj.tracks = responseObj.tracks.map((t) => {
        if (t.instrument === 'bass' || t.name.toLowerCase().includes('bass')) {
          return postProcessBassTrack(t)
        }
        return t
      })
      return NextResponse.json(responseObj)
    } catch (error) {
      const parseError = error instanceof Error ? error.message : 'Unknown parse error'
      const repairedText = await repairJsonText(text, parseError)
      const responseObj = extractJson(repairedText)
      responseObj.tracks = responseObj.tracks.map((t) => {
        if (t.instrument === 'bass' || t.name.toLowerCase().includes('bass')) {
          return postProcessBassTrack(t)
        }
        return t
      })
      return NextResponse.json(responseObj)
    }
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json({ error: 'Finisher failed', detail }, { status: 500 })
  }
}
