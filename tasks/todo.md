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
  - [x] Write `docs/code_walkthrough.md` — plain-language code explanation

## In Progress
- [ ] Phase 4: First test call — debug and iterate
  - [x] Call connects to +1-805-439-8008 via Twilio
  - [x] Bot hears receptionist greeting, responds in character
  - [x] Fix PipelineRunner SIGINT crash on Windows (handle_sigint=False)
  - [x] Fix audio_in/out_enabled defaults (were False, now True)
  - [x] Fix stage directions being spoken aloud (system prompt + TTS)
  - [x] Fix hardcoded doctor names/times (reactive prompts)
  - [x] Fix Deepgram STT encoding mismatch (removed mulaw, TwilioFrameSerializer handles conversion)
  - [x] Add SilenceFilter processor to drop "(silence)" / "..." from TTS
  - [x] Fix SilenceFilter StartFrame handling (must call super().process_frame)
  - [x] Tune VAD stop_secs from 0.6 → 1.0 to reduce interruptions
  - [x] Increase call time_limit from 180s → 300s (calls were cutting off at 3min)
  - [x] Fix silence rule too aggressive (only apply to FINAL sentence, not whole turn)
  - [x] Add live transcript logging to terminal
  - [x] Add saved files summary on quit
  - [ ] **BUG: Recordings and transcripts still not saving locally** — try/finally in bot.py should save, but files aren't appearing. Needs debugging next session.
  - [ ] **Personas too rigid / not reactive enough** — bot assumes info (doctor names, appointment types) before receptionist confirms. System prompts need to be more open-ended and purely reactive. The patient should ONLY reference information the receptionist has explicitly stated. Consider making context more dynamic or simplifying persona goals to just "I want to schedule an appointment" without pre-loading specific details.
  - [ ] **Response gap too large** — VAD stop_secs=1.0 causes noticeable delay between receptionist finishing and bot responding. Try tuning down to 0.7-0.8 for a more natural cadence.
  - [ ] Tune conversation naturalness — bot still sounds somewhat robotic
  - [ ] Verify MP3 recording captures both voices
  - [ ] Verify transcript file saves with timestamps

## Remaining
- [ ] Phase 5: Execute 10+ calls across all scenarios
  - [ ] Run all 12 scenarios
  - [ ] Commit recordings + transcripts in batches
  - [ ] Note bugs/quality issues for bug report
- [ ] Phase 6: Documentation + bug report
  - [ ] `docs/architecture.md` — 1-2 paragraph design overview
  - [ ] `docs/bug_report.md` — bugs found with recording references
  - [ ] Update `README.md` — setup + run instructions
  - [ ] Record Loom video (max 5 min)
