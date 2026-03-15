# TODO

## Completed
- [x] Phase 0: Prerequisites (accounts, ffmpeg, .env)
- [x] Phase 1: Project init with uv
- [x] Phase 2: Scenario definitions (`src/scenarios.py` — 12 scenarios)
- [x] Phase 3: Server + bot pipeline (all code written + CTO reviewed)
  - [x] `src/recorder.py` — MP3 + transcript saving
  - [x] `src/bot.py` — Pipecat pipeline (3 CTO review rounds: 10 bugs fixed total)
  - [x] `src/server.py` — FastAPI + ngrok + Twilio (CTO review: 2 bugs fixed)
  - [x] `run.py` — CLI entry point (Windows asyncio + uvicorn + scenario menu)

## In Progress
- [ ] Phase 3 wrap-up
  - [x] Write `docs/code_walkthrough.md` — plain-language code explanation
  - [ ] Commit + push Phase 3 (walkthrough, task updates)

## Remaining
- [ ] Phase 4: First test call — verify end-to-end
  - [ ] Call connects to +1-805-439-8008 via Twilio
  - [ ] Bot hears receptionist greeting, responds in character
  - [ ] MP3 recording saved with both voices audible
  - [ ] Transcript captures both sides with timestamps
  - [ ] Tune VAD `stop_secs` if bot interrupts too early
- [ ] Phase 5: CLI testing — run `uv run python run.py`, test scenario menu
- [ ] Phase 6: Execute 10+ calls across all scenarios
  - [ ] Commit recordings + transcripts in batches
  - [ ] Note bugs/quality issues for bug report
- [ ] Phase 7: Documentation + bug report
  - [ ] `docs/architecture.md` — 1-2 paragraph design overview
  - [ ] `docs/bug_report.md` — bugs found with recording references
  - [ ] Update `README.md` — setup + run instructions
  - [ ] Record Loom video (max 5 min)
