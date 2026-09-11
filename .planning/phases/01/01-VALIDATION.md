---
phase: 1
slug: house-sub-genre-expansion
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tests/` directory (existing) |
| **Quick run command** | `python -m pytest tests/test_genre_dna.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_genre_dna.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| genre-dna | 01 | 1 | SPEC §3 | — | N/A | unit | `python -m pytest tests/test_genre_dna.py -x -q` | ✅ | ⬜ pending |
| planner | 01 | 1 | SPEC §4 | — | N/A | unit | `python -m pytest tests/test_genre_dna.py tests/test_harmony.py -x -q` | ✅ | ⬜ pending |
| genre-card-ui | 02 | 2 | SPEC §5 | — | N/A | manual | Manual browser check at http://127.0.0.1:8765 | ✅ | ⬜ pending |
| listening-gate | 03 | 3 | SPEC §6 (AC-7) | — | N/A | manual | Generate 1 Deep House + 1 Tech House sketch, fill LISTENING_NOTES.md | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `tests/test_genre_dna.py` — add stubs for Deep House + Tech House registry tests (AC-1 through AC-4)
- [ ] Existing `tests/` infrastructure covers pytest setup — no new install required

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Genre cards render and click correctly | SPEC §5 (AC-5) | Browser DOM interaction | Open http://127.0.0.1:8765, verify House card expands to show Deep House and Tech House; click each, confirm prompt populates |
| Zero genre vocabulary required | SPEC §5 (AC-6) | Human judgment | Jim reads card labels cold without music knowledge context |
| Deep House sketch sounds soulful / late-night | SPEC §6 (AC-7) | Listening test | Generate sketch, fill LISTENING_NOTES.md, mark PASS |
| Tech House sketch sounds dark / peak-hour | SPEC §6 (AC-7) | Listening test | Generate sketch, fill LISTENING_NOTES.md, mark PASS |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (Plan 01-01 creates stubs)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-22
