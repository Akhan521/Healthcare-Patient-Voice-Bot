# Lessons Learned

## 1. Always CTO-review code before committing (2026-03-12)
**What happened:** First draft of `bot.py` had 4 CRITICAL bugs — wrong event handler names, VAD in wrong params, missing transcript processor. All would have silently failed at runtime.
**Rule:** Never trust that event handler names, constructor params, or API signatures are correct from memory. Always verify against actual docs/source before finalizing code. Run a CTO review agent on non-trivial code.

## 2. Pipecat event handlers are NOT guessable (2026-03-12)
**What happened:** Guessed `on_task_completed`, `on_receive_transcript`, `on_llm_response_text` — none of them exist.
**Correct names:**
- Task completion: `on_pipeline_finished(task, frame)`
- Transcript capture: Use `TranscriptProcessor` with `on_transcript_update`
- No direct events on transport or LLM for text capture
**Rule:** For any Pipecat event handler, check the docs first. Don't guess.

## 3. VAD analyzer goes in transport params, not pipeline params (2026-03-12)
**What happened:** Put `vad_analyzer=vad` in `PipelineParams` — it's actually a `FastAPIWebsocketParams` parameter.
**Rule:** VAD is a transport-level concern in Pipecat, not pipeline-level.

## 4. VADParams is a standalone import (2026-03-12)
**What happened:** Used `SileroVADAnalyzer.VADParams` as if it were a nested class — it's not.
**Correct:** `from pipecat.audio.vad.vad_analyzer import VADParams`

## 5. parse_telephony_websocket returns stream_id/call_id, NOT stream_sid/call_sid (2026-03-13)
**What happened:** Used `call_data.get("stream_sid")` — the actual keys are `"stream_id"` and `"call_id"`. Would have caused None values passed to TwilioFrameSerializer.
**Rule:** Pipecat normalizes Twilio's `streamSid`/`callSid` to `stream_id`/`call_id`. Always use the normalized names.

## 6. pyngrok has no disconnect_all() (2026-03-13)
**What happened:** Called `ngrok.disconnect_all()` which doesn't exist. Only `ngrok.disconnect(url)` and `ngrok.kill()` exist.
**Rule:** For cleanup, just use `ngrok.kill()` — it terminates the entire ngrok process.

## 7. LLMContextAggregatorPair doesn't exist yet — use create_context_aggregator (2026-03-14)
**What happened:** Used `from pipecat.processors.aggregators.llm_context import LLMContextAggregatorPair` — class doesn't exist in v0.0.105. Deprecation warnings reference it as future API but it's not implemented.
**Correct pattern:**
```python
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
context = OpenAILLMContext(messages=[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}])
context_agg = llm.create_context_aggregator(context)
# Use context_agg.user() and context_agg.assistant() in pipeline
```
**Rule:** In Pipecat v0.0.105, `OpenAILLMContext` is the universal context class for ALL providers. `llm.create_context_aggregator()` returns provider-specific aggregators.

## 8. system_instruction in Settings only works with LLMContext, not OpenAILLMContext (2026-03-14)
**What happened:** Set `system_instruction=scenario.system_prompt` in `AnthropicLLMService.Settings`. It was silently ignored because `_get_llm_invocation_params` only injects `system_instruction` for `LLMContext` instances, not for `OpenAILLMContext`/`AnthropicLLMContext`.
**Correct:** Put the system prompt in `OpenAILLMContext(messages=[{"role": "system", ...}, ...])` with at least 2 messages. A single system message gets misinterpreted as a user message.
**Rule:** Always verify how Settings params are used in `_get_llm_invocation_params` — the behavior differs by context type.

## 9. TranscriptProcessor has .assistant(), NOT .assistant_tts() (2026-03-14)
**What happened:** Used `transcript_proc.assistant_tts()` — method doesn't exist. Only `.user()` and `.assistant()` exist.
**Rule:** Don't guess method names. Check with `dir()` or source inspection.

## 10. Deprecated import paths in Pipecat v0.0.105 (2026-03-14)
**Deprecated → Correct:**
- `pipecat.services.anthropic` → `pipecat.services.anthropic.llm`
- `pipecat.transports.network.fastapi_websocket` → `pipecat.transports.websocket.fastapi`
**Rule:** Use the non-deprecated paths to avoid runtime warnings.

