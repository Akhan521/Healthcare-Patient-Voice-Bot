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
  - [x] **BUG: Recordings and transcripts not saving locally** — fixed. Two structural problems: (1) start_recording() raced StartFrame propagation, moved into on_client_connected; (2) runner.run() hangs on WebSocket disconnect, added on_client_disconnected handler to save inline + cancel task.
  - [x] **Run first test call (scenario 01 — knee pain eval)** — done, validated rules 8 and 9 work correctly. Bot waited for greeting, stayed in scope, sounded much smoother at stop_secs=0.8.
  - [x] **Auto-return to menu (no manual ENTER)** — fixed. Replaced unreliable Twilio status polling with a threading.Event signalled from the WebSocket handler's finally block.
  - [x] Verify MP3 recording captures both voices (1.2MB MP3 written, 2.5MB raw audio)
  - [x] Verify transcript file saves with timestamps (2.6KB transcript with [mm:ss] timestamps for 41+ turns)
  - [x] **Tune voice naturalness** — VAD/LLM tuning deferred (low yield per analysis). Applied two higher-leverage changes:
    - **Voice swaps (commit 1605a3c):** Recast 8 of 12 scenarios against live Deepgram Aura 2 catalog. Eliminated 3 duplicate voices (helena, hermes, apollo each used twice) and corrected 4 age/tone mismatches (Robert 62 → mars baritone, Dorothy 72 → pandora calm/breathy, Tony impatient → saturn, etc.). All 12 scenarios now have unique voices with persona-fit descriptors.
    - **Prompt phrasing (commits 4ef95d8, 2eb2eee):** Expanded SYSTEM_PREAMBLE rule #2 with sentence-fragment + self-correction guidance. Added one-sentence "Tics:" fingerprint to each of the 12 personas (signature filler phrases + tonal cue) so each persona has its own speech fingerprint. Conservative phrasing for Dorothy and Priya to avoid TTS pronouncing literal "haha" or over-fragmenting speech.

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
