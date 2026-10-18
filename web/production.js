(() => {
  const root = document.querySelector('#productionWorkspace');
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const id = () => crypto.randomUUID();
  const short = value => value ? `${String(value).slice(0, 8)}…` : '—';
  const time = seconds => `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`;

  const formatPan = pan => {
    const val = Number(pan || 0);
    if (Math.abs(val) < 0.01) return 'Center';
    const pct = Math.round(Math.abs(val) * 100);
    return val < 0 ? `${pct}% Left` : `${pct}% Right`;
  };
  const formatVol = vol => {
    if (vol === undefined || vol === null || Number.isNaN(Number(vol))) return '—';
    return `${Math.round(Number(vol) * 100)}%`;
  };
  const cleanFileName = raw => {
    if (!raw) return 'Unnamed sample';
    const base = String(raw).split('/').pop().split('\\').pop();
    return base.replace(/\.(wav|aif|aiff|flac|mp3)$/i, '');
  };

  const actionText = action =>
    action.type === 'apply_session_scene_map'
      ? `Append ${action.scenes.length} new Session View scenes and copy your selected clips into each section. Your original scenes stay untouched.`
      : action.type === 'apply_arrangement_copies'
      ? `Place ${action.copies.length} clip copies into a new Arrangement section after your current song. Original clips stay untouched.`
      : action.type === 'apply_session_to_arrangement_copies'
      ? `Place ${action.copies.length} unplaced Session clip(s) onto the Arrangement timeline with verified readback and 1-click undo.`
      : action.type === 'set_device_parameter'
      ? `Adjust device #${action.device_index + 1} parameter #${action.parameter_index + 1} on ${action.target_track_id} to ${Number(action.value).toFixed(2)}.`
      : action.type === 'apply_song_sketch_template'
      ? 'Create the Classic House track layout and set tempo to 124 BPM.'
      : escape(action.type);

  const COPY_STORAGE_KEY = 'vibelton-working-copy-confirmed';
  const getStoredCopyConfirmed = () => sessionStorage.getItem(COPY_STORAGE_KEY) === 'true';
  const setStoredCopyConfirmed = val => {
    copyConfirmed = Boolean(val);
    mixCopyConfirmed = Boolean(val);
    sessionStorage.setItem(COPY_STORAGE_KEY, copyConfirmed ? 'true' : 'false');
    window.dispatchEvent(new CustomEvent('vibelton-copy-confirmed', {detail: copyConfirmed}));
  };

  let page = 'finish',
    analysis,
    overview,
    roles,
    diagnosis,
    options,
    selection,
    plan,
    job,
    originalJob,
    cleanup,
    roleProposal,
    busy = false,
    notice = '',
    isError = false,
    copyConfirmed = getStoredCopyConfirmed(),
    mixCopyConfirmed = getStoredCopyConfirmed(),
    diagnosisVariant = 'club-version',
    roleChoices = {},
    sourceRoles = {},
    sourceClips = {},
    viewChoice = 'session',
    genreChoice = 'House',
    genreTouched = false,
    mixPlan = null,
    mixJob = null,
    deviceTweaks = {},
    devicePlan = null,
    deviceJob = null,
    shuffleResult = null,
    lockedSlots = {},
    slotTargetTracks = {},
    slotImportJobs = {},
    shuffleBpm = null,
    shuffleKey = null,
    pumplabKick = '',
    pumplabBass = '',
    pumplabReport = null,
    refBefore = '',
    refAfter = '',
    refReport = null,
    transcribePath = '',
    transcribeReport = null,
    sliceReport = null,
    autoLoadedRevision = null,
    pollInFlight = false;

  window.addEventListener('vibelton-copy-confirmed', e => {
    copyConfirmed = Boolean(e.detail);
    mixCopyConfirmed = Boolean(e.detail);
  });

  async function api(path, body) {
    const url = path.startsWith('/api/') ? path : '/api/production' + path;
    const response = await fetch(
      url,
      body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}
    );
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request failed');
    return result;
  }

  function setNotice(message, error = false) {
    notice = message;
    isError = error;
    render();
  }

  async function run(work) {
    if (busy) return;
    busy = true;
    render();
    try {
      await work();
    } catch (error) {
      notice = error.message;
      isError = true;
    }
    busy = false;
    render();
  }

  function buildFallbackAnalysis(liveState) {
    const prod = liveState?.production || {};
    const tracks = prod.tracks || liveState?.tracks || [];
    return {
      schema_version: 'vibelton.project-analysis/v1 (cached)',
      source_revision: prod.revision || 'cached',
      session_id: liveState?.session_id || prod.session_id || 'offline',
      is_cached_fallback: true,
      project: {
        tempo: liveState?.tempo || prod.tempo || 120,
        metre: liveState?.metre || prod.metre || [4, 4],
        track_count: tracks.length || liveState?.track_count || 0,
        arrangement_readable: Boolean(liveState?.arrangement_readable || prod.arrangement_readable),
        arrangement_end: liveState?.arrangement_end || 0,
        locators: prod.locators || [],
      },
      tracks,
      missing_measurements: ['audio_render', 'loudness', 'spectrum', 'stereo'],
    };
  }

  const variantsByGenre = {
    'House': [['streaming-edit', 'Streaming edit'], ['club-version', 'Club version'], ['dj-extended-mix', 'DJ extended mix']],
    'Drum & Bass': [['dnb-quick-cut', 'Quick cut'], ['dnb-rolling-club', 'Rolling club'], ['dnb-extended-journey', 'Extended journey']],
    'Techno': [['techno-hypnotic', 'Hypnotic'], ['techno-peak-time', 'Peak time'], ['techno-extended-dj', 'Extended DJ']],
    'UK Garage': [['ukg-compact', 'Compact 2-step'], ['ukg-vocal-club', 'Vocal club'], ['ukg-extended-shuffle', 'Extended shuffle']],
    'Hip Hop': [['hiphop-tight-beat', 'Tight beat'], ['hiphop-verse-hook', 'Verse / hook'], ['hiphop-instrumental', 'Instrumental journey']],
    'Disco / Nu-disco': [['disco-radio-groove', 'Radio groove'], ['disco-club-lift', 'Club lift'], ['disco-extended-mix', 'Extended mix']],
  };
  const bpmRanges = [
    ['Hip Hop', 70, 100],
    ['Disco / Nu-disco', 110, 125],
    ['House', 120, 128],
    ['UK Garage', 125, 135],
    ['Techno', 125, 140],
    ['Drum & Bass', 165, 180],
  ];
  const genreSuggestions = bpm => bpmRanges.filter(([, low, high]) => bpm >= low && bpm <= high).map(([genre]) => genre);
  const defaultVariant = genre => variantsByGenre[genre][1][0];

  function ready() {
    return (
      analysis &&
      !analysis.is_cached_fallback &&
      overview?.live?.connected &&
      Date.now() / 1000 - overview.live.updated_at < 12 &&
      overview.live.capabilities?.includes('production_v1')
    );
  }

  function stale(record) {
    return !record || record.session_id !== analysis?.session_id || record.source_revision !== analysis?.source_revision;
  }

  function autoAssignSourceRoles(currentSelection, currentOptions) {
    if (!currentSelection) return;
    const neededRoles = [...new Set(currentSelection.variant.sections.flatMap(s => s.active_track_roles))];
    const usedRoles = new Set(Object.values(sourceRoles).filter(Boolean));
    const candidates = viewChoice === 'session' ? sessionCandidates() : sourceCandidates();
    const likelyMap = new Map(
      (currentOptions?.role_inventory?.likely_roles || []).map(r => [r.track_id || r.track_name, r.role])
    );

    for (const item of candidates) {
      if (!item.choices || !item.choices.length) continue;
      if (sourceRoles[item.track.id]) continue;
      const confirmedRole = roles?.roles?.[item.track.id];
      const inferredRole =
        confirmedRole ||
        item.track.suggested_role ||
        likelyMap.get(item.track.id) ||
        likelyMap.get(item.track.name);
      if (inferredRole && neededRoles.includes(inferredRole) && !usedRoles.has(inferredRole)) {
        sourceRoles[item.track.id] = inferredRole;
        usedRoles.add(inferredRole);
      }
    }
  }

  async function ensurePageDefaults() {
    if (page === 'samples' && !shuffleResult) {
      try {
        const bpm = shuffleBpm || Number(analysis?.project?.tempo) || 119;
        const key = shuffleKey || 'Ab';
        shuffleResult = await api('/api/samples/shuffle', {target_bpm: bpm, target_key: key, locked_slots: lockedSlots});
      } catch {
        // Ignore silent auto-load error
      }
    }
    if (!ready()) return;
    try {
      if (page === 'finish' && (!diagnosis || stale(diagnosis))) {
        diagnosis = await api('/finish-diagnosis', {
          template_variant_id: diagnosisVariant,
          expected_revision: analysis.source_revision,
        });
      } else if (page === 'arrange' && (!options || stale(options))) {
        options = await api('/arrangement-options', {request_id: id(), genre: genreChoice});
      } else if (page === 'mix' && (!mixPlan || stale(mixPlan))) {
        mixPlan = await api('/mix-balance-proposal', {request_id: id()});
      }
    } catch {
      // Keep interactive button available if auto-fetch fails
    }
  }

  async function refresh() {
    overview = await api('');
    try {
      [analysis, roles] = await Promise.all([api('/analysis'), api('/track-roles')]);
    } catch {
      analysis = buildFallbackAnalysis(overview?.live || {});
      roles = roles || {active: false, roles: {}};
    }
    if (!genreTouched && analysis?.project?.tempo) {
      const matches = genreSuggestions(Number(analysis.project.tempo));
      if (matches.length === 1 && genreChoice !== matches[0]) {
        genreChoice = matches[0];
        diagnosisVariant = defaultVariant(genreChoice);
        diagnosis = null;
        options = null;
        selection = null;
      }
    }
    if (plan && !analysis.is_cached_fallback && (plan.session_id !== analysis.session_id || plan.source_revision !== analysis.source_revision)) {
      notice = 'The Ableton Set changed since this plan was drafted. Review a fresh plan before applying.';
      isError = true;
    }
    if (autoLoadedRevision !== analysis?.source_revision) {
      autoLoadedRevision = analysis?.source_revision;
      await ensurePageDefaults();
    }
  }

  function statusStepper(currentStage) {
    const stages = [
      ['draft', '1. Review Plan'],
      ['confirm', '2. Confirm Working Copy'],
      ['applied', '3. Applied in Live'],
      ['audition', '4. Listen & Keep or Undo'],
    ];
    const activeIdx = stages.findIndex(([k]) => k === currentStage);
    return `<div class="prod-stepper" aria-label="Action progress">
      ${stages.map(([, label], idx) => `<span class="prod-step ${idx < activeIdx ? 'is-done' : idx === activeIdx ? 'is-current' : ''}">${label}</span>`).join('<span class="prod-step-arrow">→</span>')}
    </div>`;
  }

  function genreControls(showCompareVariant = false) {
    const bpm = Number(analysis?.project?.tempo || 120);
    const matches = genreSuggestions(bpm);
    const hint = matches.length === 1
      ? `Matches your Set's ${bpm} BPM`
      : matches.length
      ? `${bpm} BPM fits: ${matches.join(', ')}`
      : `${bpm} BPM (custom tempo)`;
    return `<div class="prod-context-controls">
      <label class="prod-inline-field">
        <span>Style Reference</span>
        <select id="productionGenre">${Object.keys(variantsByGenre).map(genre => `<option value="${escape(genre)}" ${genreChoice === genre ? 'selected' : ''}>${escape(genre)}</option>`).join('')}</select>
      </label>
      ${showCompareVariant ? `<label class="prod-inline-field">
        <span>Target Structure</span>
        <select id="diagnosisVariant">${variantsByGenre[genreChoice].map(([value, label]) => `<option value="${value}" ${diagnosisVariant === value ? 'selected' : ''}>${label}</option>`).join('')}</select>
      </label>` : ''}
      <span class="prod-context-hint">${escape(hint)}</span>
    </div>`;
  }

  function header() {
    const p = analysis?.project || {}, live = overview?.live || {};
    const isConnected = ready();
    const activeTracks = (analysis?.tracks || []).filter(t => !t.is_group);
    const placedTracks = activeTracks.filter(t => t.arrangement_clips?.length).length;
    const confirmedCount = Object.values(roles?.roles || {}).filter(Boolean).length;

    return `<div class="prod-statusbar">
      <div class="prod-statusbar-main">
        <div class="prod-live-pill ${isConnected ? 'is-live' : 'is-offline'}">
          <span class="prod-led"></span>
          <strong>${isConnected ? 'Ableton Live Connected' : 'Live Offline (Viewing Saved Snapshot)'}</strong>
        </div>
        <div class="prod-QuickFacts">
          <span><strong>${p.tempo ?? '—'} BPM</strong> · ${p.metre?.join('/') || '4/4'}</span>
          <span><strong>${p.track_count ?? '—'}</strong> tracks (${placedTracks} in Arrangement)</span>
          <span>Roles: <strong>${roles?.active ? `${confirmedCount} confirmed` : 'Auto-detected'}</strong></span>
        </div>
      </div>
      <div class="prod-statusbar-actions">
        <label class="prod-safety-toggle" title="Check this once you have saved your Set under a working copy name (File → Save Live Set As)">
          <input id="globalWorkingCopy" type="checkbox" ${copyConfirmed ? 'checked' : ''} />
          <span>Working copy saved</span>
        </label>
        <button class="prod-btn-ghost" data-action="refresh" ${busy ? 'disabled' : ''}>↻ Refresh Set</button>
        <details class="prod-tech-popover">
          <summary>Technical Info</summary>
          <div class="prod-tech-popover-body">
            <div><span>Connection:</span> <strong>${isConnected ? 'Active heartbeat' : 'Disconnected / Cached'}</strong></div>
            <div><span>Bridge version:</span> <strong>${escape(live.bridge_version || 'Unavailable')}</strong></div>
            <div><span>Session ID:</span> <strong title="${escape(analysis?.session_id)}">${short(analysis?.session_id)}</strong></div>
            <div><span>Source revision:</span> <strong title="${escape(analysis?.source_revision)}">${short(analysis?.source_revision)}</strong></div>
            <div><span>Capabilities:</span> <strong>${escape((live.capabilities || []).join(', ') || 'None')}</strong></div>
            <div><span>Arrangement readback:</span> <strong>${p.arrangement_readable ? 'Readable' : 'Limited'}</strong></div>
          </div>
        </details>
      </div>
    </div>
    ${!isConnected ? `<div class="prod-offline-banner">
      <strong>Ableton Live is not currently sending a live heartbeat.</strong>
      <span>You can still explore your last saved Set snapshot, roll loops in <strong>Loop Finder</strong>, or run audio checks in <strong>Low-End &amp; Reference</strong>. Open Ableton Live to apply changes.</span>
    </div>` : ''}`;
  }

  function findingActionButton(f) {
    const code = f.code || '';
    if (code === 'unplaced_session_material') {
      return `<button class="prod-primary" data-action="draft-session-to-arrangement" ${!ready() || busy ? 'disabled' : ''}>Draft Session-to-Arrangement Plan →</button> <button data-goto="arrange" data-view="session">Place Session Clips in Arrange →</button>`;
    }
    if (code === 'incomplete_sections' || code === 'weak_section_contrast') {
      return `<button class="prod-primary" data-goto="arrange">Open Arrangement Shapes →</button>`;
    }
    if (code === 'repeated_material') {
      return `<button class="prod-primary" data-goto-mode="composition">Vary Phrases in Compose MIDI →</button> <button data-goto="arrange">Review Arrangement →</button>`;
    }
    if (code === 'missing_roles' || code === 'unclear_track_roles') {
      return `<button class="prod-primary" data-goto="prepare" data-auto="roles">Confirm Track Roles →</button>`;
    }
    if (code === 'empty_unused_tracks') {
      return `<button class="prod-primary" data-goto="mix">Open Mix Balance (Skips Empty Tracks) →</button>`;
    }
    if (code === 'arrangement_unreadable') {
      return `<button data-action="refresh">Refresh Set Readback</button>`;
    }
    return `<button data-goto="arrange">Explore Arrangement Options →</button>`;
  }

  function finish() {
    const p = analysis?.project || {};
    const tracks = analysis?.tracks || [];
    const arrTracks = tracks.filter(t => t.arrangement_clips?.length).length;
    const sessOnlyTracks = tracks.filter(t => (t.session_clips?.length || t.clips?.length) && !t.arrangement_clips?.length).length;

    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">STEP 1 · TRACK HEALTH &amp; NEXT STEPS</p>
        <h3>What your Set needs right now</h3>
        <p>Vibelton inspects your track structure, clip placement, and roles so you can jump straight to the highest-impact improvement.</p>
      </div>
      <div class="prod-intro-actions">
        ${genreControls(true)}
        <button class="prod-primary" data-action="diagnose" ${!ready() || busy ? 'disabled' : ''}>↻ Re-check Track</button>
      </div>
    </div>

    <div class="prod-summary-cards">
      <article class="prod-summary-card">
        <span class="prod-kicker">ARRANGEMENT</span>
        <strong>${arrTracks} tracks placed</strong>
        <p>${sessOnlyTracks ? `${sessOnlyTracks} track${sessOnlyTracks === 1 ? ' has' : 's have'} unplaced Session clips ready to arrange.` : 'All active clip tracks are represented in the timeline.'}</p>
        <div class="prod-card-btn-row">
          <button data-goto="arrange">Go to Arrange →</button>
          ${sessOnlyTracks ? `<button class="prod-primary" data-action="draft-session-to-arrangement" ${!ready() || busy ? 'disabled' : ''}>Place Session Clips →</button>` : ''}
        </div>
      </article>
      <article class="prod-summary-card">
        <span class="prod-kicker">MIX &amp; ROLES</span>
        <strong>${roles?.active ? 'Roles confirmed' : 'Roles auto-detected'}</strong>
        <p>Anchor Kick, Bass, and Vocal levels with automatic stereo headroom and instant snapshot undo.</p>
        <button data-goto="mix">Go to Mix Balance →</button>
      </article>
      <article class="prod-summary-card">
        <span class="prod-kicker">LOOPS &amp; LOW-END</span>
        <strong>${p.tempo ?? 120} BPM · ${p.metre?.join('/') || '4/4'}</strong>
        <p>Curate 4 non-clashing sample loops or check your Kick and Bass for sub-bass phase cancellation.</p>
        <div class="prod-card-btn-row">
          <button data-goto="samples">Loop Finder →</button>
          <button data-goto="pumplab">Low-End Check →</button>
        </div>
      </article>
    </div>

    ${plan && plan.workflow === 'session_to_arrangement' ? planView() : ''}

    ${diagnosis ? `<div class="prod-divider">
      <div class="prod-section-header">
        <div>
          <p class="prod-kicker">PRIORITIZED RECOMMENDATIONS · ${escape(diagnosis.genre)} (${escape(diagnosis.template_variant_id.replaceAll('-', ' '))})</p>
          <h4>Top ${diagnosis.findings.length} areas to review</h4>
        </div>
      </div>
      <div class="prod-findings-list">
        ${diagnosis.findings.map((f, i) => `<article class="prod-finding-card">
          <div class="prod-finding-num">0${i + 1}</div>
          <div class="prod-finding-body">
            <div class="prod-row">
              <h4>${escape(f.observation)}</h4>
              <span class="prod-pill">${escape(f.confidence)} confidence</span>
            </div>
            <p>${escape(f.musical_importance)}</p>
            <div class="prod-next-bar">
              <div>
                <span class="prod-next-label">Recommended next step:</span>
                <strong>${escape(f.suggested_next_action)}</strong>
              </div>
              <div class="prod-next-actions">
                ${findingActionButton(f)}
              </div>
            </div>
            <details class="prod-tech-details">
              <summary>Technical evidence &amp; assumptions</summary>
              <dl>${Object.entries(f.evidence || {}).map(([k, v]) => `<div><dt>${escape(k.replaceAll('_', ' '))}</dt><dd>${escape(Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : v)}</dd></div>`).join('')}</dl>
              ${f.assumptions?.length ? `<p class="prod-footnote">Assumptions: ${f.assumptions.map(escape).join(' ')}</p>` : ''}
            </details>
          </div>
        </article>`).join('')}
      </div>
    </div>` : `<div class="prod-card">
      <h4>Ready to inspect your Set</h4>
      <p>${ready() ? 'Click <strong>Re-check Track</strong> above to generate a prioritized checklist for your open Set.' : 'Connect Ableton Live to run a live structural diagnosis, or use the cards above to explore Arrange, Mix Balance, Loop Finder, and Low-End Check.'}</p>
    </div>`}`;
  }

  function arrangementHistory() {
    const plans = new Map((overview?.plans || []).map(p => [p.id, p]));
    const jobs = (overview?.jobs || [])
      .filter(j => j.session_id === analysis?.session_id && !j.rollback_of && plans.get(j.plan_id)?.actions?.some(a => ['apply_arrangement_copies', 'apply_session_scene_map', 'apply_session_to_arrangement_copies'].includes(a.type)))
      .slice(-5)
      .reverse();
    return jobs.length
      ? `<details class="prod-card prod-history-details">
          <summary><strong>Recent arrangement builds in this session (${jobs.length})</strong></summary>
          <div class="prod-history-list">
            ${jobs.map(j => `<div class="prod-history"><span><strong>${escape(j.status)}</strong> · Job ${short(j.id)}${j.execution?.created_copies ? ` · ${j.execution.created_copies.length} clips placed` : ''}${j.execution?.created_scenes ? ` · ${j.execution.created_scenes.length} scenes created` : ''}</span><button data-action="view-job" data-job="${escape(j.id)}">View / Undo</button></div>`).join('')}
          </div>
        </details>`
      : '';
  }

  function sourceCandidates() {
    return (analysis?.tracks || [])
      .map(track => {
        const clips = (track.arrangement_clips || []).filter(
          c => c.fingerprint && c.length >= 4 && c.length <= 64 && Math.abs(c.end_beat - c.start_beat - c.length) < 0.00001 && Math.abs(c.length / 4 - Math.round(c.length / 4)) < 0.00001
        );
        clips.sort((a, b) => (a.length > 32) - (b.length > 32) || b.length - a.length || a.start_beat - b.start_beat);
        const choices = clips.slice(0, 12);
        return clips.length ? {track, clip: choices.find(c => String(c.start_beat) === sourceClips[track.id]) || choices[0], choices} : null;
      })
      .filter(Boolean);
  }

  function sessionCandidates() {
    return (analysis?.tracks || []).map(track => {
      const live = (overview?.live?.tracks || [])[track.index] || {};
      const clips = (track.session_clips?.length ? track.session_clips : live.clips || []).filter(c => Number.isInteger(c.scene_index));
      const selected = clips.find(c => String(c.scene_index) === sourceClips[track.id]) || clips[0];
      return {track, clip: selected, choices: clips};
    });
  }

  function renderSourceRow({track, clip, choices}, rolesList, isSession) {
    const assignedRole = sourceRoles[track.id] || '';
    const hasClips = choices && choices.length > 0;
    const subtext = isSession
      ? hasClips
        ? `${choices.length} clip${choices.length === 1 ? '' : 's'} · Using "${clip.name}" (Scene ${clip.scene_index + 1})`
        : 'No Session clips on this track'
      : `Using "${clip.name}" · Bar ${Math.round(clip.start_beat / 4) + 1} (${Math.round(clip.length / 4)} bars)`;

    return `<div class="prod-role-row ${assignedRole ? 'is-assigned' : ''}">
      <span>
        <strong>${escape(track.name)} ${assignedRole ? `<span class="prod-pill">${escape(assignedRole)}</span>` : ''}</strong>
        <small>${escape(subtext)}</small>
      </span>
      <div class="prod-source-controls">
        <label>Role
          <select data-source-track="${escape(track.id)}" ${hasClips ? '' : 'disabled'}>
            <option value="">Do not use</option>
            ${rolesList.map(role => `<option value="${escape(role)}" ${assignedRole === role ? 'selected' : ''}>${escape(role)}</option>`).join('')}
          </select>
        </label>
        <label>Source clip
          <select data-source-clip="${escape(track.id)}" ${hasClips ? '' : 'disabled'}>
            ${hasClips
              ? choices.map(c => isSession
                  ? `<option value="${c.scene_index}" ${c.scene_index === clip.scene_index ? 'selected' : ''}>${escape(c.name)} · Scene ${c.scene_index + 1}${c.length ? ` (${Math.round(c.length / 4)} bars)` : ''}</option>`
                  : `<option value="${c.start_beat}" ${c.start_beat === clip.start_beat ? 'selected' : ''}>${escape(c.name)} · Bar ${Math.round(c.start_beat / 4) + 1} (${Math.round(c.length / 4)} bars)</option>`
                ).join('')
              : '<option>No clips</option>'}
          </select>
        </label>
      </div>
    </div>`;
  }

  function sourcePicker() {
    if (!selection) return '';
    const rolesList = [...new Set(selection.variant.sections.flatMap(s => s.active_track_roles))];
    const chosenRoles = Object.values(sourceRoles).filter(Boolean);
    const repeatedRole = new Set(chosenRoles).size !== chosenRoles.length;
    const isSession = viewChoice === 'session';
    const allCandidates = isSession ? sessionCandidates() : sourceCandidates();
    const activeCandidates = allCandidates.filter(c => c.choices?.length && sourceRoles[c.track.id]);
    const otherCandidates = allCandidates.filter(c => !sourceRoles[c.track.id]);

    return `<div class="prod-review">
      <div class="prod-row">
        <div>
          <p class="prod-kicker">STEP 2 · ASSIGN TRACKS TO ROLES (${escape(selection.variant.name)})</p>
          <h4>${isSession ? 'Choose clips for your new Session scenes' : 'Choose clips to place on the Arrangement timeline'}</h4>
          <p>Vibelton pre-matched your tracks below. Adjust any role or clip, then click <strong>Preview Placement Plan</strong>.</p>
        </div>
        <button data-action="auto-assign-sources" ${busy ? 'disabled' : ''}>✨ Auto-Match Tracks</button>
      </div>

      ${isSession && !overview?.live?.capabilities?.includes('session_scene_v1')
        ? '<p class="prod-warning">Note: Session scene building requires the updated Live bridge capability (session_scene_v1).</p>'
        : ''}

      ${activeCandidates.length ? `
        <div class="prod-table">
          ${activeCandidates.map(c => renderSourceRow(c, rolesList, isSession)).join('')}
        </div>
      ` : `<p class="prod-warning">No tracks are assigned to a role yet. Click <strong>Auto-Match Tracks</strong> or assign a track from the list below.</p>`}

      ${otherCandidates.length ? `
        <details class="prod-more-tracks" ${activeCandidates.length === 0 ? 'open' : ''}>
          <summary>Show ${otherCandidates.length} unassigned or empty tracks</summary>
          <div class="prod-table">
            ${otherCandidates.map(c => renderSourceRow(c, rolesList, isSession)).join('')}
          </div>
        </details>
      ` : ''}

      ${repeatedRole ? '<p class="prod-warning">Each role should only be assigned to one track. Remove the duplicate role above to continue.</p>' : ''}

      <div class="prod-actionline" style="margin-top:18px">
        <button class="prod-primary" data-action="arrangement-plan" ${!chosenRoles.length || repeatedRole || stale(selection) || busy || (isSession && !overview?.live?.capabilities?.includes('session_scene_v1')) ? 'disabled' : ''}>
          Preview Placement Plan (${chosenRoles.length} role${chosenRoles.length === 1 ? '' : 's'} assigned) →
        </button>
        <span class="prod-footnote">${isSession ? 'Appends 7 new scenes below your existing scenes.' : 'Places copies after your current Arrangement without overwriting existing clips.'}</span>
      </div>
    </div>`;
  }

  function arrange() {
    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">STEP 2 · ARRANGE TRACK</p>
        <h3>Turn your loops into a full song structure</h3>
        <p>Pick a structural map below, verify which tracks play in each section, and build it safely in Session View or on the Arrangement timeline.</p>
      </div>
      <div class="prod-intro-actions">
        ${genreControls(false)}
        <label class="prod-inline-field">
          <span>Build In</span>
          <select id="arrangementView">
            <option value="session" ${viewChoice === 'session' ? 'selected' : ''}>Session View (7 new scenes)</option>
            <option value="arrangement" ${viewChoice === 'arrangement' ? 'selected' : ''}>Arrangement Timeline (after current song)</option>
          </select>
        </label>
        <button data-action="options" ${!ready() || busy ? 'disabled' : ''}>↻ Load ${escape(genreChoice)} Maps</button>
      </div>
    </div>

    ${options ? `
      <div class="prod-option-grid">
        ${options.variants.map((v, idx) => {
          const isChosen = selection?.variant?.id === v.id;
          return `<article class="prod-option ${isChosen ? 'chosen' : ''}">
            <div class="prod-row">
              <span class="prod-pill">${escape(v.name)} ${idx === 1 ? '· Recommended' : ''}</span>
              <strong>${v.total_bars} bars · ~${time(v.approximate_duration_seconds)}</strong>
            </div>
            <div class="prod-timeline" title="Section energy profile">
              ${v.sections.map(s => `<div title="${escape(s.name)}: ${s.bar_count} bars · Energy ${s.energy_level}/10" style="flex:${s.bar_count};--energy:${s.energy_level}"></div>`).join('')}
            </div>
            <div class="prod-sections">
              ${v.sections.map(s => `<div><span>Bars ${s.start_bar + 1}–${s.end_bar}</span><strong>${escape(s.name)}</strong><i>Energy ${s.energy_level}/10</i><small>${escape(s.active_track_roles.join(', '))}</small></div>`).join('')}
            </div>
            <button class="${isChosen ? '' : 'prod-primary'}" data-action="select" data-variant="${escape(v.id)}" ${stale(options) || busy ? 'disabled' : ''}>
              ${isChosen ? '✓ Selected Shape' : 'Choose This Shape →'}
            </button>
          </article>`;
        }).join('')}
      </div>
      <details class="prod-tech-details" style="margin-top:14px">
        <summary>Source material &amp; role inventory details</summary>
        <p>${options.role_inventory.material_summary.arrangement_or_session_clip_count} clips detected across your Set. Identified roles: ${options.role_inventory.likely_roles.map(r => escape(`${r.role} (${r.track_name})`)).join(' · ') || 'None yet'}.</p>
        ${options.role_inventory.missing_roles.length ? `<p>Unassigned template roles (will leave open space for you to fill later): ${escape(options.role_inventory.missing_roles.join(', '))}.</p>` : ''}
      </details>
    ` : `<div class="prod-card">
      <h4>Load ${escape(genreChoice)} Arrangement Shapes</h4>
      <p>${ready() ? `Click <strong>Load ${escape(genreChoice)} Maps</strong> above to preview three bar-by-bar structures.` : 'Connect Ableton Live to generate arrangement maps matched to your Set.'}</p>
    </div>`}

    ${selection ? sourcePicker() : ''}
    ${plan?.arrangement_selection_id ? planView() : ''}
    ${arrangementHistory()}`;
  }

  function planView() {
    const session = plan.view === 'session';
    const currentStage = job?.status === 'Applied' ? 'audition' : job?.status === 'Queued' ? 'applied' : copyConfirmed ? 'confirm' : 'draft';
    return `<div class="prod-review prod-plan-card">
      ${statusStepper(currentStage)}
      <p class="prod-kicker">STEP 3 · CONFIRM &amp; SEND TO ABLETON LIVE</p>
      <h4>${escape(plan.intent)}</h4>
      <p>${session
        ? `Creates 7 new Session scenes starting at Scene ${plan.first_new_scene}. Your existing scenes stay untouched above them.`
        : plan.start_bar
        ? `Places your clips into a fresh Arrangement section from Bar ${plan.start_bar} to Bar ${plan.actual_end_bar}. Your existing timeline stays untouched.`
        : ''}</p>
      <ul class="prod-plan-summary-list">
        ${plan.actions.map(a => `<li>${actionText(a)}</li>`).join('')}
      </ul>
      ${plan.source_coverage?.length ? `<details class="prod-tech-details">
        <summary>View section-by-section clip placements (${plan.source_coverage.length} placements)</summary>
        <div class="prod-table">
          ${plan.source_coverage.map(c => `<div class="prod-role-row"><span><strong>${escape(c.section)} · ${escape(c.role)}</strong><small>${escape(c.source_name)} from ${escape(c.track_name)} (source ${session ? 'scene' : 'bar'} ${session ? c.source_scene : c.source_bar})</small></span>${session ? '' : `<span>Bar ${c.destination_bar} (${c.placed_bars} bars)</span>`}</div>`).join('')}
        </div>
      </details>` : ''}
      ${plan.gaps?.length ? `<details class="prod-tech-details"><summary>Open spaces / unfilled roles (${plan.gaps.length})</summary><p class="prod-footnote">${plan.gaps.map(escape).join(' · ')}</p></details>` : ''}
      ${plan.warnings?.map(w => `<p class="prod-warning">${escape(w)}</p>`).join('') || ''}

      <label class="prod-check">
        <input id="workingCopy" type="checkbox" ${copyConfirmed ? 'checked' : ''} />
        <span>I saved and opened a working copy in Ableton Live (my original Set is safe).</span>
      </label>
      <div class="prod-actionline">
        <button class="prod-primary" data-action="apply" ${!copyConfirmed || stale(plan) || plan.status !== 'Draft' || busy || (session && !overview?.live?.capabilities?.includes('session_scene_v1')) || (plan.start_bar && !overview?.live?.capabilities?.includes('arrangement_copy_v2')) ? 'disabled' : ''}>
          Apply to Ableton Live
        </button>
        ${!copyConfirmed ? '<span class="prod-warning">↑ Check the working copy box above to enable Apply.</span>' : ''}
      </div>
    </div>${jobView()}`;
  }

  function jobView() {
    if (!job) return '';
    const result = job.execution || {};
    const isApplied = job.status === 'Applied';
    const isQueued = job.status === 'Queued';
    return `<div class="prod-job ${isApplied ? 'is-success' : ''}">
      <div class="prod-row">
        <div>
          <p class="prod-kicker">LIVE EXECUTION STATUS</p>
          <h4>${isApplied ? '✅ Applied in Ableton Live — Ready to Listen' : isQueued ? '⏳ Sending to Ableton Live…' : escape(job.status)}</h4>
        </div>
        <span class="prod-pill">${escape(job.status)}</span>
      </div>
      <p>${result.error
        ? escape(result.error)
        : isQueued
        ? 'Waiting for Ableton Live to finish placing clips and verify readback…'
        : `Completed ${result.completed_actions ?? 1} action(s) with verified readback in Ableton Live.`}</p>
      ${result.created_copies ? `<p class="prod-footnote">${result.created_copies.length} clip copies recorded in safety snapshot for 1-click undo.</p>` : ''}
      ${result.created_scenes ? `<p class="prod-footnote">${result.created_scenes.length} Session scenes recorded in safety snapshot for 1-click undo.</p>` : ''}
      <div class="prod-next-bar" style="margin-top:12px">
        <div>
          <span class="prod-next-label">What to do next:</span>
          <strong>${isApplied ? 'Audition the new section in Ableton Live. Keep it, or click Undo Changes to restore your Set.' : 'Click Refresh Status if Ableton Live just finished.'}</strong>
        </div>
        <div class="prod-next-actions">
          <button data-action="job-status" ${busy ? 'disabled' : ''}>↻ Refresh Status</button>
          ${originalJob && ['Applied', 'Partial failure'].includes(originalJob.status) ? `<button data-action="rollback" ${!copyConfirmed || busy ? 'disabled' : ''}>↩ Undo Recorded Changes</button>` : ''}
        </div>
      </div>
      ${job.rollback_of ? `<p class="prod-footnote">Undo job for ${short(job.rollback_of)} · Status: ${escape(job.status)}</p>` : ''}
    </div>`;
  }

  function prepare() {
    const allProposed = roleProposal?.tracks || [];
    const activeProposed = allProposed.filter(t => !t.context?.is_empty);
    const emptyProposed = allProposed.filter(t => t.context?.is_empty);

    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">PROJECT SETUP &amp; ROLES</p>
        <h3>Confirm track roles &amp; project templates</h3>
        <p>Confirming what each track does (Kick, Bass, Vocal, Chords, Percussion) helps Arrange and Mix Balance make smarter decisions without renaming your tracks in Live.</p>
      </div>
      <button class="prod-primary" data-action="roles" ${!ready() || busy ? 'disabled' : ''}>Review &amp; Confirm Track Roles</button>
    </div>

    <div class="prod-card">
      <div class="prod-row">
        <div>
          <span class="prod-pill">${roles?.active ? '✓ Confirmed for this Set' : 'Recommended Step'}</span>
          <h4>Track Role Mapping</h4>
          <p>Review Vibelton's detected roles for your tracks. Confirming roles never alters or renames your tracks in Ableton.</p>
        </div>
        <button class="prod-primary" data-action="roles" ${!ready() || busy ? 'disabled' : ''}>${roleProposal ? '↻ Reload Roles' : 'Review Track Roles'}</button>
      </div>
    </div>

    ${roleProposal ? `<div class="prod-review">
      <div class="prod-row">
        <div>
          <p class="prod-kicker">CONFIRM ROLES · ${activeProposed.length} ACTIVE TRACKS</p>
          <h4>Verify detected roles</h4>
        </div>
        <button class="prod-primary" data-action="confirm-roles" ${stale(roleProposal) || busy ? 'disabled' : ''}>✓ Save Confirmed Roles</button>
      </div>
      <div class="prod-table">
        ${activeProposed.map(t => `<label class="prod-role-row">
          <span>
            <strong>${escape(t.context.name)}</strong>
            <small>${escape(t.reason)}</small>
          </span>
          <select data-track-id="${escape(t.track_id)}">
            ${['', ...t.options.filter(o => o !== 'Unknown / leave unchanged')].map(v => `<option value="${escape(v)}" ${v === (roleChoices[t.track_id] ?? t.suggested_role) ? 'selected' : ''}>${escape(v || 'Unknown / leave unchanged')}</option>`).join('')}
          </select>
        </label>`).join('')}
      </div>
      ${emptyProposed.length ? `<details class="prod-more-tracks">
        <summary>Empty placeholder tracks (${emptyProposed.length}) — left as Unknown</summary>
        <div class="prod-table">
          ${emptyProposed.map(t => `<label class="prod-role-row">
            <span><strong>${escape(t.context.name)}</strong><small>Empty track (no clips or instruments)</small></span>
            <select data-track-id="${escape(t.track_id)}">
              ${['', ...t.options.filter(o => o !== 'Unknown / leave unchanged')].map(v => `<option value="${escape(v)}" ${v === (roleChoices[t.track_id] ?? t.suggested_role) ? 'selected' : ''}>${escape(v || 'Unknown / leave unchanged')}</option>`).join('')}
            </select>
          </label>`).join('')}
        </div>
      </details>` : ''}
      <div class="prod-actionline" style="margin-top:16px">
        <button class="prod-primary" data-action="confirm-roles" ${stale(roleProposal) || busy ? 'disabled' : ''}>✓ Save Confirmed Roles</button>
      </div>
    </div>` : ''}

    <details class="prod-card" style="margin-top:22px">
      <summary><strong>More Project Tools: Blank Set Starter Template &amp; Name Cleanup Preview</strong></summary>
      <div class="prod-two" style="margin-top:16px">
        <article class="prod-card" style="margin-top:0">
          <span class="prod-pill">NEW BLANK SET ONLY</span>
          <h4>Classic House · 124 BPM Starter Layout</h4>
          <p>Sets up a fresh 124 BPM, 4/4 House track layout. Requires a brand-new, untouched Ableton Set.</p>
          <button data-action="template" ${!ready() || busy ? 'disabled' : ''}>Draft Starter Template</button>
        </article>
        <article class="prod-card" style="margin-top:0">
          <span class="prod-pill">READ-ONLY PREVIEW</span>
          <h4>Track Naming &amp; Organization Suggestions</h4>
          <p>Preview suggested track names and roles for messy sessions without changing Live.</p>
          <button data-action="cleanup" ${!ready() || busy ? 'disabled' : ''}>Preview Naming Suggestions</button>
        </article>
      </div>
    </details>

    ${cleanup ? `<div class="prod-review">
      <p class="prod-kicker">TRACK NAMING PREVIEW (READ-ONLY)</p>
      <p>${escape(cleanup.reason)}</p>
      <div class="prod-table">
        ${cleanup.tracks.map(t => `<div class="prod-role-row"><span><strong>${escape(t.current_name)} → ${escape(t.suggested_name || 'Keep current name')}</strong><small>${escape(t.reason)}</small></span><span class="prod-pill">${escape(t.role || 'Unknown')}</span></div>`).join('')}
      </div>
    </div>` : ''}
    ${plan && !plan.arrangement_selection_id ? planView() : ''}`;
  }

  function mixAssistant() {
    const actions = mixPlan?.actions || [];
    const summaryMap = new Map((mixPlan?.role_balance_summary || []).map(item => [item.track_id, item]));
    const skipped = mixPlan?.skipped_empty_tracks || [];
    const currentStage = mixJob?.status === 'Applied' ? 'audition' : mixJob?.status === 'Queued' ? 'applied' : mixCopyConfirmed ? 'confirm' : 'draft';
    const tracksWithDevices = (analysis?.tracks || []).filter(t => !t.is_group && Array.isArray(t.devices) && t.devices.length > 0);
    const pendingDeviceCount = Object.keys(deviceTweaks).length;

    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">STEP 4 · MIX BALANCE &amp; DEVICE MACROS</p>
        <h3>Clean starting levels, stereo headroom, spatial sends &amp; device macros</h3>
        <p>Balances your active tracks by musical role—anchoring Kick (-6.0 dB, 100% dry), Bass (-7.5 dB, 100% dry), and Vocals (-6.5 dB) dead-center while opening stereo and Send A/B space for Chords, Leads, and Percussion. Empty tracks are skipped automatically.</p>
      </div>
      <button class="prod-primary" data-action="draft-mix" ${!ready() || busy ? 'disabled' : ''}>${mixPlan ? '↻ Recalculate Mix Plan' : 'Draft Mix Balance Plan'}</button>
    </div>

    ${mixPlan ? `
    <div class="prod-review">
      ${statusStepper(currentStage)}
      <div class="prod-row">
        <div>
          <p class="prod-kicker">PROPOSED MIXER &amp; SEND ADJUSTMENTS · ${actions.length} ACTIVE TRACKS</p>
          <h4>Review level, panning &amp; Send A/B changes</h4>
        </div>
        <span class="prod-pill">${escape(mixPlan.status)}</span>
      </div>

      <div class="prod-table">
        ${actions.map(a => {
          const tr = (analysis?.tracks || []).find(t => t.id === a.target_track_id);
          const summary = summaryMap.get(a.target_track_id);
          const name = tr?.name || summary?.track_name || a.target_track_id;
          const role = summary?.role || roles?.roles?.[a.target_track_id] || tr?.suggested_role || 'Active Track';
          const curVol = formatVol(tr?.mixer?.volume);
          const curPan = formatPan(tr?.mixer?.pan);
          const curSends = Array.isArray(tr?.mixer?.sends) ? tr.mixer.sends : [];
          const curSendText = curSends.length ? ` · Send A ${formatVol(curSends[0])}${curSends.length > 1 ? ` · Send B ${formatVol(curSends[1])}` : ''}` : '';
          const targetVol = formatVol(a.values.volume);
          const targetPan = formatPan(a.values.pan);
          const targetSendA = a.values.send_0 !== undefined ? ` · Send A: ${formatVol(a.values.send_0)}` : '';
          const targetSendB = a.values.send_1 !== undefined ? ` · Send B: ${formatVol(a.values.send_1)}` : '';
          const targetDb = summary?.after?.target_db !== undefined ? `${summary.after.target_db.toFixed(1)} dB anchor` : '';
          return `<div class="prod-role-row">
            <span>
              <strong>${escape(name)} <span class="prod-pill">${escape(role)}</span></strong>
              <small>Current: Level ${curVol} · Pan ${curPan}${curSendText}</small>
            </span>
            <span class="prod-mix-target">
              <strong>Level ${targetVol} ${targetDb ? `<small>(${targetDb})</small>` : ''}</strong>
              <small>Pan: ${targetPan}${targetSendA}${targetSendB}</small>
            </span>
          </div>`;
        }).join('')}
      </div>

      ${skipped.length ? `<details class="prod-tech-details">
        <summary>Skipped ${skipped.length} empty placeholder tracks (left untouched)</summary>
        <p class="prod-footnote">${escape(skipped.map(s => s.name || s.track_id).join(', '))}</p>
      </details>` : ''}

      <label class="prod-check">
        <input id="mixWorkingCopy" type="checkbox" ${mixCopyConfirmed ? 'checked' : ''} />
        <span>I saved and opened a working copy in Ableton Live (my original Set is safe).</span>
      </label>
      <div class="prod-actionline">
        <button class="prod-primary" data-action="apply-mix" ${!mixCopyConfirmed || busy ? 'disabled' : ''}>Apply Mix Balance to Live</button>
        ${mixJob && ['Applied', 'Partial failure'].includes(mixJob.status) ? `<button data-action="rollback-mix" ${!mixCopyConfirmed || busy ? 'disabled' : ''}>↩ Undo Mix Changes</button>` : ''}
        ${!mixCopyConfirmed ? '<span class="prod-warning">↑ Check the working copy box above to enable Apply.</span>' : ''}
      </div>

      ${mixJob ? `
      <div class="prod-job ${mixJob.status === 'Applied' ? 'is-success' : ''}" style="margin-top:16px">
        <p class="prod-kicker">MIX EXECUTION STATUS</p>
        <h4>${mixJob.status === 'Applied' ? '✅ Mix Balance Applied in Ableton Live' : escape(mixJob.status)}</h4>
        <p>${mixJob.status === 'Applied' ? 'All fader levels, pan positions, and send levels were updated and verified in Live. Listen back—if you prefer your previous balance, click Undo Mix Changes above.' : escape(mixJob.status)}</p>
      </div>` : ''}
    </div>` : `<div class="prod-card">
      <h4>Ready to balance your mix</h4>
      <p>${ready() ? 'Click <strong>Draft Mix Balance Plan</strong> above to preview role-based fader, panning, and Send A/B targets for your tracks.' : 'Connect Ableton Live to inspect your mixer levels and draft a reversible mix balance plan.'}</p>
    </div>`}

    <details class="prod-card" style="margin-top:18px" open>
      <summary><strong>🎛️ Device Macros &amp; Parameters (Live Readback · ${tracksWithDevices.length} tracks with devices)</strong></summary>
      <p style="margin-top:8px">Inspect and tweak loaded instruments and effects across your Set (such as <code>VOCAL</code>, <code>Light Electro</code>, <code>Serum 2</code>, <code>THE_INSTRUMENT</code>). Changes are drafted into a reversible snapshot plan.</p>
      ${tracksWithDevices.length ? `
        <div class="prod-table" style="margin-top:12px">
          ${tracksWithDevices.map(tr => `
            <div class="prod-card" style="margin-top:8px;padding:12px">
              <strong>${escape(tr.name)}</strong>
              ${(tr.devices || []).map((dev, devIdx) => {
                const params = (dev.parameters || []).slice(0, 8);
                return `<div style="margin-top:8px">
                  <span class="prod-pill">${escape(dev.name || dev.class_name || `Device ${devIdx + 1}`)}</span>
                  ${params.length ? `<div class="prod-field-row" style="margin-top:8px;flex-wrap:wrap;gap:12px">
                    ${params.map((p, pIdx) => {
                      const key = `${tr.id}:${devIdx}:${pIdx}`;
                      const min = Number(p.min ?? 0);
                      const max = Number(p.max ?? 1);
                      const step = p.is_quantized ? 1 : Number(((max - min) / 100).toFixed(4)) || 0.01;
                      const val = deviceTweaks[key] !== undefined ? deviceTweaks[key].value : Number(p.value ?? min);
                      return `<label class="prod-inline-field" style="min-width:190px;flex-direction:column;align-items:flex-start">
                        <span style="font-size:11px">${escape(p.name || `Param ${pIdx + 1}`)}: <strong>${Number(val).toFixed(2)}</strong></span>
                        <input type="range" min="${min}" max="${max}" step="${step}" value="${val}"
                          data-dev-track="${escape(tr.id)}" data-dev-idx="${devIdx}" data-param-idx="${pIdx}" style="width:175px" />
                      </label>`;
                    }).join('')}
                  </div>` : '<small style="margin-left:8px;opacity:0.75">Device loaded (parameters read on next Live tick)</small>'}
                </div>`;
              }).join('')}
            </div>
          `).join('')}
        </div>
        <div class="prod-actionline" style="margin-top:14px">
          <button class="prod-primary" data-action="draft-device-params" ${!ready() || !pendingDeviceCount || busy ? 'disabled' : ''}>
            Draft Device Macro Plan (${pendingDeviceCount} tweak${pendingDeviceCount === 1 ? '' : 's'})
          </button>
          ${devicePlan ? `<button class="prod-primary" data-action="apply-device-params" ${!mixCopyConfirmed || busy ? 'disabled' : ''}>Apply Device Plan to Live</button>` : ''}
          ${deviceJob && ['Applied', 'Partial failure'].includes(deviceJob.status) ? `<button data-action="rollback-device-params" ${!mixCopyConfirmed || busy ? 'disabled' : ''}>↩ Undo Device Changes</button>` : ''}
        </div>
        ${devicePlan ? `<p class="prod-footnote" style="margin-top:8px">Drafted plan <code>${short(devicePlan.id)}</code> with ${devicePlan.actions.length} parameter action(s). ${deviceJob ? `Execution status: <strong>${escape(deviceJob.status)}</strong>.` : ''}</p>` : ''}
      ` : `<p class="prod-footnote" style="margin-top:10px">No loaded devices reported in current Set snapshot.</p>`}
    </details>`;
  }

  function quickShuffleView() {
    const bpm = shuffleBpm || Number(analysis?.project?.tempo) || 119;
    const key = shuffleKey || 'Ab';
    const slots = shuffleResult?.slots || [];
    const audioTracks = (analysis?.tracks || []).filter(t => t.type === 'audio' && !t.is_group && t.audio_import_supported !== false);

    const sortedAudioTracks = [...audioTracks].sort((a, b) => {
      const aEmpty = !(a.arrangement_clips?.length || a.session_clips?.length || a.clips?.length);
      const bEmpty = !(b.arrangement_clips?.length || b.session_clips?.length || b.clips?.length);
      return (bEmpty ? 1 : 0) - (aEmpty ? 1 : 0);
    });
    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">STEP 3 · LOOP FINDER</p>
        <h3>Find 4 non-clashing loops for your track</h3>
        <p>Picks complementary Top, Percussion, Bass, and FX loops from your local sample library that fit together without frequency mud. Lock any loop you like, audition it in your browser, and send it auto-tuned into Ableton Live.</p>
      </div>
      <div class="prod-intro-actions">
        <div class="prod-sync-pill">Target: <strong>${bpm} BPM · Key ${escape(key)}</strong></div>
        <button class="prod-primary" data-action="shuffle-all" ${busy ? 'disabled' : ''}>🎲 Shuffle Unlocked Loops</button>
      </div>
    </div>

    <details class="prod-tech-details" style="margin-bottom:16px">
      <summary>Customize target BPM or Key (Defaults to ${bpm} BPM · ${escape(key)})</summary>
      <div class="prod-field-row" style="margin-top:10px">
        <label class="prod-inline-field"><span>Target BPM</span><input id="shuffleBpmInput" type="number" value="${bpm}" style="width:110px" /></label>
        <label class="prod-inline-field"><span>Target Key</span><input id="shuffleKeyInput" value="${escape(key)}" style="width:110px" /></label>
        <button data-action="shuffle-all" ${busy ? 'disabled' : ''}>Apply &amp; Shuffle</button>
      </div>
    </details>

    <label class="prod-check" style="margin-bottom:14px">
      <input id="samplesWorkingCopy" type="checkbox" ${copyConfirmed ? 'checked' : ''} />
      <span>I saved and opened a working copy in Ableton Live (required before sending loops to Live).</span>
    </label>

    ${slots.length ? `
    <div class="prod-slots-grid">
      ${slots.map(s => {
        const isLocked = lockedSlots[s.slot_id] || s.locked;
        const item = s.selected;
        if (!item) return `<article class="prod-slot-card"><div class="prod-slot-header"><span class="prod-slot-title">${escape(s.label)}</span></div><p>No matching sample found for this slot.</p></article>`;
        const spec = item.spectral_bands || {};
        const pitch = item.pitch_analysis || {};
        const onset = item.onset_density || {};
        const fname = cleanFileName(item.name || item.relative_path || item.path);
        const low = Math.round(spec.low_pct || 0);
        const lowmid = Math.round(spec.low_mid_pct || 0);
        const mid = Math.round(spec.mid_pct || 0);
        const high = Math.round(spec.high_pct || 0);
        const noteLabel = pitch.note_name || 'Percussive / Unpitched';
        const coarseTune = pitch.recommended_pitch_coarse ? `${pitch.recommended_pitch_coarse > 0 ? '+' : ''}${pitch.recommended_pitch_coarse} st` : 'In key (0 st)';
        const audioPath = item.path || item.relative_path || '';
        const selectedTrackId = slotTargetTracks[s.slot_id] || 'auto';
        const slotJob = slotImportJobs[s.slot_id];

        return `<article class="prod-slot-card ${isLocked ? 'is-locked' : ''}">
          <div class="prod-slot-header">
            <span class="prod-slot-title">${escape(s.label)}</span>
            <span class="prod-pill">${isLocked ? '🔒 Locked' : 'Unlocked'}</span>
          </div>
          <div class="prod-slot-file" title="${escape(item.path)}"><strong>${escape(fname)}</strong></div>
          <audio controls preload="none" src="/api/samples/audio?path=${encodeURIComponent(audioPath)}" style="width:100%;height:34px;margin:6px 0"></audio>
          <div class="prod-slot-tags">
            <span class="prod-pill">🎵 ${escape(noteLabel)} (${escape(coarseTune)})</span>
            <span class="prod-pill">⚡ ${escape(onset.groove_density || 'medium')} groove</span>
          </div>
          <div>
            <div class="prod-spectral-bar" title="Frequency balance: Sub/Low ${low}% · Low-Mid ${lowmid}% · Mid ${mid}% · High ${high}%">
              <div class="prod-band-low" style="width:${low}%"></div>
              <div class="prod-band-lowmid" style="width:${lowmid}%"></div>
              <div class="prod-band-mid" style="width:${mid}%"></div>
              <div class="prod-band-high" style="width:${high}%"></div>
            </div>
            <div class="prod-spectral-legend">
              <span>Sub ${low}%</span>
              <span>Body ${lowmid}%</span>
              <span>Mid ${mid}%</span>
              <span>Air ${high}%</span>
            </div>
          </div>
          <div class="prod-field-row" style="margin-top:8px;gap:6px">
            <label class="prod-inline-field" style="flex:1">
              <span>Target Audio Track</span>
              <select data-slot-track="${escape(s.slot_id)}">
                <option value="auto" ${selectedTrackId === 'auto' ? 'selected' : ''}>Auto (First Empty Audio Track)</option>
                ${sortedAudioTracks.map(tr => {
                  const isEmpty = !(tr.arrangement_clips?.length || tr.session_clips?.length || tr.clips?.length);
                  return `<option value="${escape(tr.id)}" ${selectedTrackId === tr.id ? 'selected' : ''}>${escape(tr.name)}${isEmpty ? ' (Empty)' : ''}</option>`;
                }).join('')}
              </select>
            </label>
          </div>
          <details class="prod-tech-details">
            <summary>Tuning &amp; file details</summary>
            <div class="prod-tuning-info" style="margin-top:8px">
              <div>Detected Note: <strong>${escape(noteLabel)}</strong></div>
              <div>Detune Offset: <strong>${pitch.cents_offset !== undefined ? (pitch.cents_offset > 0 ? '+' : '') + Math.round(pitch.cents_offset) + ' cents' : '0 cents'}</strong></div>
              <div>Transpose: <strong>${coarseTune}</strong></div>
              <div>Fine Tune: <strong>${pitch.recommended_pitch_fine !== undefined ? (pitch.recommended_pitch_fine > 0 ? '+' : '') + pitch.recommended_pitch_fine + ' cents' : '0 cents'}</strong></div>
            </div>
            <p class="prod-footnote" style="word-break:break-all;margin-top:6px">${escape(item.relative_path || item.path)}</p>
          </details>
          ${slotJob ? `<div class="prod-footnote" style="margin-top:6px"><strong>Live Import:</strong> ${escape(slotJob.status)}${slotJob.action?.target_name ? ` → ${escape(slotJob.action.target_name)}` : ''}</div>` : ''}
          <div class="prod-row" style="margin-top:auto;padding-top:8px;gap:6px;flex-wrap:wrap">
            <button data-action="toggle-slot-lock" data-slot="${escape(s.slot_id)}" data-path="${escape(item.path)}">${isLocked ? '🔓 Unlock' : '🔒 Keep Loop'}</button>
            <button data-action="reroll-slot" data-slot="${escape(s.slot_id)}" ${isLocked || busy ? 'disabled' : ''}>🎲 Swap</button>
            <button class="prod-primary" data-action="import-slot" data-slot="${escape(s.slot_id)}" data-path="${escape(item.path)}" data-relpath="${escape(item.relative_path || item.path)}" ${!copyConfirmed || !ready() || busy ? 'disabled' : ''}>➕ Send to Live (Auto-Tuned)</button>
          </div>
        </article>`;
      }).join('')}
    </div>` : `
    <div class="prod-card" style="text-align:center;padding:40px">
      <p>Click <strong>Shuffle Unlocked Loops</strong> above to roll 4 non-clashing drum, percussion, bass, and FX loops matched to your Set.</p>
    </div>`}`;
  }

  function pumpLabView() {
    const report = pumplabReport;
    const ref = refReport;
    const corr = report?.sub_phase_correlation;
    const corrPct = corr !== undefined ? Math.round(((corr + 1.0) / 2.0) * 100) : 50;
    const setClips = analysis?.audio_clips_in_set || [];
    const shuffledClips = (shuffleResult?.slots || [])
      .filter(s => s.selected?.path)
      .map(s => ({
        track_name: `Loop Finder · ${s.label}`,
        clip_name: cleanFileName(s.selected.relative_path || s.selected.path),
        file_path: s.selected.path,
      }));
    const allAudioOptions = [...setClips, ...shuffledClips];
    const renderClipSelect = (selectId, currentVal, placeholder) => `
      <select id="${selectId}">
        <option value="">${escape(placeholder)}</option>
        ${allAudioOptions.map(c => `<option value="${escape(c.file_path)}" ${currentVal === c.file_path ? 'selected' : ''}>${escape(c.track_name)} · "${escape(c.clip_name)}"</option>`).join('')}
      </select>`;

    return `<div class="prod-intro">
      <div>
        <p class="prod-kicker">STEP 5 · LOW-END, REFERENCE &amp; AUDIO-TO-MIDI</p>
        <h3>Check sub-bass punch, match references &amp; transcribe audio loops</h3>
        <p>Select audio clips directly from your open Ableton Set (or Loop Finder) to test 30–110 Hz sub-bass phase alignment, compare a mix bounce, or extract MIDI notes and transient slices.</p>
      </div>
    </div>
    <div class="prod-two">
      <article class="prod-card">
        <div class="prod-row">
          <div>
            <span class="prod-pill">30–110 Hz Sub-Bass</span>
            <h4>Kick vs. Bass Phase Check (PumpLab)</h4>
          </div>
          <button class="prod-primary" data-action="fill-pumplab-demo" ${busy ? 'disabled' : ''}>▶ Try Clash Demo</button>
        </div>
        <p>Detects if your Kick and Bass are fighting each other in the low end and calculates whether flipping polarity gives you more sub punch.</p>

        ${allAudioOptions.length ? `
        <div style="margin-top:10px">
          <div class="prod-field-row">
            <label class="prod-inline-field" style="flex:1"><span>Kick / Drum Clip from Open Set</span>${renderClipSelect('kickClipSelect', pumplabKick, 'Select a Kick or Drum clip in your Set…')}</label>
          </div>
          <div class="prod-field-row" style="margin-top:8px">
            <label class="prod-inline-field" style="flex:1"><span>Bass / Low Clip from Open Set</span>${renderClipSelect('bassClipSelect', pumplabBass, 'Select a Bass or Sub clip in your Set…')}</label>
          </div>
          <div style="margin-top:10px">
            <button class="prod-primary" data-action="run-pumplab" ${busy ? 'disabled' : ''}>⚡ Run Low-End Phase Check</button>
          </div>
        </div>` : ''}

        <details class="prod-tech-details" style="margin-top:10px" ${!allAudioOptions.length || (pumplabKick && !pumplabKick.startsWith('/tmp/')) ? 'open' : ''}>
          <summary>Or enter custom Kick &amp; Bass WAV paths</summary>
          <div style="margin-top:10px">
            <div class="prod-field-row">
              <input id="kickPathInput" placeholder="Path to Kick WAV (/Users/...)" value="${escape(pumplabKick)}" />
            </div>
            <div class="prod-field-row">
              <input id="bassPathInput" placeholder="Path to Bass WAV (/Users/...)" value="${escape(pumplabBass)}" />
            </div>
            <button class="prod-primary" data-action="run-pumplab" ${busy ? 'disabled' : ''}>Check Custom WAV Files</button>
          </div>
        </details>

        ${report ? `
        <div class="prod-meter-wrap">
          <div class="prod-verdict ${report.phase_cancellation_detected ? 'is-warn' : 'is-good'}">
            <strong>${report.phase_cancellation_detected ? '⚠️ Phase Clash Detected — Sub Frequencies Are Canceling Out' : '✅ Healthy Low-End — Kick & Bass Sum Together Cleanly'}</strong>
            ${report.polarity_inverted_gain_db > 1.0 ? `<p>💡 <strong>Quick Fix:</strong> Flip the polarity (Ø) on either your Kick or Bass track (e.g. using Ableton Utility) to gain <strong>+${report.polarity_inverted_gain_db.toFixed(1)} dB</strong> of sub punch!</p>` : ''}
          </div>
          <div class="prod-row" style="margin-top:12px">
            <span>Phase Alignment Meter</span>
            <strong class="${report.phase_cancellation_detected ? 'prod-warning' : 'prod-success'}">${corr !== undefined ? (corr > 0 ? '+' : '') + corr.toFixed(2) : '0.00'}</strong>
          </div>
          <div class="prod-meter-bar">
            <div class="prod-meter-needle" style="left:${corrPct}%"></div>
          </div>
          <div class="prod-spectral-legend">
            <span>-1.0 (Canceling)</span>
            <span>0.0 (Independent)</span>
            <span>+1.0 (Aligned)</span>
          </div>
          ${report.recommendations?.length ? `<div class="prod-next" style="margin-top:12px"><span>What to do:</span> ${report.recommendations.map(r => `<em>${escape(r.reason)}</em>`).join(' · ')}</div>` : ''}
        </div>` : ''}
      </article>

      <article class="prod-card">
        <div class="prod-row">
          <div>
            <span class="prod-pill">Loudness &amp; 4-Band EQ</span>
            <h4>Reference Track A/B Matcher</h4>
          </div>
          <button class="prod-primary" data-action="fill-ref-demo" ${busy ? 'disabled' : ''}>▶ Try Reference Demo</button>
        </div>
        <p>Compares your rough mix bounce against a favorite reference track to show loudness, peak headroom, and 4-band tonal differences.</p>

        ${allAudioOptions.length ? `
        <div style="margin-top:10px">
          <div class="prod-field-row">
            <label class="prod-inline-field" style="flex:1"><span>Reference Clip / Stem</span>${renderClipSelect('refBeforeSelect', refBefore, 'Select Reference audio clip…')}</label>
          </div>
          <div class="prod-field-row" style="margin-top:8px">
            <label class="prod-inline-field" style="flex:1"><span>Candidate Clip / Bounce</span>${renderClipSelect('refAfterSelect', refAfter, 'Select Candidate audio clip…')}</label>
          </div>
          <div style="margin-top:10px">
            <button class="prod-primary" data-action="run-ref-compare" ${busy ? 'disabled' : ''}>⚡ Compare Selected Clips</button>
          </div>
        </div>` : ''}

        <details class="prod-tech-details" style="margin-top:10px" ${!allAudioOptions.length || (refBefore && !refBefore.startsWith('/tmp/')) ? 'open' : ''}>
          <summary>Or enter custom Reference &amp; Bounce WAV paths</summary>
          <div style="margin-top:10px">
            <div class="prod-field-row">
              <input id="refBeforeInput" placeholder="Reference Track WAV path (/Users/...)" value="${escape(refBefore)}" />
            </div>
            <div class="prod-field-row">
              <input id="refAfterInput" placeholder="Your Mix Bounce WAV path (/Users/...)" value="${escape(refAfter)}" />
            </div>
            <button class="prod-primary" data-action="run-ref-compare" ${busy ? 'disabled' : ''}>Compare WAV Files</button>
          </div>
        </details>

        ${ref ? `
        <div class="prod-meter-wrap">
          <div class="prod-tuning-info">
            <div>Loudness Difference: <strong>${ref.deltas.loudness_delta_db > 0 ? '+' : ''}${ref.deltas.loudness_delta_db.toFixed(1)} dB</strong></div>
            <div>Peak Difference: <strong>${(ref.deltas.true_peak_delta_db ?? ref.deltas.peak_delta_db ?? 0) > 0 ? '+' : ''}${(ref.deltas.true_peak_delta_db ?? ref.deltas.peak_delta_db ?? 0).toFixed(1)} dB</strong></div>
          </div>
          <div style="margin-top:12px">
            <span class="prod-kicker">4-BAND TONAL DIFFERENCE (YOUR MIX VS. REFERENCE)</span>
            <div class="prod-tuning-info" style="margin-top:6px">
              <div>Sub / Low: <strong>${ref.deltas.spectral_delta_db.low_db > 0 ? '+' : ''}${ref.deltas.spectral_delta_db.low_db.toFixed(1)} dB</strong></div>
              <div>Low-Mid: <strong>${ref.deltas.spectral_delta_db.low_mid_db > 0 ? '+' : ''}${ref.deltas.spectral_delta_db.low_mid_db.toFixed(1)} dB</strong></div>
              <div>Mid Presence: <strong>${ref.deltas.spectral_delta_db.mid_db > 0 ? '+' : ''}${ref.deltas.spectral_delta_db.mid_db.toFixed(1)} dB</strong></div>
              <div>High Air: <strong>${ref.deltas.spectral_delta_db.high_db > 0 ? '+' : ''}${ref.deltas.spectral_delta_db.high_db.toFixed(1)} dB</strong></div>
            </div>
          </div>
          ${ref.recommendations?.length ? `<div class="prod-next" style="margin-top:12px"><span>Mix tips:</span> ${ref.recommendations.map(r => `<em>${escape(typeof r === 'string' ? r : r.reason)}</em>`).join(' · ')}</div>` : ''}
        </div>` : ''}
      </article>
    </div>

    <article class="prod-card" style="margin-top:18px">
      <div class="prod-row">
        <div>
          <span class="prod-pill">KeyScope Audio-to-MIDI &amp; StudioPilot Chopper</span>
          <h4>Audio-to-MIDI Melodic/Bass Extractor &amp; Transient Slicer</h4>
        </div>
      </div>
      <p>Extract a quantized MIDI bassline/melody or transient slice kit from any audio loop in your open Ableton Set or sample library, and optionally send it straight to a MIDI track in Live.</p>
      <div class="prod-field-row" style="margin-top:10px;gap:10px;flex-wrap:wrap">
        ${allAudioOptions.length ? `<label class="prod-inline-field" style="flex:1"><span>Pick Clip from Set</span>${renderClipSelect('transcribeClipSelect', transcribePath, 'Choose an audio clip from your Set…')}</label>` : ''}
        <label class="prod-inline-field" style="flex:1"><span>Or Audio File Path</span><input id="transcribePathInput" placeholder="/Users/.../loop.wav" value="${escape(transcribePath)}" /></label>
        <label class="prod-inline-field" style="min-width:190px"><span>Target MIDI Track (for Send)</span>
          <select id="pumplab-midi-track">
            <option value="auto">✨ Auto-select MIDI Track</option>
            ${(analysis?.tracks || []).filter(t => t.type === 'midi' && !t.is_group).map(t => `<option value="${escape(t.id)}">${escape(t.name)}</option>`).join('')}
          </select>
        </label>
      </div>
      <div class="prod-field-row" style="margin-top:10px;gap:10px;flex-wrap:wrap">
        <button class="prod-primary" data-action="run-audio-to-midi" ${busy ? 'disabled' : ''}>🎹 Transcribe Audio to MIDI</button>
        <button data-action="send-audio-to-midi-live" ${busy || !copyConfirmed ? 'disabled' : ''}>➕ Transcribe &amp; Send to MIDI Track</button>
        <button data-action="run-slice-transients" ${busy ? 'disabled' : ''}>🔪 Slice Loop Transients</button>
        <button data-action="send-slice-transients-live" ${busy || !copyConfirmed ? 'disabled' : ''}>➕ Slice &amp; Send Kit MIDI to Live</button>
      </div>
      ${transcribeReport ? `<div class="prod-review" style="margin-top:12px">
        <p class="prod-kicker">TRANSCRIBED MIDI NOTES · ${transcribeReport.note_count || 0} NOTES · KEY ${escape(transcribeReport.detected_key || '—')} ${escape(transcribeReport.detected_scale || '')}${transcribeReport.queued ? ` · ${transcribeReport.status === 'Failed' || transcribeReport.status === 'Partial failure' ? '❌' : '✅'} ${escape((transcribeReport.status || 'QUEUED').toUpperCase())} TO ${escape(transcribeReport.target_track_name || transcribeReport.target_track_id)}${transcribeReport.error ? ` (${escape(transcribeReport.error)})` : ''}` : ''}</p>
        <div class="prod-table">
          ${(transcribeReport.notes || []).slice(0, 16).map(n => `<div class="prod-role-row"><span><strong>MIDI Pitch ${n.pitch}</strong> · Start Beat ${n.start}</span><span>Duration ${n.duration} beats · Vel ${n.velocity}</span></div>`).join('')}
        </div>
      </div>` : ''}
      ${sliceReport ? `<div class="prod-review" style="margin-top:12px">
        <p class="prod-kicker">TRANSIENT SLICES · ${sliceReport.slice_count || 0} SLICES (${sliceReport.duration_seconds || 0}s)${sliceReport.queued ? ` · ${sliceReport.status === 'Failed' || sliceReport.status === 'Partial failure' ? '❌' : '✅'} ${escape((sliceReport.status || 'QUEUED').toUpperCase())} TO ${escape(sliceReport.target_track_name || sliceReport.target_track_id)}${sliceReport.error ? ` (${escape(sliceReport.error)})` : ''}` : ''}</p>
        <div class="prod-table">
          ${(sliceReport.slices || []).slice(0, 16).map(s => `<div class="prod-role-row"><span><strong>Slice #${s.slice_index + 1}</strong> · ${s.start_seconds}s – ${s.end_seconds}s</span><span>Band: ${escape(s.dominant_band)} · Pitch: ${escape(s.note_name || 'Unpitched')}</span></div>`).join('')}
        </div>
      </div>` : ''}
    </article>`;
  }


  function render() {
    if (!analysis) {
      root.innerHTML = `<div class="prod-loading">Loading your workspace… ${escape(notice)}</div>`;
      return;
    }
    const navItems = [
      ['finish', '1. Overview & Check'],
      ['arrange', '2. Arrange'],
      ['samples', '3. Loop Finder'],
      ['mix', '4. Mix Balance'],
      ['pumplab', '5. Low-End & Reference'],
      ['prepare', 'Project Setup'],
    ];
    root.innerHTML = `${header()}
      <nav class="prod-nav" aria-label="Production workflow steps">
        ${navItems.map(([key, label]) => `<button data-page="${key}" class="${page === key ? 'active' : ''}">${label}</button>`).join('')}
      </nav>
      ${notice ? `<div class="prod-notice ${isError ? 'error' : ''}" role="status"><span>${escape(notice)}</span><button class="prod-notice-close" data-action="dismiss-notice" aria-label="Dismiss notice">✕</button></div>` : ''}
      <div class="prod-content">
        ${page === 'finish'
          ? finish()
          : page === 'arrange'
          ? arrange()
          : page === 'prepare'
          ? prepare()
          : page === 'mix'
          ? mixAssistant()
          : page === 'samples'
          ? quickShuffleView()
          : pumpLabView()}
      </div>
      <footer class="prod-footer">
        <strong>Safe, reversible workflow:</strong> Every Live action requires a confirmed working copy and saves a snapshot so you can undo changes in one click.
      </footer>`;
  }

  root.addEventListener('change', e => {
    if (e.target.id === 'globalWorkingCopy' || e.target.id === 'workingCopy' || e.target.id === 'mixWorkingCopy' || e.target.id === 'samplesWorkingCopy') {
      setStoredCopyConfirmed(e.target.checked);
      render();
      return;
    }
    if (e.target.dataset.slotTrack) {
      slotTargetTracks[e.target.dataset.slotTrack] = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'diagnosisVariant') {
      diagnosisVariant = e.target.value;
      if (ready()) {
        run(async () => {
          diagnosis = await api('/finish-diagnosis', {template_variant_id: diagnosisVariant, expected_revision: analysis.source_revision});
        });
      }
      return;
    }
    if (e.target.id === 'shuffleBpmInput') shuffleBpm = Number(e.target.value);
    if (e.target.id === 'shuffleKeyInput') shuffleKey = e.target.value;
    if (e.target.id === 'kickPathInput' || e.target.id === 'kickClipSelect') {
      pumplabKick = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'bassPathInput' || e.target.id === 'bassClipSelect') {
      pumplabBass = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'refBeforeInput' || e.target.id === 'refBeforeSelect') {
      refBefore = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'refAfterInput' || e.target.id === 'refAfterSelect') {
      refAfter = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'transcribePathInput' || e.target.id === 'transcribeClipSelect') {
      transcribePath = e.target.value;
      render();
      return;
    }
    if (e.target.id === 'productionGenre') {
      genreChoice = e.target.value;
      genreTouched = true;
      diagnosisVariant = defaultVariant(genreChoice);
      diagnosis = null;
      options = null;
      selection = null;
      plan = null;
      sourceRoles = {};
      sourceClips = {};
      run(async () => {
        await ensurePageDefaults();
      });
      return;
    }
    if (e.target.id === 'arrangementView') {
      viewChoice = e.target.value;
      plan = null;
      sourceRoles = {};
      sourceClips = {};
      if (selection) autoAssignSourceRoles(selection, options);
      render();
      return;
    }
    if (e.target.dataset.trackId) roleChoices[e.target.dataset.trackId] = e.target.value;
    if (e.target.dataset.sourceTrack) {
      sourceRoles[e.target.dataset.sourceTrack] = e.target.value;
      plan = null;
      render();
    }
    if (e.target.dataset.sourceClip) {
      sourceClips[e.target.dataset.sourceClip] = e.target.value;
      plan = null;
      render();
    }
    if (e.target.dataset.devTrack !== undefined) {
      const tid = e.target.dataset.devTrack;
      const devIdx = Number(e.target.dataset.devIdx);
      const paramIdx = Number(e.target.dataset.paramIdx);
      const val = Number(e.target.value);
      deviceTweaks[`${tid}:${devIdx}:${paramIdx}`] = {
        target_track_id: tid,
        device_index: devIdx,
        parameter_index: paramIdx,
        value: val,
      };
      render();
    }
  });

  root.addEventListener('click', e => {
    const button = e.target.closest('button');
    if (!button) return;
    if (button.dataset.gotoMode) {
      if (window.vibeltonSwitchMode) window.vibeltonSwitchMode(button.dataset.gotoMode);
      return;
    }
    if (button.dataset.goto) {
      page = button.dataset.goto;
      if (button.dataset.view) viewChoice = button.dataset.view;
      notice = '';
      run(async () => {
        await ensurePageDefaults();
        if (button.dataset.auto === 'roles' && ready() && !roleProposal) {
          roleProposal = await api('/track-role-proposal', {request_id: id()});
          roleChoices = {};
        }
      });
      return;
    }
    if (button.dataset.page) {
      page = button.dataset.page;
      notice = '';
      run(async () => {
        await ensurePageDefaults();
      });
      return;
    }
    const action = button.dataset.action;
    if (!action) return;
    if (action === 'dismiss-notice') {
      notice = '';
      render();
      return;
    }
    if (action === 'auto-assign-sources') {
      sourceRoles = {};
      autoAssignSourceRoles(selection, options);
      notice = 'Pre-matched tracks to roles based on your Set.';
      isError = false;
      render();
      return;
    }
    run(async () => {
      notice = '';
      isError = false;
      if (action === 'refresh') {
        autoLoadedRevision = null;
        await refresh();
        notice = ready() ? 'Set refreshed from Ableton Live.' : 'Refreshed cached Set snapshot.';
      }
      if (action === 'diagnose') {
        await refresh();
        diagnosis = await api('/finish-diagnosis', {template_variant_id: diagnosisVariant, expected_revision: analysis.source_revision});
      }
      if (action === 'draft-session-to-arrangement') {
        await refresh();
        plan = await api('/session-to-arrangement-plan', {});
        job = null;
        originalJob = null;
        notice = `Drafted reversible plan to place ${plan.placed_clips_summary?.length || 1} unplaced Session clip(s) onto the Arrangement timeline.`;
      }
      if (action === 'options') {
        await refresh();
        options = await api('/arrangement-options', {request_id: id(), genre: genreChoice});
        selection = null;
        plan = null;
        job = null;
        originalJob = null;
        sourceRoles = {};
        sourceClips = {};
      }
      if (action === 'select') {
        selection = await api('/arrangement-selection', {proposal_id: options.id, variant_id: button.dataset.variant, approved: true, request_id: id()});
        plan = null;
        job = null;
        originalJob = null;
        sourceRoles = {};
        sourceClips = {};
        autoAssignSourceRoles(selection, options);
      }
      if (action === 'arrangement-plan') {
        const session = viewChoice === 'session';
        const candidates = new Map((session ? sessionCandidates() : sourceCandidates()).map(({track, clip}) => [track.id, clip]));
        const sources = Object.entries(sourceRoles)
          .filter(([, role]) => role)
          .map(([track_id, role]) =>
            session
              ? {track_id, role, source_scene_index: candidates.get(track_id)?.scene_index}
              : {track_id, role, source_start_beat: candidates.get(track_id)?.start_beat}
          );
        plan = await api('/arrangement-execution-plan', {
          selection_id: selection.id,
          snapshot_name: `Before ${selection.variant.name} ${session ? 'Session scenes' : 'arrangement'}`,
          approved: true,
          sources,
          ...(session ? {view: 'session'} : {}),
        });
      }
      if (action === 'template') {
        await refresh();
        plan = await api('/template', {snapshot_name: 'Before Classic House template'});
        job = null;
        originalJob = null;
      }
      if (action === 'cleanup') {
        await refresh();
        cleanup = await api('/cleanup-proposal', {});
      }
      if (action === 'roles') {
        await refresh();
        roleProposal = await api('/track-role-proposal', {request_id: id()});
        roleChoices = {};
      }
      if (action === 'confirm-roles') {
        const choices = Object.fromEntries(roleProposal.tracks.map(t => [t.track_id, roleChoices[t.track_id] ?? t.suggested_role ?? null]));
        roles = await api('/track-role-confirmation', {proposal_id: roleProposal.id, roles: choices});
        notice = 'Track roles saved for this Set. Your Ableton tracks were not renamed or altered.';
        roleProposal = null;
      }
      if (action === 'apply') {
        if (!copyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        await refresh();
        if (stale(plan)) throw new Error('The Live Set changed. Please preview a fresh placement plan.');
        job = await api('/apply', {plan_id: plan.id, working_copy_confirmed: true});
        originalJob = job;
        plan.status = 'Queued';
        notice = 'Sent to Ableton Live. Verifying placement…';
      }
      if (action === 'view-job') {
        job = await api('/status/' + button.dataset.job);
        originalJob = job;
        plan = await api('/plans/' + job.plan_id);
      }
      if (action === 'job-status') {
        job = await api('/status/' + job.id);
        if (originalJob?.id === job.id) originalJob = job;
        await refresh();
      }
      if (action === 'rollback') {
        if (!copyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        const source = await api('/status/' + originalJob.id);
        job = await api('/rollback', {job_id: source.id, working_copy_confirmed: true});
        notice = 'Undo queued in Ableton Live. Restoring previous state…';
      }
      if (action === 'draft-mix') {
        await refresh();
        mixPlan = await api('/mix-balance-proposal', {request_id: id()});
        notice = 'Mix balance plan ready. Review the proposed levels, panning, and spatial sends below.';
      }
      if (action === 'apply-mix') {
        if (!mixCopyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        await refresh();
        mixJob = await api('/apply', {plan_id: mixPlan.id, working_copy_confirmed: true});
        notice = 'Mix balance sent to Ableton Live.';
      }
      if (action === 'rollback-mix') {
        if (!mixCopyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        await api('/rollback', {job_id: mixJob.id, working_copy_confirmed: true});
        mixJob = null;
        notice = 'Mix changes undone—restored previous fader, pan, and send settings.';
      }
      if (action === 'draft-device-params') {
        const changes = Object.values(deviceTweaks);
        if (!changes.length) throw new Error('Move at least one device parameter slider first.');
        await refresh();
        devicePlan = await api('/device-parameter-plan', {changes});
        deviceJob = null;
        notice = `Drafted device macro plan (${changes.length} parameter tweak${changes.length === 1 ? '' : 's'}).`;
      }
      if (action === 'apply-device-params') {
        if (!mixCopyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        await refresh();
        deviceJob = await api('/apply', {plan_id: devicePlan.id, working_copy_confirmed: true});
        notice = 'Device parameter plan sent to Ableton Live.';
      }
      if (action === 'rollback-device-params') {
        if (!mixCopyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        await api('/rollback', {job_id: deviceJob.id, working_copy_confirmed: true});
        deviceJob = null;
        deviceTweaks = {};
        notice = 'Device parameter changes undone.';
      }
      if (action === 'shuffle-all') {
        const bpm = shuffleBpm || Number(analysis?.project?.tempo) || 119;
        const key = shuffleKey || 'Ab';
        shuffleResult = await api('/api/samples/shuffle', {target_bpm: bpm, target_key: key, locked_slots: lockedSlots});
        notice = `Rolled 4 non-clashing loops matched to ${bpm} BPM and ${key}.`;
      }
      if (action === 'toggle-slot-lock') {
        const slot = button.dataset.slot;
        const path = button.dataset.path;
        if (lockedSlots[slot]) {
          delete lockedSlots[slot];
        } else {
          lockedSlots[slot] = path;
        }
        render();
      }
      if (action === 'reroll-slot') {
        const bpm = shuffleBpm || Number(analysis?.project?.tempo) || 119;
        const key = shuffleKey || 'Ab';
        const tempLocks = {...lockedSlots};
        const targetSlot = button.dataset.slot;
        for (const s of shuffleResult?.slots || []) {
          if (s.slot_id !== targetSlot && s.selected?.path) {
            tempLocks[s.slot_id] = s.selected.path;
          }
        }
        delete tempLocks[targetSlot];
        shuffleResult = await api('/api/samples/shuffle', {
          target_bpm: bpm,
          target_key: key,
          locked_slots: tempLocks,
          seed: Math.floor(Math.random() * 10000),
        });
        render();
      }
      if (action === 'import-slot') {
        if (!copyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
        const slotId = button.dataset.slot;
        const path = button.dataset.path || button.dataset.relpath;
        const trackId = slotTargetTracks[slotId] || 'auto';
        const key = shuffleKey || 'Ab';
        await refresh();
        const importJob = await api('/api/samples/import-smart', {
          path,
          relative_path: button.dataset.relpath,
          track_id: trackId,
          target_key: key,
          auto_tune: true,
          working_copy_confirmed: true,
        });
        slotImportJobs[slotId] = importJob;
        notice = `Queued auto-tuned loop import to ${importJob.action?.target_name || trackId} in Ableton Live.`;
      }
      if (action === 'run-pumplab') {
        const k = document.querySelector('#kickPathInput')?.value || document.querySelector('#kickClipSelect')?.value || pumplabKick;
        const b = document.querySelector('#bassPathInput')?.value || document.querySelector('#bassClipSelect')?.value || pumplabBass;
        if (!k || !b) throw new Error('Please select or enter both Kick and Bass audio files (or click "Try Clash Demo").');
        pumplabReport = await api('/low-end-check', {kick_path: k, bass_path: b});
        notice = pumplabReport.phase_cancellation_detected
          ? 'Phase cancellation detected! See the recommended fix below.'
          : 'Low-end phase is healthy—Kick and Bass sum cleanly.';
      }
      if (action === 'fill-pumplab-demo') {
        pumplabKick = '/tmp/pumplab_demo_kick.wav';
        pumplabBass = '/tmp/pumplab_demo_bass.wav';
        pumplabReport = await api('/low-end-check', {kick_path: pumplabKick, bass_path: pumplabBass});
        notice = 'Loaded 180° phase clash demo: notice how flipping polarity restores sub punch.';
      }
      if (action === 'fill-ref-demo') {
        refBefore = '/tmp/ref_demo_target.wav';
        refAfter = '/tmp/ref_demo_candidate.wav';
        refReport = await api('/reference-compare', {reference_path: refBefore, candidate_path: refAfter});
        notice = 'Loaded Reference Comparison demo: review the loudness and 4-band EQ differences below.';
      }
      if (action === 'run-ref-compare') {
        const ref = document.querySelector('#refBeforeInput')?.value || document.querySelector('#refBeforeSelect')?.value || refBefore;
        const cand = document.querySelector('#refAfterInput')?.value || document.querySelector('#refAfterSelect')?.value || refAfter;
        if (!ref || !cand) throw new Error('Please select or enter both Reference and Mix Bounce WAV paths (or click "Try Reference Demo").');
        refReport = await api('/reference-compare', {reference_path: ref, candidate_path: cand});
        notice = 'Reference comparison complete.';
      }
      if (action === 'run-audio-to-midi' || action === 'send-audio-to-midi-live') {
        const p = document.querySelector('#transcribePathInput')?.value || document.querySelector('#transcribeClipSelect')?.value || transcribePath;
        if (!p) throw new Error('Please select an audio clip or enter a WAV file path to transcribe.');
        transcribePath = p;
        const bpm = Number(analysis?.project?.tempo) || 120;
        const payload = {path: p, bpm, quantize_grid: 0.25};
        if (action === 'send-audio-to-midi-live') {
          if (!copyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
          payload.target_track_id = document.querySelector('#pumplab-midi-track')?.value || document.querySelector('#transcribeTargetTrack')?.value || 'auto';
          payload.working_copy_confirmed = true;
        }
        transcribeReport = await api('/api/samples/audio-to-midi', payload);
        notice = transcribeReport.queued
          ? `Transcribed ${transcribeReport.note_count || 0} MIDI notes and queued clip to ${transcribeReport.target_track_name || transcribeReport.target_track_id}.`
          : `Transcribed ${transcribeReport.note_count || 0} MIDI notes from audio loop (Key: ${transcribeReport.detected_key || '—'} ${transcribeReport.detected_scale || ''}).`;
      }
      if (action === 'run-slice-transients' || action === 'send-slice-transients-live') {
        const p = document.querySelector('#transcribePathInput')?.value || document.querySelector('#transcribeClipSelect')?.value || transcribePath;
        if (!p) throw new Error('Please select an audio clip or enter a WAV file path to slice.');
        transcribePath = p;
        const bpm = Number(analysis?.project?.tempo) || 120;
        const payload = {path: p, max_slices: 16, bpm};
        if (action === 'send-slice-transients-live') {
          if (!copyConfirmed) throw new Error('Please check the "Working copy saved" box first.');
          payload.target_track_id = document.querySelector('#pumplab-midi-track')?.value || document.querySelector('#transcribeTargetTrack')?.value || 'auto';
          payload.working_copy_confirmed = true;
        }
        sliceReport = await api('/api/samples/slice-transients', payload);
        notice = sliceReport.queued
          ? `Detected ${sliceReport.slice_count || 0} transient slices and queued MIDI kit clip to ${sliceReport.target_track_name || sliceReport.target_track_id}.`
          : `Detected ${sliceReport.slice_count || 0} transient slices.`;
      }
    });
  });

  window.addEventListener('production-open', () => {
    copyConfirmed = getStoredCopyConfirmed();
    mixCopyConfirmed = getStoredCopyConfirmed();
    refresh().then(render).catch(e => setNotice(e.message, true));
  });

  function hasFocusedInput() {
    const el = document.activeElement;
    return Boolean(el && root.contains(el) && ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName));
  }

  // Auto-poll active Queued jobs so user never has to click "Refresh Status" manually
  setInterval(async () => {
    if (busy || pollInFlight || !document.body.classList.contains('mode-production')) return;
    pollInFlight = true;
    try {
      let shouldRefresh = false;
      if (job && ['Queued', 'queued', 'Running', 'running'].includes(job.status)) {
        job = await api('/status/' + job.id);
        if (originalJob?.id === job.id) originalJob = job;
        if (!['Queued', 'queued', 'Running', 'running'].includes(job.status)) {
          shouldRefresh = true;
        }
      }
      if (mixJob && ['Queued', 'queued', 'Running', 'running'].includes(mixJob.status)) {
        mixJob = await api('/status/' + mixJob.id);
        if (!['Queued', 'queued', 'Running', 'running'].includes(mixJob.status)) {
          shouldRefresh = true;
        }
      }
      if (deviceJob && ['Queued', 'queued', 'Running', 'running'].includes(deviceJob.status)) {
        deviceJob = await api('/status/' + deviceJob.id);
        if (!['Queued', 'queued', 'Running', 'running'].includes(deviceJob.status)) {
          shouldRefresh = true;
        }
      }
      for (const [slotId, sJob] of Object.entries(slotImportJobs)) {
        if (sJob && sJob.status === 'Queued') {
          const updated = await api('/api/samples/imports/' + sJob.id);
          slotImportJobs[slotId] = updated;
          if (updated.status !== 'Queued') {
            shouldRefresh = true;
          }
        }
      }
      for (const report of [transcribeReport, sliceReport]) {
        if (report && report.job_id && report.status === 'Queued') {
          const updated = await api('/api/samples/imports/' + report.job_id);
          report.status = updated.status;
          report.execution = updated.execution;
          if (updated.error || updated.execution?.error) {
            report.error = updated.error || updated.execution?.error;
            if (updated.status === 'Failed' || updated.status === 'Partial failure') {
              notice = report.error;
              isError = true;
            }
          }
          if (updated.status !== 'Queued') {
            shouldRefresh = true;
          }
        }
      }
      if (shouldRefresh) {
        await refresh();
        if (!hasFocusedInput()) render();
      }
    } catch {
      // Ignore transient poll errors
    } finally {
      pollInFlight = false;
    }
  }, 1800);


  setInterval(() => {
    if (!busy && !pollInFlight && document.body.classList.contains('mode-production') && !hasFocusedInput()) {
      pollInFlight = true;
      refresh().then(() => {
        if (!hasFocusedInput()) render();
      }).catch(() => {}).finally(() => {
        pollInFlight = false;
      });
    }
  }, 7000);

  refresh().then(render).catch(e => {
    root.innerHTML = `<div class="prod-loading">Could not load workspace: ${escape(e.message)} <button onclick="location.reload()">Retry</button></div>`;
  });
})();