## 12. Always verify API details with live docs, not training data (2026-03-26)
**What happened:** Code used model ID `claude-haiku-4-5-20250315` — a date suffix that doesn't exist. The valid IDs are `claude-haiku-4-5` (alias) or `claude-haiku-4-5-20251001` (pinned). This was written from memory during initial implementation and never caught across 3 CTO review rounds because the reviews checked Pipecat patterns, not upstream provider constants.
**How it was caught:** Full API verification pass using Context7 MCP server and the `get-api-docs` skill to pull live documentation for every third-party dependency (Pipecat, Twilio, Deepgram, Anthropic, pyngrok).
**Rule:** Before finalizing any code that uses third-party APIs, verify model IDs, parameter names, and function signatures against live documentation — not training data or memory. Use the `get-api-docs` skill or Context7 MCP to fetch current docs. This is especially important for:
- Model IDs and version strings (they change with releases)
- SDK parameter names (they get renamed between versions)
- Event handler names (framework-specific, not guessable)
- Voice/model catalog names (providers add/remove these regularly)

## 13. TranscriptProcessor is deprecated in Pipecat v0.0.105 (2026-03-26)
**What happened:** API verification revealed `TranscriptProcessor` prints a `DeprecationWarning` at runtime. It works but will be removed in a future version. The recommended replacement is to use `on_user_turn_stopped` / `on_assistant_turn_stopped` events on the context aggregators.
**Rule:** Not a blocker for this project (v0.0.105 supports it), but if upgrading Pipecat in the future, this will need to change. Note in any upgrade planning.

## 14. CTO reviews don't catch upstream constant errors (2026-03-26)
**What happened:** Three rounds of CTO code review caught 14 bugs in Pipecat API usage (event names, import paths, parameter placement), but none caught the invalid Anthropic model ID. Code reviews focus on structural patterns and logic flow — they're blind to whether a string constant like a model ID is actually valid upstream.
**Rule:** Code review and API doc verification are complementary, not redundant. After CTO review passes, run a separate verification pass that checks every third-party constant (model IDs, voice names, API endpoints, SDK version compatibility) against live documentation.

## 11. ffmpeg on Windows: nested folder from zip extraction (2026-03-12)
**What happened:** Extracting ffmpeg zip created a double-nested folder. Had to flatten it.
**Rule:** After extracting, check the actual structure before assuming paths are correct.

## 15. PipelineRunner signal handling crashes on Windows in non-main thread (2026-04-10)
**What happened:** `PipelineRunner()` calls `signal.signal(SIGINT)` by default, which raises `ValueError: signal only works in main thread` when running inside uvicorn's worker thread on Windows.
**Fix:** Pass `handle_sigint=False` to `PipelineRunner()` when it runs in a non-main thread.
**Rule:** On Windows with threaded servers (uvicorn in a thread), always disable PipelineRunner's signal handling.

## 16. FastAPIWebsocketParams audio_in/out_enabled default to False (2026-04-10)
**What happened:** Pipeline started, Deepgram connected, but zero audio frames flowed. No STT, no LLM calls, complete silence for the entire call. Root cause: `audio_in_enabled` and `audio_out_enabled` both default to `False` in pipecat's `TransportParams`. The transport silently drops all audio unless explicitly enabled.
**Fix:** Always set `audio_in_enabled=True, audio_out_enabled=True` in `FastAPIWebsocketParams`.
**Rule:** Never assume transport defaults enable audio. Always explicitly set `audio_in_enabled=True` and `audio_out_enabled=True`.

## 17. LLM system prompts for voice bots must forbid stage directions (2026-04-10)
**What happened:** Bot read aloud text like "*pauses briefly*" and "*sighs*" because the LLM generated stage directions/emotions as text output, which TTS faithfully vocalized.
**Fix:** System prompt must explicitly say: "You produce ONLY spoken dialogue. Never output stage directions, emotions, asterisks, parenthetical actions, or narration."
**Rule:** Any LLM driving TTS needs a hard rule against non-speech text. LLMs default to including stage directions in roleplay — you must explicitly forbid it.

