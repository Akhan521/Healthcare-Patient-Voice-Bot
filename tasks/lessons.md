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
