# TODO

- [x] Phase 0: Prerequisites (accounts, ffmpeg, .env)
- [x] Phase 1: Project init with uv
- [x] Phase 2: Scenario definitions (`src/scenarios.py`)
- [ ] Phase 3: Server + bot pipeline
  - [x] `src/recorder.py` — MP3 + transcript saving
  - [x] `src/bot.py` — Pipecat pipeline (CTO reviewed, bugs fixed)
  - [ ] `src/server.py` — FastAPI + ngrok + Twilio call initiation
  - [ ] `run.py` — Entry point (Windows asyncio + uvicorn)
  - [ ] CTO review `server.py` and `run.py`
  - [ ] `docs/code_walkthrough.md` — Plain-language code explanation
  - [ ] Commit + push Phase 3
- [ ] Phase 4: Recording + transcripts (built into bot.py — verify with test call)
- [ ] Phase 5: CLI runner (scenario selection menu)
- [ ] Phase 6: Execute 10+ calls
- [ ] Phase 7: Bug report + docs (architecture.md, bug_report.md, README.md)