## 18. Voice bot personas must be reactive, not scripted with hardcoded details (2026-04-10)
**What happened:** Scenario prompts included specific doctor names ("Dr. Smith"), appointment times ("Thursday at 2pm"), and other details the receptionist never mentioned. The bot would reference these unprompted, making the conversation feel unnatural and scripted.
**Fix:** Remove all hardcoded details that should come from the receptionist. Add rule: "Never invent details the receptionist has not mentioned. Wait for them to offer options."
**Rule:** Voice bot personas should define personality, goals, and background info (DOB, insurance) — but never pre-script details that depend on the conversation flow (doctor names, times, availability).

## 19. Deepgram STT needs explicit encoding/sample_rate for Twilio audio (2026-04-11)
**What happened:** DeepgramSTTService was initialized with only `api_key`. Twilio sends mulaw-encoded audio at 8kHz, but without telling Deepgram the encoding, it may misinterpret the audio format, leading to poor or no transcription.
**Fix:** Pass `model="nova-3-general", language="en-US", encoding="mulaw", sample_rate=8000` to `DeepgramSTTService`.
**Rule:** Always configure STT to match the exact audio format of the transport. For Twilio: mulaw encoding at 8000Hz.

## 20. Pipeline cleanup must use try/finally, not on_pipeline_finished alone (2026-04-11)
**What happened:** Recordings and transcripts were never saved locally. The `on_pipeline_finished` event handler was responsible for calling `audiobuffer.stop_recording()` and `save_transcript()`, but when the WebSocket disconnects (Twilio hangs up), the pipeline may not end cleanly and the event never fires.
**Fix:** Wrap `runner.run(task)` in try/finally. Save recording and transcript in the `finally` block so they're saved even on crash or abrupt disconnection.
**Rule:** Never rely solely on pipeline events for critical cleanup. Always use try/finally around `runner.run()`.

## 21. VAD stop_secs tuning: 0.6s is too aggressive for phone calls (2026-04-11)
**What happened:** With `stop_secs=0.6`, the bot would start responding after only 0.6s of silence, frequently interrupting the receptionist mid-pause. Phone conversations have natural pauses, and the receptionist's AI also has processing gaps between sentences.
**Fix:** Increased `stop_secs` to 1.0. This gives the receptionist time to pause between sentences without triggering a bot response.
**Rule:** For telephony bots calling other AI agents, start with `stop_secs=1.0` and tune from there. Lower values cause interruptions, higher values feel sluggish.

## 22. LLM temperature and max_tokens tuning for voice bots (2026-04-11)
**What happened:** With `temperature=0.7` and `max_tokens=200`, the bot produced verbose, varied responses that sounded unnatural when spoken aloud. Phone conversation responses should be short and predictable.
**Fix:** Reduced to `temperature=0.5, max_tokens=100`. Lower temperature = more consistent/natural phrasing. Lower max_tokens = faster response generation and shorter utterances.
**Rule:** Voice bots should use lower temperature (0.4-0.6) and lower max_tokens (50-100) than text bots. Brevity is naturalness in phone calls.

## 23. PipelineRunner.run() hangs on WebSocket disconnect — use on_client_disconnected (2026-04-28)
**What happened:** Try/finally around `runner.run(task)` was supposed to guarantee transcript+recording save (lesson 20), but the finally never executed. Trace showed last bot message → DeprecationWarning → silence. Twilio hung up the call but Pipecat's pipeline kept waiting for an EndFrame that never propagated, so `runner.run()` never returned.
**Fix:** Add a `transport.event_handler("on_client_disconnected")` callback that does the save work inline AND calls `await task.cancel()` to force the runner to return. Keep the finally block as belt-and-suspenders, gated by a `saved` flag to prevent double-writes.
**Rule:** For WebSocket-based telephony transports in Pipecat, do critical save work in `on_client_disconnected`, not just in finally. The disconnect event is the only reliable signal that the call is truly over. **This supersedes lesson 20**: try/finally alone is not sufficient.

## 24. AudioBufferProcessor.start_recording() must run AFTER the pipeline boots (2026-04-28)
**What happened:** Calling `await audiobuffer.start_recording()` immediately before `runner.run(task)` raced the pipeline's StartFrame propagation. When `start_recording()` fired before the processor had received its StartFrame, it silently no-op'd and never accumulated frames. End-of-call `stop_recording()` had nothing to flush, so `on_audio_data` never fired and no MP3 was written.
**Fix:** Move `start_recording()` into a `transport.event_handler("on_client_connected")` callback. This guarantees it runs after the pipeline has fully booted and the AudioBufferProcessor is in a state where it can accept frames.
**Rule:** Any per-call setup that depends on processor state should run in `on_client_connected`, not before `runner.run()`. Pre-pipeline setup runs in a void where processors haven't received their StartFrame yet.

