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
  - [x] **Personas too rigid / not reactive enough** — rewrote SYSTEM_PREAMBLE rule #3 to enforce purely reactive behavior; simplified each persona to state only high-level goal, moved all specifics (DOB, insurance, med names) behind "ONLY if asked"
  - [x] **Response gap too large** — VAD stop_secs 1.0 → 0.8 for more natural cadence
  - [x] **Reframe personas for orthopedics target** — 7 of 12 scenarios rewritten as ortho-fit (knee pain, post-op follow-ups, meloxicam refill, rolled ankle, etc.); 4 kept domain-neutral; 1 (pet pivot) kept as deliberate off-domain edge case
  - [x] **Personas bulldoze past receptionist's framing** — added preamble rule 8 (listen to greeting, answer specific questions first, work within announced scope, follow test-call instructions) and rule 9 (remember and respect what receptionist said earlier). Softened all personas from "Open by..." → "When invited to speak, say..." Scenarios 10 and 11 explicitly told to drop items the receptionist marks out of scope.
  - [ ] **BUG: Recordings and transcripts still not saving locally** — TOP PRIORITY next session. Add debug logging inside the try/finally and the on_audio_data handler to trace whether stop_recording() is actually triggering the callback. If the event doesn't fire, try calling save_recording directly in the finally block.
  - [ ] **Run first test call (scenario 01 — knee pain eval)** to validate the preamble/persona rewrite before running the rest
  - [ ] **Tune voice naturalness** — bot still sounds somewhat robotic. User plans to experiment with TTS voice alternatives, VAD timing, LLM temperature, and possibly prompt phrasing tweaks.
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
