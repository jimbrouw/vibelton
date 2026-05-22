'use client'

import { FormEvent, useState } from 'react'

type GenreCard = {
  label: string
  subline: string
  description: string
  prompt: string
  genreId: string
}

const classicChicagoJackingPrompt =
  'Create a detailed Classic, Chicago, and Jacking House song sketch at 124-128 BPM with raw TR-707/TR-909-style drum-machine grooves, a jacking bassline, punchy claps on 2 and 4, swung open hats, short vocal shouts, gospel or disco piano stabs, organ bass movement, and a warehouse-friendly arrangement with a DJ intro, stripped groove sections, call-and-response hook moments, a piano or organ breakdown, a tough final jack section, and an outro. Keep it physical, repetitive, simple, and club-functional rather than overly polished.'
const acidHousePrompt =
  'Create a detailed Acid House song sketch at 122-128 BPM with a Roland TB-303-style resonant bassline, squelchy filter automation, repetitive hypnotic riffing, raw machine-funk drums, tight claps, bright hats, psychedelic delay throws, and gradual mixer-style movement. Build a DJ-friendly structure with an acid intro, main 303 groove, filter-rise tension, sparse breakdown, louder acid jack drop, and extended outro. Make the 303 line the central hook and keep the arrangement hypnotic, ravey, and tactile.'
const deepHousePrompt =
  'Create a detailed Deep House song sketch at 118-124 BPM with warm seventh and ninth chords, soulful or jazzy harmony, understated drums, a subby syncopated bassline, soft pads, Rhodes-style keys, subtle percussion, and restrained emotional atmosphere. Arrange it with a soft drum intro, chord-and-bass groove, pad lift, intimate breakdown, deeper second groove, small melodic variation, and smooth DJ outro. Avoid obvious EDM drops; focus on warmth, groove, space, and late-night feeling.'
const soulfulGospelGaragePrompt =
  'Create a detailed Soulful, Gospel, and Garage House song sketch at 122-126 BPM with full vocal-hook energy, church-influenced piano and organ chords, gospel call-and-response phrases, R and B harmony, swung garage drums, warm bass, live-feeling keys, backing-vocal stabs, and an emotional club arrangement. Include a vocal or chopped-vocal intro, verse-like groove, uplifting piano breakdown, organ-led lift, chorus-style release, and extended club outro. Make it songful, human, and expressive while staying DJ-ready.'
const discoFunkyFilterFrenchPrompt =
  'Create a detailed Disco, Funky, Filter, and French House song sketch at 122-128 BPM with filtered disco or funk loops, bright house drums, live-style bass guitar movement, guitar chops, brass or string stabs, celebratory vocal snippets, sidechain pump, and dramatic filter sweeps. Arrange it with a looped DJ intro, filtered build, full disco-funk groove, breakdown with rising filter automation, compressed French-house style drop, short sample-cut variation, and clean outro. Make it upbeat, glossy, sample-driven, and dancefloor-friendly.'

const subGenreCards: GenreCard[] = [
  {
    label: 'Classic, Chicago, and Jacking House',
    subline: '124-128 BPM · Raw · Jacking',
    description: 'Drum-machine swing, organ or piano stabs, short vocal shouts, and a body-led Chicago warehouse groove.',
    prompt: classicChicagoJackingPrompt,
    genreId: 'classicChicagoJackingHouse',
  },
  {
    label: 'Acid House',
    subline: '122-128 BPM · 303 · Hypnotic',
    description: 'Squelchy 303 bass, raw drum machines, filter movement, delay, and repetitive warehouse-rave pressure.',
    prompt: acidHousePrompt,
    genreId: 'acidHouse',
  },
  {
    label: 'Deep House',
    subline: '118-124 BPM · Warm · Soulful',
    description: 'Warm chords, subby bass, Rhodes keys, pads, subtle drums, and a restrained late-night club mood.',
    prompt: deepHousePrompt,
    genreId: 'deepHouse',
  },
  {
    label: 'Soulful, Gospel, and Garage House',
    subline: '122-126 BPM · Vocal · Swung',
    description: 'Gospel piano, organ bass, soulful vocals, garage swing, warm bass, and an emotional club release.',
    prompt: soulfulGospelGaragePrompt,
    genreId: 'soulfulGospelGarageHouse',
  },
  {
    label: 'Disco, Funky, Filter, and French House',
    subline: '122-128 BPM · Funky · Filtered',
    description: 'Disco loops, funk bass, guitar chops, brass or strings, filter sweeps, and glossy French-house compression.',
    prompt: discoFunkyFilterFrenchPrompt,
    genreId: 'discoFunkyFilterFrenchHouse',
  },
]