## 25. Twilio call-status polling is unreliable for "call ended" detection (2026-04-28)
**What happened:** CLI polled Twilio's call status to detect call end and return to the menu. Twilio reports `completed` the moment its audio stream ends, but the WebSocket close cascading through FastAPI → `on_client_disconnected` → save logic → pipeline teardown takes another 500ms–2s. The menu reappeared mid-teardown, with a flood of disconnect logs interleaved over the input prompt — eating the user's keystroke as "Invalid input."
**Fix:** Use a `threading.Event` set by the WebSocket handler's `finally` block (after `run_bot` returns). The CLI waits on this event instead of polling Twilio. The event only fires after every save log has flushed and the pipeline is fully torn down.
**Rule:** For "is the work truly done" signals, prefer in-process completion signals over external API polling. External services report status from their own perspective; local cleanup may take significantly longer.

## 26. Fetch the live voice catalog before casting voices (2026-05-01)
**What happened:** Initial scenario voice assignments had three duplicate voices (helena, hermes, apollo each used twice across 12 scenarios) plus four age/tone mismatches (David age 28 with the older-sounding `orpheus`, Robert age 62 with the younger-sounding `apollo`, Dorothy age 72 with the energetic `thalia`, Tony impatient with the smooth `apollo`). The original casting was guessed from voice-name vibes without consulting Deepgram's published descriptors.
**Fix:** Used `WebFetch` against `developers.deepgram.com/docs/tts-models` to pull the full Aura 2 catalog (40+ voices, each with gender, perceived-age, and tone descriptors). Re-cast 8 of 12 scenarios so each persona maps to a voice whose descriptors fit the character (Robert → `mars` "Patient, Baritone"; Dorothy → `pandora` "Calm, Melodic, Breathy"; Tony → `saturn` "Confident, Baritone" — no warmth softeners).
**Rule:** For provider voice catalogs (Deepgram, ElevenLabs, etc.), fetch the live catalog with descriptors before casting voices. Voice IDs are mythological names with no inherent meaning — training data lacks the perceived-age and tonal cues needed to match a persona, so guessing from the name is unreliable.

## 27. Per-persona prompt fingerprints beat generic naturalness rules (2026-05-01)
**What happened:** SYSTEM_PREAMBLE had a generic "use contractions and casual filler" rule that all 12 personas inherited equally. Even after persona-specific tone descriptions ("Brusque but not rude", "Sweet but scattered"), every persona sounded like the same flavor of "human" voice in different costumes.
**Fix:** Added a one-sentence "Tics:" fingerprint to each persona naming 2-3 signature filler phrases plus a tonal cue (Tony: "yeah yeah", "right", clipped two-to-four word replies; Robert: "hmm", "well...", slow and thoughtful; Susan: "mm-hm", "I see", composed). Differentiation now lives in the specifics, not in shared instructions.
**Rule:** When making LLM-driven personas distinct, prefer per-persona phrasing fingerprints over more generic preamble rules. A 10-15 word per-persona "Tics:" line costs little prompt tokens and gives each persona a distinguishable voice. Generic naturalness rules in the preamble flatten everyone into the same average human.

## 28. Conservative phrasing for TTS-bound prompts — avoid sound-effect literals (2026-05-01)
**What happened:** First-draft fingerprints overshot in two places. Priya's "haha — silly me" risked the LLM emitting literal "haha" which TTS would phonetically vocalize. Dorothy's "sometimes lose the thread mid-sentence" was a directive that could over-fragment speech beyond what reads as natural confusion. Both were flagged before applying and revised to safer versions ("silly me" only; "Soft and unhurried" with the explicit fragmenting directive removed).
**Fix:** Strip sound-effect literals (haha, ugh, sigh, *laughs*) from prompts whose output flows into TTS. Provide *flavor* (bright + self-deprecating) without giving the LLM permission to output sound-effect words as text. Avoid hard "always do X" directives for behaviors the persona description already implies — they can drown out the rest of the persona.
**Rule:** Any prompt-engineered phrase that will pass through TTS needs scrubbing for sound-effect words and over-prescriptive directives. The same prompt that reads charming on paper can produce a robot phonetically pronouncing "haha" on a real call.
