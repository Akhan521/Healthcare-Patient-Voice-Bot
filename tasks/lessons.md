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

## 5. ffmpeg on Windows: nested folder from zip extraction (2026-03-12)
**What happened:** Extracting ffmpeg zip created a double-nested folder. Had to flatten it.
**Rule:** After extracting, check the actual structure before assuming paths are correct.
