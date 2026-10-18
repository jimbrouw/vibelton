/**
 * Vibelton Arranger Max for Live In-DAW Companion UI
 * High-density Ableton Live 12 dark-mode interface for subtractive arrangement scaffolding.
 */

(() => {
  // --- State ---
  let liveState = null;
  let analysis = null;
  let activeRoles = null;
  let genreOptions = null;
  let selectedGenre = 'House';
  let selectedVariant = 'club-version';
  let userStemOverrides = {};
  let rememberedRoles = {};        // { trackId: { role, matched_by, needs_review } } remembered for this Set
  let roleMemoryInfo = null;
  let currentPlan = null;
  let lastAppliedJob = null;
  let isBusy = false;
  let selectedScope = '';          // '' = whole arrangement, otherwise a section name
  let scaffoldedSections = {};     // { sectionName: { clips, job_id } } as currently in the Set
  let pendingRescaffold = false;
  let serverReachable = true;      // false while the heartbeat cannot reach the server

  const STORAGE_KEY_CONFIRMED = 'vibelton-arranger-copy-confirmed';
  let workingCopyConfirmed = sessionStorage.getItem(STORAGE_KEY_CONFIRMED) === 'true';

  const ALL_ROLES = [
    'Kick',
    'Snare / Clap',
    'Hats',
    'Percussion',
    'Bass',
    'Chords',
    'Lead',
    'Hook',
    'Atmosphere',
    'Vocal',
    'FX / Risers',
    'Ignore / Unknown'
  ];

  // The genre list comes from GET /api/production/genres. This copy is only used when the server
  // cannot be reached, so the device still shows the four original structures.
  const FALLBACK_CATALOGUE = {
    default_genre: 'House',
    genres: [
      { genre: 'House', family: 'House & Disco', bpm_range: [120, 128], default_variant: 'club-version', variants: [
        { id: 'streaming-edit', name: 'Streaming edit', target_duration: '3:15', target_duration_seconds: 195 },
        { id: 'club-version', name: 'Club version', target_duration: '4:39', target_duration_seconds: 278.7 },
        { id: 'dj-extended-mix', name: 'DJ extended mix', target_duration: '6:00', target_duration_seconds: 360 }] },
      { genre: 'Techno', family: 'Techno & Trance', bpm_range: [125, 140], default_variant: 'techno-peak-time', variants: [
        { id: 'techno-hypnotic', name: 'Hypnotic', target_duration: '5:00', target_duration_seconds: 300 },
        { id: 'techno-peak-time', name: 'Peak time', target_duration: '5:30', target_duration_seconds: 330 },
        { id: 'techno-extended-dj', name: 'Extended DJ', target_duration: '6:30', target_duration_seconds: 390 }] },
      { genre: 'Drum & Bass', family: 'Breaks & Bass', bpm_range: [170, 180], default_variant: 'dnb-rolling-club', variants: [
        { id: 'dnb-quick-cut', name: 'Quick cut', target_duration: '3:00', target_duration_seconds: 180 },
        { id: 'dnb-rolling-club', name: 'Rolling club', target_duration: '4:00', target_duration_seconds: 240 },
        { id: 'dnb-extended-journey', name: 'Extended journey', target_duration: '5:00', target_duration_seconds: 300 }] },
      { genre: 'UK Garage', family: 'Breaks & Bass', bpm_range: [128, 136], default_variant: 'ukg-vocal-club', variants: [
        { id: 'ukg-compact', name: 'Compact 2-step', target_duration: '3:00', target_duration_seconds: 180 },
        { id: 'ukg-vocal-club', name: 'Vocal club', target_duration: '4:00', target_duration_seconds: 240 },
        { id: 'ukg-extended-shuffle', name: 'Extended shuffle', target_duration: '5:00', target_duration_seconds: 300 }] }
    ]
  };
  let genreCatalogue = FALLBACK_CATALOGUE;
  let lastLabelTempo = null;

  // --- DOM Elements ---
  const elConnectionPill = document.getElementById('connectionPill');
  const elConnectionText = document.getElementById('connectionText');
  const elSetNameBadge = document.getElementById('setNameBadge');
  const elSetNameText = document.getElementById('setNameText');
  const elBtnRefresh = document.getElementById('btnRefresh');
  const elBtnPopout = document.getElementById('btnPopout');
  const elStemsContainer = document.getElementById('stemsContainer');
  const elStemsCountBadge = document.getElementById('stemsCountBadge');
  const elGenreSelect = document.getElementById('genreSelect');
  const elVariantSelect = document.getElementById('variantSelect');
  const elEnergySvg = document.getElementById('energySvg');
  const elSvgGrid = document.getElementById('svgGrid');
  const elSvgFill = document.getElementById('svgFill');
  const elSvgStroke = document.getElementById('svgStroke');
  const elSvgSections = document.getElementById('svgSections');
  const elEnergyTooltip = document.getElementById('energyTooltip');
  const elTtTitle = document.getElementById('ttTitle');
  const elTtEnergy = document.getElementById('ttEnergy');
  const elTtActive = document.getElementById('ttActive');
  const elTtMuted = document.getElementById('ttMuted');
  const elTtTransition = document.getElementById('ttTransition');
  const elStepAnalyze = document.getElementById('stepAnalyze');
  const elStepPlan = document.getElementById('stepPlan');
  const elStepPlace = document.getElementById('stepPlace');
  const elStepVerify = document.getElementById('stepVerify');
  const elSafetyBox = document.getElementById('safetyBox');
  const elSafetyLabel = document.getElementById('safetyLabel');
  const elWorkingCopyCheck = document.getElementById('workingCopyCheck');
  const elBtnScaffold = document.getElementById('btnScaffold');
  const elScaffoldBtnLabel = document.getElementById('scaffoldBtnLabel');
  const elBtnRollback = document.getElementById('btnRollback');
  const elStatusFeedback = document.getElementById('statusFeedback');

  // --- API Helper ---
  async function api(endpoint, method = 'GET', body = null) {
    const opts = { method, headers: {} };
    if (body !== null) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(endpoint, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const failure = new Error(data.error || `HTTP ${res.status}`);
      failure.explanation = data.explanation || null;
      throw failure;
    }
    return data;
  }

  // Plain message in the main view; the raw error sits behind a collapsed "Details" toggle.
  const elErrorDetails = document.getElementById('errorDetails');
  const elErrorDetailsText = document.getElementById('errorDetailsText');

  function clearFailure() {
    elErrorDetails.hidden = true;
    elErrorDetails.open = false;
    elErrorDetailsText.textContent = '';
  }

  function showFailure(err, prefix = '') {
    const e = err && err.explanation;
    const plain = e
      ? [e.title ? `${e.title}.` : '', e.message, e.next_step].filter(Boolean).join(' ')
      : (prefix || 'Something went wrong.');
    elStatusFeedback.textContent = plain;
    elStatusFeedback.className = 'status-feedback error';
    const raw = (e && e.raw) || (err && err.message) || '';
    const lines = e && Array.isArray(e.details) ? e.details.slice(0, 40) : [];
    elErrorDetailsText.textContent = lines.length ? `${lines.join('\n')}\n\n${raw}` : raw;
    elErrorDetails.hidden = !raw;
    elErrorDetails.open = false;
    return plain;
  }

  // A finished-but-failed job: keep the explanation so Undo stays available for what was placed.
  function jobFailure(statusData, fallback) {
    const failure = new Error(statusData.error || fallback);
    failure.explanation = statusData.explanation || null;
    failure.job = statusData;
    return failure;
  }

  // --- Working Copy Gate (verdict comes from the server, which also enforces it) ---
  let workingCopyGate = { allowed: false, reason: 'unknown', message: 'Checking the open Live Set…', set_name: null };

  function updateSafetyUI(verdict) {
    workingCopyGate = verdict || workingCopyGate;
    const name = workingCopyGate.set_name || 'Untitled Set';
    elSetNameText.textContent = name;
    elSetNameBadge.title = workingCopyGate.set_path || 'Unsaved Set';

    if (workingCopyGate.allowed) {
      elSetNameBadge.className = 'set-name-badge is-copy';
      elSetNameBadge.innerHTML = `<span>✓</span> Working copy (${escapeHtml(name)})`;
      elSafetyBox.className = 'safety-box';
      elSafetyLabel.textContent = 'I confirm this is a working copy';
      elWorkingCopyCheck.disabled = false;
      elWorkingCopyCheck.checked = workingCopyConfirmed;
    } else {
      elSetNameBadge.className = 'set-name-badge is-master';
      elSetNameBadge.innerHTML = `<span>⛔</span> Original Set — scaffolding disabled (${escapeHtml(name)})`;
      elSafetyBox.className = 'safety-box warning';
      elSafetyLabel.textContent = workingCopyGate.message;
      elWorkingCopyCheck.disabled = true;
      elWorkingCopyCheck.checked = false;
    }
    updateScaffoldButtonState();
  }

  function escapeHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // --- Stepper UI ---
  function updateStepper(activeStage, completed = false) {
    const steps = [
      { id: 'analyze', el: elStepAnalyze },
      { id: 'plan', el: elStepPlan },
      { id: 'place', el: elStepPlace },
      { id: 'verify', el: elStepVerify }
    ];

    let foundActive = false;
    steps.forEach(({ id, el }) => {
      el.classList.remove('active', 'done');
      if (id === activeStage) {
        foundActive = true;
        if (completed) {
          el.classList.add('done');
        } else {
          el.classList.add('active');
        }
      } else if (!foundActive) {
        el.classList.add('done');
      }
    });
  }

  function resetStepper() {
    [elStepAnalyze, elStepPlan, elStepPlace, elStepVerify].forEach(el => {
      el.classList.remove('active', 'done');
    });
  }

  // --- Stem Role Inference ---
  function inferRoleFromName(trackName) {
    const lower = (trackName || '').toLowerCase();
    if (lower.includes('kick') || lower.includes('bd') || lower.includes('bassdrum')) return 'Kick';
    if (lower.includes('snare') || lower.includes('clap') || lower.includes('rim')) return 'Snare / Clap';
    if (lower.includes('hat') || lower.includes('hh') || lower.includes('cymbal') || lower.includes('ride')) return 'Hats';
    if (lower.includes('perc') || lower.includes('shaker') || lower.includes('conga') || lower.includes('bongo') || lower.includes('tamb')) return 'Percussion';
    if (lower.includes('bass') || lower.includes('sub') || lower.includes('808') || lower.includes('reese')) return 'Bass';
    if (lower.includes('chord') || lower.includes('pad') || lower.includes('rhodes') || lower.includes('key') || lower.includes('piano')) return 'Chords';
    if (lower.includes('lead') || lower.includes('synth') || lower.includes('pluck') || lower.includes('arp')) return 'Lead';
    if (lower.includes('hook') || lower.includes('theme') || lower.includes('riff')) return 'Hook';
    if (lower.includes('atmo') || lower.includes('texture') || lower.includes('drone') || lower.includes('ambient')) return 'Atmosphere';
    if (lower.includes('vox') || lower.includes('vocal') || lower.includes('acapella')) return 'Vocal';
    if (lower.includes('fx') || lower.includes('riser') || lower.includes('sweep') || lower.includes('impact') || lower.includes('downlifter')) return 'FX / Risers';
    return null;
  }

  // Precedence: this session's choice > exact-revision confirmation > remembered for this Set > name guess.
  function resolveRole(track) {
    const remembered = rememberedRoles[track.id];
    return userStemOverrides[track.id]
      || (activeRoles && activeRoles.roles ? activeRoles.roles[track.id] : null)
      || (remembered ? (remembered.role || 'Ignore / Unknown') : null)
      || track.suggested_role || inferRoleFromName(track.name)
      || 'Ignore / Unknown';
  }

  async function refreshRoleMemory() {
    try {
      roleMemoryInfo = await api('/api/production/role-memory');
      rememberedRoles = roleMemoryInfo.remembered || {};
    } catch (err) {
      roleMemoryInfo = null;
      rememberedRoles = {};
    }
    const note = document.getElementById('roleMemoryNote');
    const forget = document.getElementById('btnForgetRoles');
    note.textContent = roleMemoryInfo ? roleMemoryInfo.message : '';
    note.classList.toggle('has-review', Boolean(roleMemoryInfo && roleMemoryInfo.needs_review && roleMemoryInfo.needs_review.length));
    forget.hidden = !(roleMemoryInfo && Object.keys(rememberedRoles).length);
  }

  async function rememberRole(trackId, role) {
    try {
      await api('/api/production/role-memory', 'POST', { roles: { [trackId]: role } });
      await refreshRoleMemory();
      renderStems();
    } catch (err) {
      showFailure(err, 'Could not remember that role.');
    }
  }

  document.getElementById('btnForgetRoles').addEventListener('click', async () => {
    await api('/api/production/role-memory', 'POST', { clear: true }).catch(() => null);
    userStemOverrides = {};
    await refreshRoleMemory();
    renderStems();
    drawEnergyCurve();
  });

  // --- Step 1: Render Stems ---
  function renderStems() {
    if (!analysis || !analysis.tracks) {
      elStemsContainer.innerHTML = '<div class="status-feedback">No tracks detected</div>';
      elStemsCountBadge.textContent = '0 tracks';
      return;
    }

    const tracks = analysis.tracks.filter(t => !t.is_group);
    elStemsCountBadge.textContent = `${tracks.length} tracks`;

    if (tracks.length === 0) {
      elStemsContainer.innerHTML = '<div class="status-feedback">No playable tracks in Set</div>';
      return;
    }

    elStemsContainer.innerHTML = '';

    tracks.forEach(track => {
      // Determine assigned role
      const override = userStemOverrides[track.id];
      const confirmed = activeRoles && activeRoles.roles ? activeRoles.roles[track.id] : null;
      const remembered = rememberedRoles[track.id];
      const suggested = track.suggested_role || inferRoleFromName(track.name);
      const role = resolveRole(track);

      // Confidence
      let confClass = 'conf-med';
      if (override || confirmed || (remembered && !remembered.needs_review)) {
        confClass = 'conf-high';
      } else if (!suggested && !remembered) {
        confClass = 'conf-low';
      }
      const memoryNote = remembered && !override
        ? (remembered.needs_review ? 'Remembered by position — check this role'
           : remembered.renamed_from ? `Remembered (was "${remembered.renamed_from}")` : 'Remembered for this Set')
        : '';

      // Clip summary
      const arrClips = track.arrangement_clips || [];
      const sessClips = track.session_clips || [];
      let clipInfo = 'Empty';
      if (arrClips.length > 0) {
        const lenBars = Math.round(Number(arrClips[0].length || 4) / 4);
        clipInfo = `Arr: ${lenBars}b`;
      } else if (sessClips.length > 0) {
        const lenBars = Math.round(Number(sessClips[0].length || 4) / 4);
        clipInfo = `Sess: ${lenBars}b`;
      }

      const row = document.createElement('div');
      row.className = 'stem-row';
      row.innerHTML = `
        <div class="stem-track-info" title="${escapeHtml(track.name)} (${clipInfo})${memoryNote ? ' — ' + escapeHtml(memoryNote) : ''}">
          <span class="confidence-indicator ${confClass}" title="Role confidence"></span>
          <span class="stem-track-name">${escapeHtml(track.name)}</span>
          <span class="stem-source-badge">${clipInfo}</span>
        </div>
        <select class="stem-role-select" data-track-id="${track.id}">
          ${ALL_ROLES.map(r => `<option value="${r}" ${r === role ? 'selected' : ''}>${r}</option>`).join('')}
        </select>
      `;

      const select = row.querySelector('.stem-role-select');
      select.addEventListener('change', (e) => {
        const val = e.target.value;
        userStemOverrides[track.id] = val;
        renderStems();
        drawEnergyCurve();
        rememberRole(track.id, val);
      });

      elStemsContainer.appendChild(row);
    });
  }

  // --- Step 2: Genre Energy Profile & SVG Curve ---
  function genreEntry(genre = selectedGenre) {
    return genreCatalogue.genres.find(g => g.genre === genre) || null;
  }

  function formatSeconds(seconds) {
    const total = Math.round(Number(seconds) || 0);
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
  }

  function liveTempo() {
    return (liveState && Number(liveState.tempo)) ? Number(liveState.tempo) : null;
  }

  // Bars and duration for a variant: the server's map for this Set once loaded, otherwise an estimate.
  function variantFacts(variant) {
    const planned = genreOptions && genreOptions.genre === selectedGenre && genreOptions.variants
      ? genreOptions.variants.find(v => v.id === variant.id) : null;
    if (planned) {
      return { bars: planned.total_bars, duration: formatSeconds(planned.approximate_duration_seconds) };
    }
    const tempo = liveTempo() || 120;
    return { bars: Math.round(variant.target_duration_seconds * tempo / 240), duration: variant.target_duration };
  }

  function renderGenreSelect() {
    elGenreSelect.replaceChildren();
    const families = [];
    genreCatalogue.genres.forEach(g => {
      let group = families.find(f => f.label === g.family);
      if (!group) {
        group = document.createElement('optgroup');
        group.label = g.family || 'Other';
        families.push(group);
        elGenreSelect.appendChild(group);
      }
      const opt = document.createElement('option');
      opt.value = g.genre;
      opt.textContent = g.genre;
      group.appendChild(opt);
    });
    if (!genreEntry()) selectedGenre = genreCatalogue.default_genre || genreCatalogue.genres[0]?.genre || 'House';
    elGenreSelect.value = selectedGenre;
  }

  function populateVariantsDropdown() {
    const entry = genreEntry();
    const variants = entry ? entry.variants : [];
    if (!variants.some(v => v.id === selectedVariant)) {
      selectedVariant = (entry && entry.default_variant) || variants[0]?.id || '';
    }
    elVariantSelect.innerHTML = '';
    variants.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.name} (${variantFacts(v).duration})`;
      if (v.id === selectedVariant) opt.selected = true;
      elVariantSelect.appendChild(opt);
    });
    updateScaffoldButtonLabel();
  }

  function updateScaffoldButtonLabel() {
    const entry = genreEntry();
    const curr = entry ? entry.variants.find(v => v.id === selectedVariant) : null;
    const facts = curr ? variantFacts(curr) : { bars: 144, duration: '4:39' };
    elScaffoldBtnLabel.dataset.whole = `Scaffold ${facts.duration} Arrangement`;
    elScaffoldBtnLabel.textContent = selectedScope ? elScaffoldBtnLabel.textContent : elScaffoldBtnLabel.dataset.whole;

    const tempo = liveTempo();
    const shownTempo = tempo ? Math.round(tempo) : 119;
    const variantMetaSpan = document.getElementById('variantMetaSpan');
    if (variantMetaSpan) {
      let tempoNote = '';
      if (entry && entry.bpm_range) {
        const [low, high] = entry.bpm_range;
        const outside = tempo && (tempo < low - 0.5 || tempo > high + 0.5);
        tempoNote = outside ? ` · usually ${low}–${high} BPM (your Set: ${shownTempo})` : ` · usually ${low}–${high} BPM`;
      }
      variantMetaSpan.textContent = `${selectedGenre} · ${facts.bars} bars (${facts.duration}) · 7 sections${tempoNote}`;
    }
    const statDuration = document.getElementById('statDuration');
    if (statDuration) {
      statDuration.textContent = `${facts.bars} bars (${facts.duration} @ ${shownTempo} BPM)`;
    }
    const statStructure = document.getElementById('statStructure');
    if (statStructure) {
      statStructure.textContent = `${selectedGenre} (${curr ? curr.name : 'Club version'})`;
    }
  }

  async function loadGenreCatalogue() {
    try {
      const catalogue = await api('/api/production/genres');
      if (catalogue && Array.isArray(catalogue.genres) && catalogue.genres.length) {
        genreCatalogue = catalogue;
      }
    } catch (err) {
      console.warn('Failed to fetch the genre list from the server, using the built-in list', err);
    }
    renderGenreSelect();
    populateVariantsDropdown();
  }

  async function loadGenreOptions() {
    try {
      const requestedGenre = selectedGenre;
      const options = await api(`/api/production/arrangement-options`, 'POST', {
        request_id: crypto.randomUUID(),
        genre: requestedGenre
      });
      if (requestedGenre !== selectedGenre) return; // the user switched genre while this was loading
      genreOptions = options;
      populateVariantsDropdown();
      drawEnergyCurve();
    } catch (err) {
      console.warn('Failed to fetch arrangement options from server, using fallback', err);
      drawEnergyCurve();
    }
  }

  function getActiveVariantData() {
    if (genreOptions && genreOptions.variants) {
      const found = genreOptions.variants.find(v => v.id === selectedVariant);
      if (found) return found;
    }
    // Fallback template
    return {
      id: selectedVariant,
      total_bars: 144,
      sections: [
        { id: 'intro', name: 'Intro', start_bar: 0, end_bar: 16, bar_count: 16, energy_level: 2, active_track_roles: ['Kick', 'Hats', 'Atmosphere'], transition_suggestion: 'Filtered pickup' },
        { id: 'groove', name: 'Groove', start_bar: 16, end_bar: 32, bar_count: 16, energy_level: 4, active_track_roles: ['Kick', 'Snare / Clap', 'Hats', 'Bass', 'Chords'], transition_suggestion: 'Introduce bassline' },
        { id: 'main_groove', name: 'Main Groove', start_bar: 32, end_bar: 64, bar_count: 32, energy_level: 6, active_track_roles: ['Kick', 'Snare / Clap', 'Hats', 'Bass', 'Chords', 'Lead', 'Hook'], transition_suggestion: 'Hook statement' },
        { id: 'tension', name: 'Tension', start_bar: 64, end_bar: 80, bar_count: 16, energy_level: 5, active_track_roles: ['Kick', 'Hats', 'Bass', 'FX / Risers'], transition_suggestion: 'Build riser into break' },
        { id: 'breakdown', name: 'Breakdown', start_bar: 80, end_bar: 96, bar_count: 16, energy_level: 3, active_track_roles: ['Chords', 'Lead', 'Hook', 'Atmosphere', 'Vocal'], transition_suggestion: 'Hold back kick until final bar' },
        { id: 'main_section', name: 'Drop / Peak', start_bar: 96, end_bar: 128, bar_count: 32, energy_level: 8, active_track_roles: ['Kick', 'Snare / Clap', 'Hats', 'Percussion', 'Bass', 'Chords', 'Lead', 'Hook', 'Atmosphere', 'Vocal', 'FX / Risers'], transition_suggestion: 'Full energy peak' },
        { id: 'outro', name: 'Outro', start_bar: 128, end_bar: 144, bar_count: 16, energy_level: 3, active_track_roles: ['Kick', 'Hats', 'Bass', 'Atmosphere'], transition_suggestion: 'Strip melodic layers' }
      ]
    };
  }

  // --- Scope: whole arrangement or one section ---
  const elScopeSelect = document.getElementById('scopeSelect');
  const elScopeState = document.getElementById('scopeState');

  function populateScopeDropdown() {
    const names = (getActiveVariantData().sections || []).map(sec => sec.name);
    const wanted = ['', ...names];
    const have = Array.from(elScopeSelect.options).map(o => o.value);
    if (JSON.stringify(wanted) !== JSON.stringify(have)) {
      elScopeSelect.replaceChildren();
      wanted.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name || 'Whole arrangement';
        elScopeSelect.appendChild(opt);
      });
      if (!wanted.includes(selectedScope)) selectedScope = '';
    }
    elScopeSelect.value = selectedScope;
  }

  function scopeIsPlaced() {
    return Boolean(selectedScope && scaffoldedSections[selectedScope]);
  }

  function updateScopeUI() {
    populateScopeDropdown();
    if (!selectedScope) {
      const placed = Object.keys(scaffoldedSections);
      elScopeState.textContent = placed.length ? `In the Set now: ${placed.join(', ')}` : '';
      elScopeState.className = 'scope-state';
      elScaffoldBtnLabel.textContent = elScaffoldBtnLabel.dataset.whole || elScaffoldBtnLabel.textContent;
    } else if (scopeIsPlaced()) {
      elScopeState.textContent = `${selectedScope}: ${scaffoldedSections[selectedScope].clips} clips placed`;
      elScopeState.className = 'scope-state is-placed';
      elScaffoldBtnLabel.textContent = `Re-scaffold ${selectedScope}`;
    } else {
      elScopeState.textContent = `${selectedScope}: not scaffolded yet`;
      elScopeState.className = 'scope-state';
      elScaffoldBtnLabel.textContent = `Scaffold ${selectedScope} only`;
    }
    updateScaffoldButtonState();
  }

  async function refreshScaffoldedSections() {
    try {
      const result = await api(`/api/production/scaffold-sections?genre=${encodeURIComponent(selectedGenre)}&variant_id=${encodeURIComponent(selectedVariant)}`);
      scaffoldedSections = result.sections || {};
    } catch (err) {
      scaffoldedSections = {};
    }
    updateScopeUI();
  }

  elScopeSelect.addEventListener('change', () => {
    selectedScope = elScopeSelect.value;
    updateScopeUI();
  });

  // Drawn at the wrapper's real pixel size (viewBox = CSS size), so text is never stretched.
  const ENERGY_STRIP_HEIGHT = 64;
  const ENERGY_LABEL_ROW = 14;

  function svgEl(tag, attrs) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }

  // Longest form of the section label that fits the section's width (about 5.6px per 9px character).
  function fitSectionLabel(sec, width) {
    const maxChars = Math.floor((width - 6) / 5.6);
    const full = `${sec.name} ${sec.bar_count}b`;
    if (full.length <= maxChars) return full;
    if (sec.name.length <= maxChars) return sec.name;
    if (maxChars >= 4) return sec.name.slice(0, maxChars - 1) + '…';
    return '';
  }

  function drawEnergyCurve() {
    const variantData = getActiveVariantData();
    const sections = variantData.sections || [];
    const totalBars = variantData.total_bars || 144;

    const wrapper = document.getElementById('energyCurveWrapper');
    const svgWidth = Math.max(120, Math.round(wrapper.clientWidth || 800));
    const svgHeight = ENERGY_STRIP_HEIGHT;
    const baseline = svgHeight - ENERGY_LABEL_ROW;
    const usableHeight = baseline - 4;
    elEnergySvg.setAttribute('viewBox', `0 0 ${svgWidth} ${svgHeight}`);

    elSvgGrid.innerHTML = '';
    elSvgSections.innerHTML = '';
    elSvgStroke.setAttribute('d', '');
    elSvgFill.setAttribute('d', '');
    if (sections.length === 0) return;

    elSvgGrid.appendChild(svgEl('line', { x1: 0, x2: svgWidth, y1: baseline, y2: baseline, stroke: '#333333' }));

    const points = [];
    sections.forEach((sec, idx) => {
      const startX = (sec.start_bar / totalBars) * svgWidth;
      const endX = (sec.end_bar / totalBars) * svgWidth;
      const y = baseline - ((sec.energy_level / 10) * usableHeight);

      if (idx === 0) {
        points.push({ x: startX, y });
      } else {
        points.push({ x: startX, y: points[points.length - 1].y });
        points.push({ x: startX, y });
        elSvgGrid.appendChild(svgEl('line', { x1: startX, x2: startX, y1: 0, y2: svgHeight, stroke: '#2e2e2e' }));
      }
      points.push({ x: endX, y });

      // Energy number inside the step, only when the step is wide enough to hold it.
      if (endX - startX >= 14) {
        const energy = svgEl('text', { x: startX + 4, y: Math.min(baseline - 3, y + 11), class: 'energy-level-text' });
        energy.textContent = String(sec.energy_level);
        elSvgGrid.appendChild(energy);
      }

      const label = fitSectionLabel(sec, endX - startX);
      if (label) {
        const text = svgEl('text', { x: startX + 3, y: svgHeight - 3, class: 'energy-section-text' });
        text.textContent = label;
        elSvgGrid.appendChild(text);
      }

      const rect = svgEl('rect', { x: startX, y: 0, width: Math.max(1, endX - startX), height: svgHeight,
                                   class: 'energy-section-rect' });
      rect.addEventListener('mouseenter', (e) => showTooltip(e, sec));
      rect.addEventListener('mousemove', (e) => positionTooltip(e));
      rect.addEventListener('mouseleave', hideTooltip);
      elSvgSections.appendChild(rect);
    });

    const pathD = points.map((pt, i) => `${i ? 'L' : 'M'} ${pt.x} ${pt.y}`).join(' ');
    elSvgStroke.setAttribute('d', pathD);
    elSvgFill.setAttribute('d', `${pathD} L ${svgWidth} ${baseline} L 0 ${baseline} Z`);
  }

  if (typeof ResizeObserver === 'function') {
    let lastWidth = 0;
    new ResizeObserver(entries => {
      const width = Math.round(entries[0].contentRect.width);
      if (width && width !== lastWidth) {
        lastWidth = width;
        drawEnergyCurve();
      }
    }).observe(document.getElementById('energyCurveWrapper'));
  }

  // --- Tooltip Handler ---
  function getAssignedStemRoles() {
    const assigned = new Set();
    const tracks = analysis?.tracks || [];
    tracks.forEach(t => {
      if (t.is_group) return;
      const role = resolveRole(t);
      if (role && role !== 'Ignore / Unknown') {
        assigned.add(role);
      }
    });
    return Array.from(assigned);
  }

  function showTooltip(e, section) {
    const assigned = getAssignedStemRoles();
    const active = section.active_track_roles || [];
    const activeAssigned = active.filter(r => assigned.length === 0 || assigned.includes(r));
    const mutedAssigned = assigned.filter(r => !active.includes(r));

    elTtTitle.textContent = `${section.name} · ${section.bar_count} bars (Bars ${section.start_bar + 1}–${section.end_bar})`;
    elTtEnergy.textContent = `${section.energy_level}/10 ${'■'.repeat(section.energy_level)}${'□'.repeat(10 - section.energy_level)}`;
    elTtActive.textContent = activeAssigned.length ? activeAssigned.join(', ') : (active.join(', ') || 'None');
    elTtMuted.textContent = mutedAssigned.length ? mutedAssigned.join(', ') : 'None';
    elTtTransition.textContent = section.transition_suggestion ? `Transition: ${section.transition_suggestion}` : '';

    elEnergyTooltip.style.display = 'block';
    positionTooltip(e);
  }

  function positionTooltip(e) {
    const wrapper = document.getElementById('energyCurveWrapper');
    const wrapRect = wrapper.getBoundingClientRect();
    let x = e.clientX - wrapRect.left + 12;
    let y = e.clientY - wrapRect.top + 12;

    const ttWidth = elEnergyTooltip.offsetWidth || 200;
    const ttHeight = elEnergyTooltip.offsetHeight || 100;

    if (x + ttWidth > wrapRect.width) {
      x = e.clientX - wrapRect.left - ttWidth - 12;
    }
    if (y + ttHeight > wrapRect.height) {
      y = wrapRect.height - ttHeight - 8;
    }
    if (x < 4) x = 4;
    if (y < 4) y = 4;

    elEnergyTooltip.style.left = `${x}px`;
    elEnergyTooltip.style.top = `${y}px`;
  }

  function hideTooltip() {
    elEnergyTooltip.style.display = 'none';
  }

  // --- Step 3: Scaffold & Rollback Execution ---
  function updateScaffoldButtonState() {
    const isConnected = serverReachable && liveState && liveState.connected;
    const hasTracks = analysis && analysis.tracks && analysis.tracks.length > 0;
    elBtnScaffold.disabled = isBusy || !isConnected || !hasTracks || !workingCopyGate.allowed || !workingCopyConfirmed;
    elBtnRollback.disabled = isBusy || !serverReachable || !(selectedScope ? scopeIsPlaced() : lastAppliedJob) || !workingCopyGate.allowed || !workingCopyConfirmed;
  }

  async function executeScaffold() {
    if (isBusy) return;
    if (!workingCopyGate.allowed) {
      elStatusFeedback.textContent = workingCopyGate.message;
      elStatusFeedback.className = 'status-feedback error';
      return;
    }
    if (!workingCopyConfirmed) {
      elStatusFeedback.textContent = 'Please confirm you are working in a named copy first!';
      elStatusFeedback.className = 'status-feedback error';
      return;
    }

    if (scopeIsPlaced() && !pendingRescaffold) {
      // Re-scaffold = undo exactly that section first (with the usual preview), then plan again.
      pendingRescaffold = true;
      await executeRollback();
      return;
    }

    clearFailure();
    isBusy = true;
    updateScaffoldButtonState();

    try {
      // 1. Analyzing
      updateStepper('analyze');
      elStatusFeedback.textContent = 'Step 1/4: Analyzing Live Set stems & loop boundaries…';
      elStatusFeedback.className = 'status-feedback';
      await refreshAllData();

      // 2. Planning
      updateStepper('plan');
      elStatusFeedback.textContent = 'Step 2/4: Generating subtractive arrangement scaffold plan…';
      
      const scaffoldPayload = {
        genre: selectedGenre,
        variant_id: selectedVariant,
        snapshot_name: `Before ${selectedGenre} ${selectedVariant} Scaffold`,
        roles: userStemOverrides,
        ...(selectedScope ? { section: selectedScope } : {})
      };

      currentPlan = await api('/api/production/plans', 'POST', scaffoldPayload);
      if (!currentPlan || !currentPlan.id) {
        throw new Error('Failed to create arrangement plan');
      }

      // 3. Preview. Nothing has been sent to the bridge yet.
      updateStepper('plan', true);
      showPlanPreview(currentPlan);
      elStatusFeedback.textContent = 'Review the preview, then press Apply to Live.';
    } catch (err) {
      console.error('Scaffold error:', err);
      showFailure(err, 'Could not plan the arrangement.');
      resetStepper();
    } finally {
      isBusy = false;
      updateScaffoldButtonState();
      await refreshAllData();
    }
  }

  // --- Plan preview: colour-blocked tracks x sections ---
  const elPlanPreview = document.getElementById('planPreview');
  const elPlanTimeline = document.getElementById('planTimeline');

  function roleHue(role) {
    let h = 0;
    for (const ch of String(role || '')) h = (h * 31 + ch.charCodeAt(0)) % 360;
    return h;
  }

  function showPlanPreview(plan) {
    const sections = (plan.variant && plan.variant.sections) || [];
    const coverage = plan.source_coverage || [];
    const first = sections.length ? sections[0].start_bar : 0;
    const last = sections.length ? sections[sections.length - 1].end_bar : 0;
    const rows = [];
    coverage.forEach(c => { if (!rows.find(r => r.track === c.track_name)) rows.push({ track: c.track_name, role: c.role }); });

    const only = plan.scaffold_scope && plan.scaffold_scope.section;
    const scoped = only ? sections.find(sec => sec.name === only) : null;
    const barRange = scoped
      ? `${scoped.name} only · bars ${plan.start_bar + scoped.start_bar}–${plan.start_bar + scoped.end_bar - 1}`
      : `bars ${plan.start_bar}–${plan.actual_end_bar}`;
    const copyCount = (plan.actions[0].copies || []).length;
    document.getElementById('planPreviewMeta').textContent =
      `${plan.variant ? plan.variant.name : 'Arrangement'} · ${barRange} · ` +
      `${copyCount} clip ${copyCount === 1 ? 'copy' : 'copies'} on ${rows.length} ${rows.length === 1 ? 'track' : 'tracks'}`;

    elPlanTimeline.replaceChildren();
    const head = document.createElement('div');
    head.className = 'plan-row plan-head';
    head.appendChild(document.createElement('div'));
    const headCells = document.createElement('div');
    headCells.className = 'plan-cells';
    sections.forEach(sec => {
      const cell = document.createElement('div');
      cell.className = 'plan-cell';
      cell.style.flex = `${sec.end_bar - sec.start_bar} 1 0`;
      cell.textContent = sec.name;
      cell.title = `${sec.name}: bars ${sec.start_bar + 1}–${sec.end_bar} of the plan`;
      headCells.appendChild(cell);
    });
    head.appendChild(headCells);
    elPlanTimeline.appendChild(head);

    // Markers: solid when Live will get them, dashed when they are plan-only.
    const markerRow = document.createElement('div');
    markerRow.className = 'plan-row plan-marker-row';
    const markerLabel = document.createElement('div');
    markerLabel.className = 'plan-track-name';
    markerLabel.textContent = plan.locators_deferred ? 'Markers (plan only)' : 'Markers in Live';
    const markerCells = document.createElement('div');
    markerCells.className = 'plan-cells';
    const created = new Set((plan.actions[0].locators || []).map(l => l.time));
    sections.forEach((sec, i) => {
      const def = (plan.locator_definitions || [])[i];
      const cell = document.createElement('div');
      cell.style.flex = `${sec.end_bar - sec.start_bar} 1 0`;
      const willCreate = def && created.has(def.time);
      cell.className = 'plan-marker' + (willCreate ? ' is-created' : (def ? ' is-planned' : ''));
      cell.textContent = def ? def.name : '';
      cell.title = def ? `${def.name} at bar ${Math.round(def.time / 4) + 1}` +
        (willCreate ? ' — will be created in Live' : ' — not created in Live') : '';
      markerCells.appendChild(cell);
    });
    markerRow.appendChild(markerLabel);
    markerRow.appendChild(markerCells);
    elPlanTimeline.appendChild(markerRow);

    rows.forEach(row => {
      const el = document.createElement('div');
      el.className = 'plan-row';
      const label = document.createElement('div');
      label.className = 'plan-track-name';
      label.textContent = row.track;
      label.title = `${row.track} (${row.role})`;
      const cells = document.createElement('div');
      cells.className = 'plan-cells';
      sections.forEach(sec => {
        const bars = sec.end_bar - sec.start_bar;
        const entry = coverage.find(c => c.track_name === row.track && c.section === sec.name);
        const cell = document.createElement('div');
        cell.style.flex = `${bars} 1 0`;
        cell.style.setProperty('--hue', roleHue(row.role));
        if (!entry || entry.placed_bars <= 0) {
          cell.className = 'plan-cell';
          cell.title = `${sec.name}: ${row.track} is silent`;
        } else if (entry.placed_bars < bars) {
          cell.className = 'plan-cell is-partial';
          cell.title = `${sec.name}: ${entry.placed_bars} of ${bars} bars filled`;
        } else {
          cell.className = 'plan-cell is-full';
          cell.title = `${sec.name}: ${row.track} plays all ${bars} bars`;
        }
        cells.appendChild(cell);
      });
      el.appendChild(label);
      el.appendChild(cells);
      elPlanTimeline.appendChild(el);
    });

    const gapBySection = {};
    (plan.section_gaps || []).forEach(g => { gapBySection[g.section] = g; });
    if (Object.keys(gapBySection).length) {
      const gapRow = document.createElement('div');
      gapRow.className = 'plan-row';
      const gapLabel = document.createElement('div');
      gapLabel.className = 'plan-track-name';
      gapLabel.textContent = 'Gaps';
      const gapCells = document.createElement('div');
      gapCells.className = 'plan-cells';
      sections.forEach(sec => {
        const g = gapBySection[sec.name];
        const cell = document.createElement('div');
        cell.style.flex = `${sec.end_bar - sec.start_bar} 1 0`;
        cell.className = 'plan-cell' + (g ? ' is-gap' : '');
        cell.title = g
          ? (g.empty ? `${sec.name}: nothing fits, left empty` : `${sec.name}: up to ${g.max_unfilled_bars} of ${g.section_bars} bars unfilled`)
          : `${sec.name}: filled`;
        gapCells.appendChild(cell);
      });
      gapRow.appendChild(gapLabel);
      gapRow.appendChild(gapCells);
      elPlanTimeline.appendChild(gapRow);
    }

    const notes = document.getElementById('planNotes');
    notes.replaceChildren();
    [...(plan.gaps || []), plan.boundary_summary, ...(plan.warnings || [])].filter(Boolean).forEach(text => {
      const li = document.createElement('li');
      li.textContent = text;
      notes.appendChild(li);
    });
    elPlanPreview.hidden = false;
  }

  function hidePlanPreview() {
    elPlanPreview.hidden = true;
  }

  // Step 2 of the flow: only now is anything sent to the bridge.
  async function applyPlan() {
    if (isBusy || !currentPlan) return;
    if (!workingCopyGate.allowed || !workingCopyConfirmed) {
      elStatusFeedback.textContent = workingCopyGate.allowed ? 'Please confirm the working copy first.' : workingCopyGate.message;
      elStatusFeedback.className = 'status-feedback error';
      return;
    }
    hidePlanPreview();
    clearFailure();
    isBusy = true;
    updateScaffoldButtonState();
    try {
      updateStepper('place');
      elStatusFeedback.textContent = 'Step 3/4: Applying clip copies to timeline…';
      elStatusFeedback.className = 'status-feedback';
      const job = await api('/api/production/apply', 'POST', { plan_id: currentPlan.id, working_copy_confirmed: true });
      lastAppliedJob = job;

      updateStepper('verify');
      elStatusFeedback.textContent = 'Step 4/4: Verifying arrangement readback from Live…';
      let verified = false;
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 600));
        const statusData = await api(`/api/production/status/${job.id}`);
        if (statusData.status === 'Applied') {
          verified = true;
          lastAppliedJob = statusData;
          break;
        } else if (statusData.status === 'Failed' || statusData.status === 'Interrupted' || statusData.status === 'Partial failure') {
          throw jobFailure(statusData, `Execution failed with status: ${statusData.status}`);
        }
      }
      if (verified) {
        updateStepper('verify', true);
        const created = (lastAppliedJob?.execution?.created_copies || []).length;
        const placedText = created ? `${created} clip ${created === 1 ? 'copy' : 'copies'}` : 'the clips';
        elStatusFeedback.textContent = `✓ Verified in Live! Placed ${placedText}. 1-click Undo active.`;
        elStatusFeedback.className = 'status-feedback success';
      } else {
        elStatusFeedback.textContent = 'Queued to Live. Check arrangement view.';
      }
    } catch (err) {
      console.error('Apply error:', err);
      // A partial failure leaves real clips in the Set: keep Undo available for exactly those.
      if (err.job && err.explanation && err.explanation.undo_available) lastAppliedJob = err.job;
      showFailure(err, 'Could not apply the arrangement.');
      resetStepper();
    } finally {
      isBusy = false;
      updateScaffoldButtonState();
      await refreshAllData();
    }
  }

  document.getElementById('btnPlanApply').addEventListener('click', applyPlan);
  document.getElementById('btnPlanCancel').addEventListener('click', () => {
    hidePlanPreview();
    currentPlan = null;
    resetStepper();
    elStatusFeedback.textContent = 'Preview cancelled. Nothing was written to Live.';
  });

  const elRollbackPreview = document.getElementById('rollbackPreview');
  const elRollbackPreviewText = document.getElementById('rollbackPreviewText');

  function rollbackRequest(extra) {
    if (selectedScope) {
      return api('/api/production/rollback', 'POST', {
        working_copy_confirmed: true, section: selectedScope, genre: selectedGenre, variant_id: selectedVariant, ...extra
      });
    }
    const body = { job_id: lastAppliedJob.id, working_copy_confirmed: true, ...extra };
    const route = currentPlan && currentPlan.id ? `/api/production/plans/${currentPlan.id}/rollback` : '/api/production/rollback';
    return api(route, 'POST', body);
  }

  // Step 1: dry run. Nothing is sent to Live; the user sees exactly what would be removed.
  async function executeRollback() {
    if (isBusy || !(selectedScope ? scopeIsPlaced() : lastAppliedJob)) return;
    if (!workingCopyConfirmed) {
      elStatusFeedback.textContent = 'Confirm working copy before rollback.';
      elStatusFeedback.className = 'status-feedback error';
      return;
    }
    try {
      const preview = await rollbackRequest({ dry_run: true });
      elRollbackPreviewText.textContent = preview.dry_run ? preview.summary : 'Ready to undo.';
      elRollbackPreview.hidden = false;
      elStatusFeedback.textContent = '';
      clearFailure();
    } catch (err) {
      showFailure(err, 'Could not prepare the undo.');
    }
  }

  // Step 2: the user confirmed the preview; queue the real rollback.
  async function confirmRollback() {
    if (isBusy || !(selectedScope ? scopeIsPlaced() : lastAppliedJob)) return;
    elRollbackPreview.hidden = true;
    isBusy = true;
    updateScaffoldButtonState();
    elStatusFeedback.textContent = 'Queuing rollback…';
    elStatusFeedback.className = 'status-feedback';

    try {
      const rollbackResult = await rollbackRequest({});
      let message = null;
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 500));
        const statusData = await api(`/api/production/status/${rollbackResult.id}`);
        if (statusData.status === 'Applied') {
          message = statusData.message || 'Undo completed.';
          break;
        } else if (statusData.status === 'Failed' || statusData.status === 'Partial failure') {
          throw jobFailure(statusData, 'Rollback execution failed');
        }
      }
      if (message === null) throw new Error('Rollback was queued but Live has not confirmed it yet. Refresh to check.');

      if (!selectedScope) lastAppliedJob = null;
      currentPlan = null;
      resetStepper();
      elStatusFeedback.textContent = `✓ ${message}`;
      elStatusFeedback.className = 'status-feedback success';
      if (pendingRescaffold) {
        // The user asked to re-scaffold: the section is now clear, so plan it again.
        pendingRescaffold = false;
        await refreshScaffoldedSections();
        isBusy = false;
        await executeScaffold();
        return;
      }
    } catch (err) {
      console.error('Rollback error:', err);
      showFailure(err, 'The undo did not finish.');
    } finally {
      isBusy = false;
      updateScaffoldButtonState();
      await refreshAllData();
    }
  }

  document.getElementById('btnRollbackConfirm').addEventListener('click', confirmRollback);
  document.getElementById('btnRollbackCancel').addEventListener('click', () => { elRollbackPreview.hidden = true; pendingRescaffold = false; });

  // --- Pop Out Handler ---
  async function triggerPopout() {
    // Inside Max the device's own jweb has no popup windows: window.open (or a max: URL) would load the
    // pop-out page into the docked panel itself, which then hides its Pop Out button for good. So in Max,
    // only ask the patch to show its floating window.
    if (window.max && typeof window.max.outlet === 'function') {
      try {
        window.max.outlet('open_popout', 1);
      } catch (e) {
        console.warn('Max popout request:', e);
      }
      return;
    }
    // In a normal browser: ask the server, then open a popup window.
    try {
      await fetch('/api/popout', { method: 'POST' });
    } catch (e) {
      console.warn('Backend popout request:', e);
    }
    try {
      const popoutUrl = `${window.location.origin}/arranger_device.html?popout=1`;
      window.open(popoutUrl, 'VibeltonArrangerStudio', 'width=1120,height=680,menubar=no,toolbar=no,location=no,status=no');
    } catch (e) {}
  }

  // --- Versions and stale-install warnings ---
  const elVersionInfo = document.getElementById('versionInfo');
  const elVersionWarn = document.getElementById('btnVersionWarn');
  const elVersionPanel = document.getElementById('versionPanel');
  const elVersionPanelBody = document.getElementById('versionPanelBody');
  let versionData = null;

  function shortVersion(v) { return v ? String(v) : '?'; }

  function renderVersions() {
    if (!versionData) {
      elVersionInfo.textContent = '';
      elVersionWarn.hidden = true;
      return;
    }
    const d = versionData.device || {}, b = versionData.bridge || {};
    elVersionInfo.textContent = `Device ${shortVersion(d.loaded || d.repo)} · Bridge ${shortVersion(b.running)} · Server ${shortVersion(versionData.server_version)}`;
    const warnings = versionData.warnings || [];
    elVersionWarn.hidden = warnings.length === 0;
    elVersionWarn.textContent = warnings.length === 1 ? '⚠ Update' : `⚠ ${warnings.length} updates`;

    elVersionPanelBody.replaceChildren();
    const heading = document.createElement('div');
    heading.innerHTML = `<b>Versions</b> — device loaded in Live: <code></code> · device on disk: <code></code> · bridge running: <code></code> / installed: <code></code> · server: <code></code>`;
    const codes = heading.querySelectorAll('code');
    [d.loaded || 'not reported', d.repo, b.running || 'not connected', b.installed, versionData.server_version]
      .forEach((value, i) => { codes[i].textContent = shortVersion(value); });
    elVersionPanelBody.appendChild(heading);
    if (warnings.length) {
      const list = document.createElement('ul');
      warnings.forEach(w => {
        const li = document.createElement('li');
        li.append(w.message + ' ');
        const fix = document.createElement('span');
        fix.className = 'fix';
        fix.textContent = w.fix;
        li.appendChild(fix);
        list.appendChild(li);
      });
      elVersionPanelBody.appendChild(list);
    } else {
      const ok = document.createElement('div');
      ok.textContent = 'Everything matches.';
      elVersionPanelBody.appendChild(ok);
    }
  }

  async function refreshVersions() {
    try {
      versionData = await api('/api/versions');
    } catch (err) {
      versionData = null;
    }
    renderVersions();
  }

  elVersionWarn.addEventListener('click', () => { elVersionPanel.hidden = !elVersionPanel.hidden; });
  document.getElementById('btnVersionClose').addEventListener('click', () => { elVersionPanel.hidden = true; });

  // --- Offline state ---
  const elOfflineBanner = document.getElementById('offlineBanner');
  const elOfflineMessage = document.getElementById('offlineMessage');
  const elLogPath = document.getElementById('logPathText');

  function setServerOffline(offline) {
    serverReachable = !offline;
    elOfflineBanner.hidden = !offline;
    if (offline) {
      elOfflineMessage.textContent = 'Server offline — Vibelton is not answering on this machine.';
      // Drop everything read from the dead server so no stale stems or sections stay actionable.
      liveState = null;
      analysis = null;
      activeRoles = null;
      scaffoldedSections = {};
      selectedScope = '';
      renderStems();
      updateScopeUI();
    } else {
      elLogPath.hidden = true;
    }
  }

  document.getElementById('btnRetry').addEventListener('click', () => {
    // Inside Max, ask the device to restart the server; then re-check.
    if (window.max && typeof window.max.outlet === 'function') window.max.outlet('retry');
    refreshAllData();
  });
  document.getElementById('btnShowLog').addEventListener('click', () => {
    elLogPath.hidden = !elLogPath.hidden;
  });

  // --- Main Refresh ---
  async function refreshAllData() {
    try {
      const statusRes = await api('/api/status');
      setServerOffline(false);
      liveState = statusRes.state || {};
      
      const isConnected = Boolean(liveState.connected);
      const tempo = Math.round(Number(liveState.tempo || 120));

      if (isConnected) {
        elConnectionPill.className = 'connection-pill is-connected';
        elConnectionText.textContent = `● Connected ${tempo} BPM`;
        if (tempo !== lastLabelTempo) {
          lastLabelTempo = tempo;
          updateScaffoldButtonLabel(); // the tempo hint and bar estimate depend on the Set's tempo
        }
      } else {
        elConnectionPill.className = 'connection-pill is-offline';
        elConnectionText.textContent = `Offline (Live closed)`;
      }

      // Fetch production analysis
      try {
        analysis = await api('/api/production/analysis');
        activeRoles = await api('/api/production/track-roles').catch(() => null);
        await refreshRoleMemory();
      } catch (err) {
        // Fallback analysis if bridge is in snapshot state
        analysis = {
          tracks: liveState.tracks || [],
          project: {
            tempo: liveState.tempo || 120,
            metre: liveState.metre || [4, 4],
            arrangement_readable: liveState.arrangement_readable
          }
        };
      }

      updateSafetyUI(await api('/api/production/working-copy').catch(() => null));
      renderStems();
      drawEnergyCurve();
      updateScaffoldButtonState();
      await refreshScaffoldedSections();
    } catch (err) {
      elConnectionPill.className = 'connection-pill is-offline';
      // fetch() rejects with TypeError when nothing is listening.
      if (err instanceof TypeError) {
        setServerOffline(true);
        elConnectionText.textContent = 'Server offline';
        elStatusFeedback.textContent = '';
      } else {
        elConnectionText.textContent = 'Server error';
        showFailure(err, 'Could not read Vibelton status.');
      }
    }
  }

  // --- Event Listeners ---
  elBtnRefresh.addEventListener('click', () => {
    refreshAllData();
  });

  elBtnPopout.addEventListener('click', () => {
    triggerPopout();
  });

  elGenreSelect.addEventListener('change', (e) => {
    selectedGenre = e.target.value;
    genreOptions = null;
    selectedVariant = genreEntry()?.default_variant || '';
    populateVariantsDropdown();
    drawEnergyCurve();
    loadGenreOptions();
    refreshScaffoldedSections();
  });

  elVariantSelect.addEventListener('change', (e) => {
    selectedVariant = e.target.value;
    updateScaffoldButtonLabel();
    drawEnergyCurve();
  });

  elWorkingCopyCheck.addEventListener('change', (e) => {
    workingCopyConfirmed = e.target.checked;
    sessionStorage.setItem(STORAGE_KEY_CONFIRMED, workingCopyConfirmed ? 'true' : 'false');
    updateScaffoldButtonState();
  });

  elBtnScaffold.addEventListener('click', executeScaffold);
  elBtnRollback.addEventListener('click', executeRollback);

  // --- Check URL Params (Popout mode detection) ---
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('popout') === '1') {
    document.body.classList.add('is-popout');
    elBtnPopout.style.display = 'none'; // Hide Pop Out button inside popout window
  }

  // --- In-page menus for <select> ---
  // Max's jweb delivers clicks but cannot open the native <select> pop-up list, so inside Max (or with
  // ?selectmenu=1 for testing in a browser) clicking a select opens this menu instead. Choosing an item
  // sets the select's value and fires a bubbling 'change' event, so existing listeners work unchanged.
  function installSelectMenus() {
    let menu = null;

    function close() {
      if (menu) {
        menu.remove();
        menu = null;
      }
    }

    function open(select) {
      menu = document.createElement('div');
      menu.className = 'select-menu';
      menu.setAttribute('role', 'listbox');
      let lastGroup = null;
      Array.from(select.options).forEach(option => {
        const group = option.parentElement && option.parentElement.tagName === 'OPTGROUP' ? option.parentElement : null;
        if (group && group !== lastGroup) {
          const header = document.createElement('div');
          header.className = 'select-menu-group';
          header.textContent = group.label;
          menu.appendChild(header);
        }
        lastGroup = group;
        const item = document.createElement('div');
        item.className = 'select-menu-item';
        item.setAttribute('role', 'option');
        item.classList.toggle('is-selected', option.selected);
        item.classList.toggle('is-disabled', option.disabled);
        item.textContent = option.textContent;
        item.addEventListener('mousedown', (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (option.disabled) return;
          if (select.value !== option.value) {
            select.value = option.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
          }
          close();
        });
        menu.appendChild(item);
      });
      document.body.appendChild(menu);

      // Below the select if it fits, otherwise wherever there is more room; never off-screen.
      const rect = select.getBoundingClientRect();
      const below = window.innerHeight - rect.bottom - 4;
      const above = rect.top - 4;
      const natural = menu.scrollHeight;
      const placeBelow = natural <= below || below >= above;
      const maxHeight = Math.max(48, placeBelow ? below : above);
      menu.style.maxHeight = `${maxHeight}px`;
      menu.style.minWidth = `${rect.width}px`;
      const height = Math.min(natural, maxHeight);
      menu.style.top = `${placeBelow ? rect.bottom + 2 : rect.top - 2 - height}px`;
      menu.style.left = `${Math.max(4, Math.min(rect.left, window.innerWidth - menu.offsetWidth - 4))}px`;
      // Scroll only the menu itself: scrolling the page would close it.
      const selected = menu.querySelector('.is-selected');
      if (selected) menu.scrollTop = Math.max(0, selected.offsetTop - menu.clientHeight / 2);
    }

    document.addEventListener('mousedown', (event) => {
      if (menu && menu.contains(event.target)) return;
      const select = event.target.closest ? event.target.closest('select') : null;
      const wasOpenFor = menu && menu.dataset.for;
      close();
      if (!select || select.disabled) return;
      event.preventDefault();
      select.focus({ preventScroll: true });
      if (wasOpenFor && wasOpenFor === (select.id || select.name || '')) return; // second click closes
      open(select);
      menu.dataset.for = select.id || select.name || '';
    }, true);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });
    document.addEventListener('scroll', (event) => {
      if (menu && !menu.contains(event.target)) close();
    }, true);
    // No close on window blur: in Max, clicking the panel hands focus back to Live, which blurs the page
    // straight after the menu opens.
    window.addEventListener('resize', () => close());
  }

  if ((window.max && typeof window.max.outlet === 'function') || urlParams.get('selectmenu') === '1') {
    installSelectMenus();
  }

  // --- Initialization ---
  renderGenreSelect();
  populateVariantsDropdown();
  refreshAllData();
  loadGenreCatalogue().then(loadGenreOptions);

  refreshVersions();
  setInterval(refreshVersions, 30000);

  // Periodic heartbeat every 3 seconds
  setInterval(refreshAllData, 3000);
})();
