/**
 * Vibleton - MIDI Generator
 *
 * Converts The Finisher's JSON response into actual .mid file bytes.
 * Works in both Node/server and browser/client contexts.
 *
 * Required dependency:
 *   npm install @tonejs/midi
 */

import * as ToneMidi from '@tonejs/midi'

type MidiConstructor = typeof import('@tonejs/midi')['Midi']

const Midi = (
  ToneMidi.Midi ??
  (ToneMidi as unknown as { default?: { Midi?: MidiConstructor } }).default?.Midi ??
  (ToneMidi as unknown as { 'module.exports'?: { Midi?: MidiConstructor } })['module.exports']?.Midi
) as MidiConstructor

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

export type FinisherResponse = {
  tempo: number
  barCount: number
  narrative: string
  sections: Section[]
  tracks: Track[]
}

/**
 * Convert a FinisherResponse into MIDI bytes.
 */
export function generateMidi(response: FinisherResponse): Uint8Array {
  const midi = new Midi()

  midi.header.setTempo(response.tempo)
  midi.header.name = `Vibleton - ${response.tempo} BPM`

  const beatDurationSec = 60 / response.tempo

  for (const section of response.sections) {
    const startBeats = section.startBar * 4
    midi.header.meta.push({
      type: 'marker',
      ticks: midi.header.secondsToTicks(startBeats * beatDurationSec),
      text: `${section.name} (intensity ${section.intensity}/10)`,
    })
  }

  for (const track of response.tracks) {
    const midiTrack = midi.addTrack()
    midiTrack.name = track.name

    if (track.instrument === 'drum') {
      midiTrack.channel = 9
    }

    for (const note of track.notes) {
      midiTrack.addNote({
        midi: clamp(note.pitch, 0, 127),
        time: note.start * beatDurationSec,
        duration: Math.max(0.01, note.duration * beatDurationSec),
        velocity: clamp(note.velocity / 127, 0, 1),
      })
    }
  }

  return midi.toArray()
}

/**
 * Browser-only. Generate a MIDI file and trigger a download.
 */
export function downloadMidi(
  response: FinisherResponse,
  filename: string = 'vibleton-track.mid'
): void {
  if (typeof window === 'undefined') {
    throw new Error('downloadMidi can only be called in the browser')
  }

  const bytes = generateMidi(response)
  const arrayBuffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength
  ) as ArrayBuffer
  const blob = new Blob([arrayBuffer], { type: 'audio/midi' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.mid') ? filename : `${filename}.mid`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * Generate one MIDI file per section for Ableton Session View workflows.
 */
export function generateMidiPerSection(
  response: FinisherResponse
): Array<{ filename: string; bytes: Uint8Array }> {
  const beatDurationSec = 60 / response.tempo

  return response.sections.map((section) => {
    const startBeat = section.startBar * 4
    const endBeat = startBeat + section.bars * 4
    const sectionMidi = new Midi()

    sectionMidi.header.setTempo(response.tempo)
    sectionMidi.header.name = `${section.name} - ${response.tempo} BPM`

    for (const track of response.tracks) {
      const midiTrack = sectionMidi.addTrack()
      midiTrack.name = track.name
      if (track.instrument === 'drum') midiTrack.channel = 9

      const sectionNotes = track.notes.filter(
        (note) => note.start >= startBeat && note.start < endBeat
      )

      for (const note of sectionNotes) {
        midiTrack.addNote({
          midi: clamp(note.pitch, 0, 127),
          time: (note.start - startBeat) * beatDurationSec,
          duration: Math.max(0.01, note.duration * beatDurationSec),
          velocity: clamp(note.velocity / 127, 0, 1),
        })
      }
    }

    const sanitized = section.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    return {
      filename: `${String(section.startBar).padStart(3, '0')}-${sanitized}.mid`,
      bytes: sectionMidi.toArray(),
    }
  })
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}
