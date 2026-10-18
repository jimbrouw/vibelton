/* Composition Lab: guided multi-part MIDI score editor with progressive disclosure. */
(() => {
  const root = document.querySelector('#compositionLab');
  const roles = ['drums', 'percussion', 'bass', 'chords', 'motif', 'counterline'];
  const roleLabels = {
    drums: 'Drums (Kick/Snare/Hat)',
    percussion: 'Percussion',
    bass: 'Bassline',
    chords: 'Chords / Pads',
    motif: 'Lead Motif',
    counterline: 'Counterline / Arp',
  };
  const ingredientNames = {
    interlocking: 'Interlocking percussion',
    angular: 'Angular ensemble',
    spacious: 'Open / spacious',
    jungle: 'Jungle breaks',
    uk_bass: 'UK bass syncopation',
    sparse: 'Sparse phrasing',
  };
  const expressions = {
    density: 'Note Density',
    syncopation: 'Syncopation',
    swing: 'Swing Feel',
    timing: 'Human Timing',
    tension: 'Harmonic Tension',
    space: 'Rest & Space',
  };
  const noteNames = ['C', 'C# / Db', 'D', 'Eb', 'E', 'F', 'F# / Gb', 'G', 'Ab', 'A', 'Bb', 'B'];
  const midiToNoteName = midi => {
    const n = Number(midi || 60);
    const name = noteNames[((n % 12) + 12) % 12];
    const octave = Math.floor(n / 12) - 1;
    return `${name} (${octave})`;
  };

  const escape = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const clone = x => JSON.parse(JSON.stringify(x));
  const duration = n => `${Math.floor(n / 60)}:${String(Math.round(n % 60)).padStart(2, '0')}`;
  const barBeats = s => (s.metre[0] * 4) / s.metre[1];

  const COPY_STORAGE_KEY = 'vibelton-working-copy-confirmed';
  const getStoredCopyConfirmed = () => sessionStorage.getItem(COPY_STORAGE_KEY) === 'true';
  const setStoredCopyConfirmed = val => {
    savedCopy = Boolean(val);
    sessionStorage.setItem(COPY_STORAGE_KEY, savedCopy ? 'true' : 'false');
    window.dispatchEvent(new CustomEvent('vibelton-copy-confirmed', {detail: savedCopy}));
  };

  let doc,
    revision = 0,
    selected,
    history = [],
    live = {},
    jobs = [],
    dirty = false,
    busy = false,
    message = '',
    error = false,
    savedCopy = getStoredCopyConfirmed(),
    bassDensity = 'medium',
    bassMovement = 'syncopated_hook',
    bassSwing = 0.16,
    bassScope = 'selected';

  window.addEventListener('vibelton-copy-confirmed', e => {
    savedCopy = Boolean(e.detail);
  });

  const localKey = 'vibelton-composition-draft-v1';

  async function api(path = '', payload) {
    const response = await fetch(
      '/api/composition' + path,
      payload === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)}
    );
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Composition request failed');
    return result;
  }

  function cache() {
    try {
      localStorage.setItem(localKey, JSON.stringify({revision, composition: doc, dirty}));
    } catch {
      message = 'Browser draft storage is full. Save this draft to keep it.';
    }
  }

  function changed() {
    dirty = true;
    cache();
  }

  function notify(text, failed = false) {
    message = text;
    error = failed;
    const box = root.querySelector('#labMessage');
    if (box) {
      box.textContent = text;
      box.classList.toggle('lab-error', failed);
    }
  }

  async function run(work) {
    if (busy) return;
    busy = true;
    render();
    try {
      await work();
    } catch (e) {
      notify(e.message, true);
    } finally {
      busy = false;
      render();
    }
  }

  async function load() {
    await run(async () => {
      const data = await api();
      doc = data.composition;
      revision = data.revision;
      history = data.history;
      live = data.live;
      jobs = data.jobs;
      const cached = JSON.parse(localStorage.getItem(localKey) || 'null');
      if (cached?.dirty && cached.revision === revision) {
        doc = cached.composition;
        dirty = true;
      } else if (cached?.dirty) {
        notify('Loaded the latest saved revision (your older unsaved browser draft is still in local storage).', false);
      }
      selected = doc.sections[0].id;
    });
  }

  const option = (value, label, current) => `<option value="${escape(value)}" ${value === current ? 'selected' : ''}>${escape(label)}</option>`;
  const input = (label, path, value, type = 'text', extra = '') =>
    `<label><span>${escape(label)}</span><input data-doc="${path}" type="${type}" value="${escape(value)}" ${extra}></label>`;

  function render() {
    if (!doc) {
      root.innerHTML = `<div class="lab-intro"><h2>Compose MIDI</h2><p>${escape(message || 'Loading your composition workspace…')}</p><button data-action="reload">Reload</button></div>`;
      return;
    }
    const section = doc.sections.find(s => s.id === selected) || doc.sections[0];
    selected = section.id;
    const total = doc.sections.reduce((n, s) => n + barBeats(s) * s.bars, 0);
    const seconds = (total * 60) / doc.bpm;
    const fresh = live.connected && Date.now() / 1000 - live.updated_at < 10;
    const ready = fresh && live.capabilities?.includes('composition_v1');
    const midi = (live.tracks || []).filter(t => t.type === 'midi' && t.id);
    const disabled = busy ? 'disabled' : '';
    const blocked = busy || dirty || !revision || !ready || !savedCopy ? 'disabled' : '';
    const rootPitchClass = ((Number(doc.root_midi || 57) % 12) + 12) % 12;
    const assignedCount = roles.filter(r => doc.assignments?.[r]?.id).length;
    let beat = 0;

    root.innerHTML = `
      <div class="lab-header-bar">
        <div>
          <p class="eyebrow">MULTI-PART MIDI COMPOSER</p>
          <h2>${escape(doc.title || 'Untitled Composition')}</h2>
          <p class="lab-subline">Key: <strong>${escape(noteNames[rootPitchClass])} ${escape(doc.mode)}</strong> · <strong>${doc.bpm} BPM</strong> · <strong>${doc.sections.length} sections</strong> (${duration(seconds)} total)</p>
        </div>
        <div class="lab-duration-box">
          <strong>${duration(seconds)}</strong>
          <span>Target ${duration(doc.target_seconds)} (${Math.abs(seconds - doc.target_seconds) < 0.5 ? 'Exact fit' : `${seconds > doc.target_seconds ? '+' : ''}${Math.round(seconds - doc.target_seconds)}s`})</span>
        </div>
      </div>

      <section class="lab-workflow-bar" aria-label="Composition workflow steps">
        <div class="lab-workflow-step">
          <span class="lab-step-num">1. Start / Import</span>
          <button data-action="from-project" ${disabled} title="Import tempo, key, and tracks from your open Ableton Set">✨ Seed from Open Set</button>
        </div>
        <div class="lab-workflow-step">
          <span class="lab-step-num">2. Save Changes</span>
          <button class="${dirty ? 'lab-primary' : ''}" data-action="save" ${disabled}>${dirty ? '💾 Save Draft (Required before Apply)' : `✓ Saved (Rev ${revision})`}</button>
        </div>
        <div class="lab-workflow-step lab-workflow-apply">
          <span class="lab-step-num">3. Send to Ableton Live</span>
          <div class="lab-apply-controls">
            <label class="lab-check lab-copy-check">
              <input id="labWorkingCopy" type="checkbox" ${savedCopy ? 'checked' : ''}>
              <span>Working copy saved</span>
            </label>
            <button class="${!dirty && savedCopy && ready ? 'lab-primary' : ''}" data-action="preview" ${blocked} title="Write and loop only the selected section in Ableton">▶ Preview Section</button>
            <button class="${!dirty && savedCopy && ready ? 'lab-primary' : ''}" data-action="build" ${blocked} title="Write the entire multi-section arrangement into Ableton">🏗 Build Full Arrangement</button>
          </div>
        </div>
        <details class="lab-more-tools">
          <summary>More Tools</summary>
          <div class="lab-more-tools-menu">
            <button data-action="fit" ${disabled}>⏱ Fit Target Duration (${duration(doc.target_seconds)})</button>
            <button data-action="copy" ${disabled}>📋 Copy Brief for AI</button>
            <button data-action="reload" ${disabled}>↺ Discard Unsaved Edits</button>
          </div>
        </details>
      </section>

      <div id="labMessage" class="lab-message ${error ? 'lab-error' : ''}" role="status" aria-live="polite">
        ${escape(
          message ||
            (dirty
              ? 'You have unsaved edits. Click "Save Draft" above to compile notes before sending to Ableton.'
              : !ready
              ? 'Draft editing is ready. Connect Ableton Live to preview or build sections in your Set.'
              : !savedCopy
              ? 'Check "Working copy saved" above to enable Preview Section and Build Full Arrangement.'
              : 'Select any section below to adjust its bars, time signature, energy, or active instruments.')
        )}
      </div>

      ${doc.source_clips_used?.length ? `<div class="lab-panel" style="padding:10px 14px;margin-bottom:12px">
        <small><strong>👁️ Seeded from Open Set MIDI:</strong> Extracted motif &amp; key from ${doc.source_clips_used.map(c => `${escape(c.track_name)} ("${escape(c.clip_name)}", ${c.note_count} notes)`).join(' · ')}</small>
      </div>` : ''}

      <section class="lab-panel" aria-label="Bass Companion Quick-Generator Bar" style="margin-bottom:14px">
        <div class="lab-panel-heading" style="margin-bottom:8px">
          <div>
            <p class="eyebrow">SMYLZ BASS COMPANION · CROSS-TRACK GROOVE LOCK</p>
            <h3>Kick-Locked Bassline Generator</h3>
          </div>
          <span>Locks downbeats to your kick &amp; places 2-bar syncopated answers in the gaps</span>
        </div>
        <div class="lab-fields" style="align-items:end">
          <label>
            <span>Density</span>
            <select id="bassCompanionDensity">
              ${option('sparse', 'Sparse (Sub Anchor)', bassDensity)}
              ${option('medium', 'Medium (Groove Answer)', bassDensity)}
              ${option('rolling', 'Rolling (16th Pocket)', bassDensity)}
            </select>
          </label>
          <label>
            <span>Movement</span>
            <select id="bassCompanionMovement">
              ${option('syncopated_hook', 'Syncopated Hook', bassMovement)}
              ${option('octave_jump', 'Octave Jump', bassMovement)}
              ${option('fifth_glide', 'Fifth Glide', bassMovement)}
              ${option('pedal', 'Pedal Sub', bassMovement)}
            </select>
          </label>
          <label>
            <span>Swing <output>${Math.round(bassSwing * 100)}%</output></span>
            <input id="bassCompanionSwing" type="range" min="0" max="0.35" step="0.02" value="${bassSwing}">
          </label>
          <label>
            <span>Apply Scope</span>
            <select id="bassCompanionScope">
              ${option('selected', `Selected Section (${section.name})`, bassScope)}
              ${option('all', 'All Unlocked Sections', bassScope)}
            </select>
          </label>
          <button class="lab-primary" data-action="bass-companion" ${disabled}>⚡ Generate Kick-Locked Bass</button>
        </div>
      </section>

      <div class="lab-grid">
        <div class="lab-main">
          <section class="lab-panel">
            <div class="lab-panel-heading">
              <div>
                <p class="eyebrow">SECTION TIMELINE</p>
                <h3>Song Structure (${doc.sections.length} passages)</h3>
              </div>
              <span>Click any bar or row to inspect &amp; edit</span>
            </div>
            <div class="lab-ribbon" aria-label="Composition energy and metre">
              ${doc.sections
                .map(
                  s =>
                    `<button data-select="${escape(s.id)}" style="flex:${barBeats(s) * s.bars};--energy:${s.energy}" title="${escape(s.name)} · ${s.metre.join('/')} · ${s.bars} bars" aria-label="Select ${escape(s.name)}" class="${selected === s.id ? 'selected' : ''}"><span>${s.metre.join('/')}</span></button>`
                )
                .join('')}
            </div>
            <div class="lab-timeline">
              ${doc.sections
                .map((s, i) => {
                  const at = (beat * 60) / doc.bpm;
                  beat += barBeats(s) * s.bars;
                  return `<div class="lab-row ${selected === s.id ? 'selected' : ''}">
                    <button class="lab-row-main" data-select="${escape(s.id)}" aria-pressed="${selected === s.id}">
                      <span class="lab-index">${String(i + 1).padStart(2, '0')}</span>
                      <span>
                        <b>${escape(s.name)} ${s.locked ? '🔒' : ''}</b>
                        <small>Starts at ${duration(at)} · ${s.active_parts.length} active part${s.active_parts.length === 1 ? '' : 's'}</small>
                      </span>
                      <strong>${s.metre.join('/')}</strong>
                      <span>${s.bars} bars</span>
                    </button>
                    <div class="lab-row-actions">
                      <button data-move="${i}" data-direction="-1" title="Move section earlier" aria-label="Move ${escape(s.name)} up" ${i === 0 || s.locked || busy ? 'disabled' : ''}>↑</button>
                      <button data-move="${i}" data-direction="1" title="Move section later" aria-label="Move ${escape(s.name)} down" ${i === doc.sections.length - 1 || s.locked || busy ? 'disabled' : ''}>↓</button>
                    </div>
                  </div>`;
                })
                .join('')}
            </div>
          </section>

          <details class="lab-panel" ${assignedCount === 0 && midi.length > 0 ? 'open' : ''}>
            <summary><b>Instrument Track Assignments</b><span>${assignedCount} of ${roles.length} roles assigned to Live MIDI tracks</span></summary>
            <p class="lab-help">Choose which existing MIDI track in Ableton plays each musical role. Your instruments, presets, and mixer settings stay untouched.</p>
            <div class="lab-fields">
              ${roles
                .map(
                  role =>
                    `<label><span>${escape(roleLabels[role] || role)}</span><select data-role="${role}">${option('', 'Choose a MIDI track in Live…', doc.assignments[role]?.id || '')}${midi
                      .map(t => option(t.id, t.name + (t.devices?.length ? ' · ' + t.devices.map(d => d.name).join(', ') : ''), doc.assignments[role]?.id))
                      .join('')}</select></label>`
                )
                .join('')}
            </div>
            <div class="lab-small-actions">
              <button data-action="refresh" ${disabled}>↻ Refresh Live Tracks</button>
            </div>
            <details class="lab-subdetails">
              <summary>Advanced: Drum MIDI Note Mapping (Kick, Snare, Hat note numbers)</summary>
              <div class="lab-fields" style="margin-top:10px">
                ${Object.entries(doc.drum_notes)
                  .map(([name, note]) => input(`${name} (${midiToNoteName(note)})`, 'drum_notes.' + name, note, 'number', 'min="0" max="127"'))
                  .join('')}
              </div>
            </details>
          </details>

          <details class="lab-panel">
            <summary><b>Song Key, Tempo &amp; Creative Brief</b><span>${escape(noteNames[rootPitchClass])} ${escape(doc.mode)} · ${doc.bpm} BPM</span></summary>
            <div class="lab-fields">
              ${input('Song Title', 'title', doc.title)}
              ${input('Mood / Vibe', 'mood', doc.mood)}
              <label>
                <span>Root Key</span>
                <select data-root-pitch>
                  ${noteNames.map((n, idx) => `<option value="${idx}" ${idx === rootPitchClass ? 'selected' : ''}>${escape(n)}</option>`).join('')}
                </select>
              </label>
              <label>
                <span>Scale Mode</span>
                <select data-doc="mode">${option('minor', 'Minor', doc.mode)}${option('major', 'Major', doc.mode)}</select>
              </label>
              ${input('Tempo (BPM)', 'bpm', doc.bpm, 'number', 'min="40" max="240"')}
              ${input('Target Duration (seconds)', 'target_seconds', doc.target_seconds, 'number', 'min="10" max="900"')}
              <label class="lab-wide"><span>Creative Notes / Brief</span><textarea data-doc="brief" rows="2">${escape(doc.brief)}</textarea></label>
            </div>
            <details class="lab-subdetails">
              <summary>Advanced Generator Settings (Motif intervals, seed, style ingredients)</summary>
              <div class="lab-fields" style="margin-top:10px">
                ${input('Exact Root MIDI Note (24–84)', 'root_midi', doc.root_midi, 'number', 'min="24" max="84"')}
                ${input('Variation Seed', 'seed', doc.seed, 'number', 'min="0" max="2147483647"')}
                <label class="lab-wide"><span>Motif Semitone Intervals</span><input data-motif value="${doc.motif.join(', ')}"></label>
              </div>
              <div class="lab-ingredients">
                ${['rhythm', 'harmony', 'phrasing', 'structure']
                  .map(
                    area =>
                      `<fieldset><legend>${area}</legend>${Object.entries(ingredientNames)
                        .map(
                          ([id, label]) =>
                            `<label class="lab-check"><input type="checkbox" data-ingredient="${area}" value="${id}" ${(doc.ingredients[area] || []).includes(id) ? 'checked' : ''}><span>${label}</span></label>`
                        )
                        .join('')}</fieldset>`
                  )
                  .join('')}
              </div>
            </details>
          </details>

          <details class="lab-panel">
            <summary><b>Saved Revisions &amp; Live Build History</b><span>${history.length} saved revisions · ${jobs.length} Live runs</span></summary>
            <div class="lab-two-col">
              <div>
                <h4>Revision History</h4>
                <div class="lab-history">
                  ${history.length
                    ? history
                        .slice()
                        .reverse()
                        .map(h => `<button data-restore="${h.revision}">Revision ${h.revision}<span>${escape(h.title)}</span><small>${new Date(h.created_at * 1000).toLocaleTimeString()}</small></button>`)
                        .join('')
                    : '<p class="lab-help">No saved revisions yet.</p>'}
                </div>
              </div>
              <div>
                <div class="lab-panel-heading">
                  <h4>Live Builds</h4>
                  <button data-action="refresh" ${disabled}>↻ Refresh</button>
                </div>
                <div id="labJobs">${jobsHTML()}</div>
              </div>
            </div>
          </details>
        </div>

        <aside class="lab-inspector">
          <section class="lab-panel">
            <div class="lab-panel-heading" style="margin-bottom:8px">
              <div>
                <p class="eyebrow">SELECTED PASSAGE</p>
                <h3>${escape(section.name)}</h3>
              </div>
              <label class="lab-check" style="margin:0" title="Locking prevents any edits or regeneration in this section">
                <input type="checkbox" data-section="locked" ${section.locked ? 'checked' : ''}>
                <span>🔒 Lock</span>
              </label>
            </div>
            <p class="lab-help" style="margin-top:0">${duration((barBeats(section) * section.bars * 60) / doc.bpm)} · ${section.parts ? Object.values(section.parts).reduce((n, p) => n + p.notes.length, 0) : 0} MIDI notes</p>

            <fieldset class="lab-section-fields" ${section.locked || busy ? 'disabled' : ''}>
              <label><span>Section Name</span><input data-section="name" value="${escape(section.name)}"></label>
              <div class="lab-fields">
                <label>
                  <span>Time Signature</span>
                  <select data-section="metre">${['4/4', '3/4', '5/4', '7/8', '9/8'].map(m => option(m, m, section.metre.join('/'))).join('')}</select>
                </label>
                <label><span>Length (Bars)</span><input type="number" min="1" max="256" data-section="bars" value="${section.bars}"></label>
              </div>
              <label>
                <span>Section Energy <output>${Math.round(section.energy * 100)}%</output></span>
                <input type="range" min="0" max="1" step=".05" data-section="energy" value="${section.energy}">
              </label>

              <div class="lab-parts">
                <span><strong>Active Instruments</strong></span>
                <span><strong>Lock Notes</strong></span>
                ${roles
                  .map(
                    role =>
                      `<label class="lab-check"><input type="checkbox" data-active="${role}" ${section.active_parts.includes(role) ? 'checked' : ''} ${section.parts[role]?.locked ? 'disabled' : ''}><span>${escape(roleLabels[role] || role)}</span></label><label class="lab-part-lock"><input type="checkbox" title="Keep current ${role} notes when varying" aria-label="Lock ${role} notes" data-part-lock="${role}" ${section.parts[role]?.locked ? 'checked' : ''} ${!section.parts[role] ? 'disabled' : ''}></label>`
                  )
                  .join('')}
              </div>

              <details class="lab-subdetails">
                <summary>Advanced Phrasing (Motif Transform &amp; Accent Grouping)</summary>
                <div style="margin-top:10px">
                  <label>
                    <span>Motif Development</span>
                    <select data-section="motif_transform">
                      ${[
                        ['original', 'Original motif'],
                        ['displace', 'Rhythmic displacement'],
                        ['fragment', 'Fragmented phrases'],
                        ['stretch', 'Stretched / half-time feel'],
                        ['return', 'Home return'],
                      ]
                        .map(([val, lbl]) => option(val, lbl, section.motif_transform))
                        .join('')}
                    </select>
                  </label>
                  <label><span>Accent Grouping (e.g. 2+2+3)</span><input data-section="grouping" value="${section.grouping.join('+')}"></label>
                </div>
              </details>
            </fieldset>

            <div class="lab-small-actions">
              <button class="lab-primary" data-action="regenerate" ${section.locked || busy ? 'disabled' : ''}>🎲 Vary Unlocked Parts</button>
              <button data-action="duplicate" ${disabled}>Duplicate Section</button>
            </div>
          </section>

          <details class="lab-panel">
            <summary><b>Global Expression</b><span>Density, Swing &amp; Feel</span></summary>
            ${Object.entries(expressions)
              .map(
                ([key, label]) =>
                  `<label><span>${label}<output>${Math.round(doc.expression[key] * 100)}%</output></span><input data-doc="expression.${key}" type="range" min="0" max="1" step=".05" value="${doc.expression[key]}"></label>`
              )
              .join('')}
            <p class="lab-help">Adjusting these sliders updates unlocked parts the next time you click <strong>Save Draft</strong>.</p>
          </details>
        </aside>
      </div>`;
  }

  function jobsHTML() {
    return jobs.length
      ? jobs
          .slice()
          .reverse()
          .map(
            j =>
              `<article>
                <div><b>Rev ${j.revision} · ${j.preview ? 'Section Preview' : 'Full Arrangement'}</b><span class="lab-badge">${escape(j.status)}</span></div>
                <p>${escape(
                  j.execution?.preview_error ||
                    j.execution?.error ||
                    j.error ||
                    (j.status === 'Applied'
                      ? 'Clips placed and verified in Ableton Live.'
                      : j.status === 'Verified'
                      ? 'Clips and time-signature markers verified.'
                      : 'Sending to Ableton Live…')
                )}</p>
                <small>${j.execution?.completed_clips || 0} clips placed · starts at beat ${j.start_beat}</small>
                ${j.markers?.length ? `<details><summary>Time-signature marker checklist (${j.markers.length})</summary>${j.markers.map(m => `<p>Beat ${m.beat} · ${m.metre.join('/')} · ${escape(m.section)}</p>`).join('')}</details>` : ''}
              </article>`
          )
          .join('')
      : '<p class="lab-help">No builds sent yet. Saving a draft only updates your browser score.</p>';
  }

  async function save(extra = {}) {
    const result = await api('/save', {base_revision: revision, composition: doc, ...extra});
    doc = result.composition;
    revision = result.revision;
    dirty = false;
    cache();
    history.push({revision, title: doc.title, created_at: result.created_at});
    notify(`Revision ${revision} saved (${duration(result.compiled.seconds)}). Ready to preview or build in Ableton Live.`);
  }

  root.addEventListener('change', e => {
    if (!doc || busy) return;
    const t = e.target,
      section = doc.sections.find(s => s.id === selected);
    if (t.id === 'labWorkingCopy') {
      setStoredCopyConfirmed(t.checked);
      render();
      return;
    }
    if (t.id === 'bassCompanionDensity') {
      bassDensity = t.value;
      render();
      return;
    }
    if (t.id === 'bassCompanionMovement') {
      bassMovement = t.value;
      render();
      return;
    }
    if (t.id === 'bassCompanionSwing') {
      bassSwing = Number(t.value);
      render();
      return;
    }
    if (t.id === 'bassCompanionScope') {
      bassScope = t.value;
      render();
      return;
    }
    if (t.hasAttribute('data-root-pitch')) {
      const targetClass = Number(t.value);
      const currentOctaveBase = Math.floor(Number(doc.root_midi || 57) / 12) * 12;
      let nextMidi = currentOctaveBase + targetClass;
      if (nextMidi < 36) nextMidi += 12;
      if (nextMidi > 72) nextMidi -= 12;
      doc.root_midi = nextMidi;
    } else if (t.dataset.doc) {
      const keys = t.dataset.doc.split('.');
      let target = doc;
      for (const k of keys.slice(0, -1)) target = target[k];
      target[keys.at(-1)] = ['number', 'range'].includes(t.type) ? Number(t.value) : t.value;
    } else if (t.hasAttribute('data-motif')) {
      doc.motif = t.value.split(',').map(x => Number(x.trim()));
    } else if (t.dataset.ingredient) {
      const list = doc.ingredients[t.dataset.ingredient];
      doc.ingredients[t.dataset.ingredient] = t.checked ? [...list, t.value] : list.filter(x => x !== t.value);
    } else if (t.dataset.role) {
      const track = live.tracks.find(x => x.id === t.value);
      doc.assignments[t.dataset.role] = track ? {id: track.id, name: track.name, session_id: live.session_id} : null;
    } else if (t.dataset.section) {
      const field = t.dataset.section;
      if (field === 'metre') {
        section.metre = t.value.split('/').map(Number);
        section.grouping = {3: [3], 4: [2, 2], 5: [3, 2], 7: [2, 2, 3], 9: [2, 2, 2, 3]}[section.metre[0]] || [section.metre[0]];
      } else if (field === 'grouping') {
        section.grouping = t.value.split('+').map(Number);
      } else {
        section[field] = t.type === 'checkbox' ? t.checked : ['number', 'range'].includes(t.type) ? Number(t.value) : t.value;
      }
    } else if (t.dataset.active) {
      section.active_parts = t.checked ? [...section.active_parts, t.dataset.active] : section.active_parts.filter(r => r !== t.dataset.active);
    } else if (t.dataset.partLock) {
      section.parts[t.dataset.partLock].locked = t.checked;
    } else {
      return;
    }
    changed();
    render();
  });

  root.addEventListener('click', e => {
    const t = e.target.closest('button');
    if (!t || busy) return;
    if (t.dataset.select) {
      selected = t.dataset.select;
      render();
      return;
    }
    if (t.hasAttribute('data-move')) {
      const i = Number(t.dataset.move),
        j = i + Number(t.dataset.direction);
      if (doc.sections[j]?.locked || doc.sections[i]?.locked) {
        notify('Unlock the adjacent section before reordering.', true);
        return;
      }
      [doc.sections[i], doc.sections[j]] = [doc.sections[j], doc.sections[i]];
      changed();
      render();
      return;
    }
    run(async () => {
      if (t.dataset.restore) {
        const restored = await api('/revisions/' + t.dataset.restore);
        doc = restored.composition;
        selected = doc.sections[0].id;
        changed();
        notify('Earlier revision loaded into draft. Click Save Draft to make it your active revision.');
        return;
      }
      switch (t.dataset.action) {
        case 'save':
          await save();
          break;
        case 'from-project': {
          const data = await api('/from-project', {bars: 16});
          doc = data.composition;
          revision = data.revision;
          dirty = false;
          cache();
          if (data.created_at) history.push({revision, title: doc.title, created_at: data.created_at});
          const clipInfo = doc.source_clips_used?.length ? ` (extracted real MIDI from ${doc.source_clips_used.length} clip(s))` : '';
          notify(`Imported tempo, key, and tracks from your open Ableton Set${clipInfo} (Revision ${revision}).`);
          break;
        }
        case 'bass-companion': {
          const data = await api('/bass-companion', {
            composition: doc,
            section_id: bassScope === 'selected' ? selected : null,
            key: doc.root_midi,
            scale: doc.mode,
            density: bassDensity,
            movement: bassMovement,
            swing: bassSwing,
            lock_to_kick: true,
          });
          doc = data.composition;
          revision = data.revision;
          dirty = false;
          cache();
          if (data.created_at) history.push({revision, title: doc.title, created_at: data.created_at});
          notify(`Generated kick-locked Bass Companion (${bassDensity}, ${bassMovement.replace('_', ' ')}) in Revision ${revision}.`);
          break;
        }
        case 'fit':
          await save({fit_duration: true});
          break;
        case 'regenerate': {
          const s = doc.sections.find(s => s.id === selected);
          await save({regenerate: {sections: [s.id], roles: s.active_parts}});
          break;
        }
        case 'duplicate': {
          const s = clone(doc.sections.find(s => s.id === selected));
          s.id = 'section-' + crypto.randomUUID();
          s.name += ' variation';
          s.locked = false;
          Object.values(s.parts).forEach(p => (p.locked = false));
          doc.sections.push(s);
          selected = s.id;
          changed();
          notify('Section duplicated at the end of the timeline. Click Save Draft when ready.');
          break;
        }
        case 'copy':
          await navigator.clipboard.writeText(
            `Vibelton Composition Lab revision ${revision}${dirty ? ' (unsaved edits)' : ''}\n${doc.title}\n${doc.brief}\nMood: ${doc.mood}\n${doc.bpm} BPM; target ${doc.target_seconds} seconds.\nSelected section: ${selected}\nRead the current score from GET /api/composition on the local Vibelton server. Preserve locked sections, parts and sounds. Collaborate with me on the musical structure; save revisions before applying. ${dirty ? 'Ask me to save the browser draft first.' : ''}`
          );
          notify('AI brief copied to clipboard.');
          break;
        case 'reload': {
          const data = await api();
          doc = data.composition;
          revision = data.revision;
          history = data.history;
          live = data.live;
          jobs = data.jobs;
          dirty = false;
          cache();
          notify('Restored last saved revision.');
          break;
        }
        case 'refresh': {
          const data = await api();
          live = data.live;
          jobs = data.jobs;
          history = data.history;
          notify('Live MIDI tracks and build status refreshed.');
          break;
        }
        case 'preview':
        case 'build': {
          const job = await api('/apply', {
            revision,
            section_id: t.dataset.action === 'preview' ? selected : null,
            working_copy_confirmed: savedCopy,
          });
          jobs.push(job);
          notify('Sent to Ableton Live! Clips are being placed in a fresh Arrangement section.');
          break;
        }
      }
    });
  });

  window.addEventListener('composition-open', () => {
    savedCopy = getStoredCopyConfirmed();
    if (!doc) load();
    else render();
  });

  setInterval(async () => {
    if (!doc || busy || root.hidden) return;
    try {
      const status = await fetch('/api/status').then(r => r.json());
      live = status.state;
      for (let i = 0; i < jobs.length; i++) {
        if (['Queued', 'Applied'].includes(jobs[i].status)) {
          jobs[i] = await api('/status/' + jobs[i].id);
        }
      }
      const box = root.querySelector('#labJobs');
      if (box) box.innerHTML = jobsHTML();
      const blocked =
        dirty || !revision || !savedCopy || !live.connected || Date.now() / 1000 - live.updated_at > 10 || !live.capabilities?.includes('composition_v1');
      root.querySelectorAll('[data-action="preview"], [data-action="build"]').forEach(b => (b.disabled = blocked));
    } catch {
      /* Keep the last result visible */
    }
  }, 4000);
})();