const directGenreCards: GenreCard[] = [
  {
    label: 'Techno',
    subline: '125–135 BPM · Hypnotic · Machine-like',
    description: 'Steady club pressure built from repetition, dark texture, and small changes over time.',
    prompt: 'Create an expanded Techno song sketch with a hypnotic pulse, dark texture, machine-like drums, and slow-building pressure.',
    genreId: 'techno',
  },
  {
    label: 'UK Garage',
    subline: '130–136 BPM · Skippy · Swung',
    description: 'Bouncy two-step drums, soulful chords, and sub bass that moves around the groove.',
    prompt: 'Create an expanded UK Garage song sketch with skippy two-step drums, soulful chords, vocal-chop energy, and bouncy sub bass.',
    genreId: 'ukGarage',
  },
  {
    label: 'Trap',
    subline: '130–150 BPM · Sparse · 808-led',
    description: 'Half-time drums, tuned 808 bass, fast hats, and a moody melodic loop.',
    prompt: 'Create an expanded Trap song sketch with sparse half-time drums, tuned 808 bass, fast hi-hat rolls, and a dark melodic hook.',
    genreId: 'trap',
  },
]

export default function Home() {
  const [userInput, setUserInput] = useState('')
  const [genreId, setGenreId] = useState('house')
  const [result, setResult] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function handleCardClick(card: GenreCard) {
    setUserInput(card.prompt)
    setGenreId(card.genreId)
    setResult('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setResult('')

    try {
      const response = await fetch('/api/finisher', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ genreId, userInput }),
      })
      const data = await response.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (error) {
      setResult(error instanceof Error ? error.message : 'Request failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="genre-page">
      <section className="genre-shell" aria-labelledby="genre-heading">
        <div className="genre-header">
          <h1>Vibleton</h1>
          <p>The Finisher API is available at /api/finisher.</p>
        </div>

        <section className="genre-section" aria-labelledby="genre-heading">
          <h2 id="genre-heading">Pick your sound</h2>

          <details className="genre-parent-card">
            <summary>
              <span>
                <strong>House</strong>
                <small>Classic · Acid · Deep · Garage · Disco</small>
              </span>
            </summary>
            <div className="genre-sub-cards">
              {subGenreCards.map((card) => (
                <button
                  className="prompt-button genre-sub-card"
                  key={card.genreId}
                  onClick={() => handleCardClick(card)}
                  type="button"
                >
                  <span>{card.label}</span>
                  <small className="genre-subline">{card.subline}</small>
                  <p className="genre-description">{card.description}</p>
                </button>
              ))}
            </div>
          </details>

          <div className="direct-genre-grid">
            {directGenreCards.map((card) => (
              <button
                className="prompt-button"
                key={card.genreId}
                onClick={() => handleCardClick(card)}
                type="button"
              >
                <span>{card.label}</span>
                <small className="genre-subline">{card.subline}</small>
                <p className="genre-description">{card.description}</p>
              </button>
            ))}
          </div>
        </section>

        <form className="genre-form" onSubmit={handleSubmit}>
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            onChange={(event) => setUserInput(event.target.value)}
            placeholder="Choose a genre card or write a prompt..."
            rows={5}
            value={userInput}
          />
          <input name="genreId" type="hidden" value={genreId} />
          <button disabled={!userInput.trim() || isSubmitting} type="submit">
            {isSubmitting ? 'Generating...' : 'Generate'}
          </button>
        </form>

        {result ? <pre className="genre-result">{result}</pre> : null}
      </section>

      <style jsx>{`
        .genre-page {
          --bg: #101312;
          --ink: #f3f0e8;
          --muted: #b9c2ba;
          --soft: #d7ded5;
          --line: #2c342f;
          --panel: #171c1a;
          --panel-strong: #202823;
          --dark: #0b0e0d;
          --accent: #67b99a;
          background: var(--bg);
          color: var(--ink);
          font-family: Avenir Next, Avenir, Montserrat, Trebuchet MS, sans-serif;
          min-height: 100dvh;
          padding: 48px 20px;
        }

        .genre-shell {
          width: min(960px, 100%);
          margin: 0 auto;
          display: grid;
          gap: 28px;
        }

        .genre-header {
          display: grid;
          gap: 6px;
        }

        .genre-header h1,
        .genre-section h2 {
          margin: 0;
          letter-spacing: 0;
        }

        .genre-header h1 {
          font-size: clamp(2rem, 7vw, 4.5rem);
          line-height: 0.95;
        }

        .genre-header p,
        .genre-description,
        .genre-subline {
          color: var(--muted);
        }

        .genre-header p,
        .genre-description {
          margin: 0;
          line-height: 1.55;
        }

        .genre-section {
          display: grid;
          gap: 14px;
        }

        .genre-section h2 {
          font-size: 1.35rem;
          line-height: 1.2;
        }

        .genre-parent-card {
          background: var(--panel-strong);
          border: 1px solid var(--line);
          border-radius: 8px;
          overflow: hidden;
        }

        .genre-parent-card summary {
          cursor: pointer;
          list-style: none;
          padding: 16px;
          outline: none;
        }

        .genre-parent-card summary::-webkit-details-marker {
          display: none;
        }

        .genre-parent-card summary span {
          align-items: center;
          display: flex;
          gap: 12px;
          justify-content: space-between;
        }

        .genre-parent-card summary strong {
          font-size: 1.15rem;
        }

        .genre-parent-card summary small {
          color: var(--muted);
        }

        .genre-parent-card summary span::after {
          color: var(--muted);
          content: '▸';
          font-size: 1rem;
          line-height: 1;
        }

        .genre-parent-card[open] summary span::after {
          color: var(--accent);
          transform: rotate(90deg);
        }

        .genre-sub-cards,
        .direct-genre-grid {
          display: grid;
          gap: 8px;
        }

        .genre-sub-cards {
          padding: 8px 16px 16px;
        }

        .direct-genre-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .prompt-button {
          background: var(--panel-strong);
          border: 1px solid var(--line);
          border-radius: 8px;
          color: var(--ink);
          cursor: pointer;
          display: grid;
          gap: 10px;
          min-height: 128px;
          padding: 15px;
          text-align: left;
        }

        .prompt-button span {
          font-weight: 700;
        }

        .genre-subline {
          display: block;
          font-size: 0.88rem;
          line-height: 1.35;
        }

        .genre-description {
          font-size: 0.95rem;
        }

        .genre-form {
          display: grid;
          gap: 10px;
        }

        .genre-form label {
          color: var(--muted);
          font-size: 0.9rem;
          font-weight: 700;
        }

        .genre-form textarea,
        .genre-form button {
          border-radius: 8px;
          border: 1px solid var(--line);
        }

        .genre-form textarea {
          background: var(--panel);
          color: var(--ink);
          min-height: 128px;
          padding: 14px;
          resize: vertical;
        }

        .genre-form button {
          background: var(--accent);
          color: var(--dark);
          cursor: pointer;
          font-weight: 800;
          justify-self: start;
          padding: 12px 18px;
        }

        .genre-form button:disabled {
          cursor: not-allowed;
          opacity: 0.55;
        }

        .genre-result {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          color: var(--soft);
          margin: 0;
          max-height: 360px;
          overflow: auto;
          padding: 16px;
          white-space: pre-wrap;
        }

        @media (prefers-reduced-motion: no-preference) {
          .genre-parent-card summary span::after {
            transition: color 200ms ease, transform 200ms ease;
          }
        }

        @media (max-width: 760px) {
          .genre-page {
            padding: 28px 14px;
          }

          .direct-genre-grid {
            grid-template-columns: 1fr;
          }

          .genre-parent-card summary span {
            align-items: flex-start;
            flex-direction: column;
          }
        }
      `}</style>
    </main>
  )
}
