# Code Walkthrough

A plain-language guide to every file in the project. Designed to be read quickly before a demo.

---

## How It All Fits Together

The bot simulates a patient calling a doctor's office. When you run `run.py`, it:

1. Starts a local web server (FastAPI)
2. Opens an ngrok tunnel so Twilio can reach it from the internet
3. Shows a menu of patient scenarios
4. When you pick one, Twilio dials the test number and streams the live audio back to our server over a WebSocket
5. Pipecat processes that audio stream — listening, thinking, speaking — in real time
6. When the call ends, it saves an MP3 recording and a text transcript

```
You (CLI) --> run.py --> server.py --> Twilio --> Phone Call
                                         |
                              WebSocket audio stream
                                         |
                                      bot.py (Pipecat pipeline)
                                         |
                              recorder.py --> MP3 + transcript
```

---

## `run.py` — Entry Point

**What it does:** The CLI you interact with. Starts everything, shows the scenario menu, triggers calls.

**Key details:**
- Sets `WindowsProactorEventLoopPolicy` at startup — required on Windows for asyncio networking to work correctly
- Runs the FastAPI server in a background thread so the main thread stays free for the interactive menu
- Calls `start_ngrok()` to create a public URL (Twilio needs to reach our local server from the internet — ngrok creates that bridge)
- After each call, waits on a `threading.Event` (set by the WebSocket handler when the bot is fully done) so the menu reappears automatically once teardown finishes — no manual ENTER required

**Why uvicorn in a thread?** We need the web server running continuously to handle Twilio's WebSocket callbacks, but we also need an interactive CLI in the foreground. Threading lets both happen at once.

---

## `src/server.py` — Web Server + Call Initiation

**What it does:** Two jobs — (1) tell Twilio to make a phone call, and (2) receive the audio stream from that call.

**Safety constants:**
- `TARGET_NUMBER = "+18054398008"` — hardcoded, never from user input. This is the ONLY number we ever call.
- `MAX_CALLS_PER_SESSION = 15` and `MAX_CALL_DURATION_SECONDS = 300` — cost safety valves.

**`make_call(scenario_id)`** — Initiates the phone call via Twilio's REST API. The key part is the TwiML instruction:

```xml
<Response><Connect><Stream url="wss://xxxx.ngrok-free.app/ws">
  <Parameter name="scenario_id" value="01_scheduling"/>
</Stream></Connect></Response>
```

This tells Twilio: "Dial the number, and when it connects, stream the live audio to my WebSocket endpoint." The `<Parameter>` tag passes the scenario ID through so the bot knows which patient persona to use.

**Why `record=True`?** Twilio keeps a server-side backup recording. If our local recording fails, we have a fallback.

**`/ws` WebSocket endpoint** — When Twilio connects the audio stream, this endpoint receives it. It uses Pipecat's `parse_telephony_websocket()` to extract the stream/call IDs, then hands everything to `run_bot()`.

**Why Twilio?** It's the most mature telephony API. We use a paid account (not trial) because trial accounts can't call unverified numbers and play an announcement before the call starts, which would break automated conversation.

**Why ngrok?** Twilio needs a public URL to send the audio stream to, but we're running locally. ngrok creates a secure tunnel from a public URL to our local port. We use `pyngrok` to manage this programmatically — no separate ngrok install needed.

---

## `src/bot.py` — The Voice Pipeline (Core)

**What it does:** Builds and runs the Pipecat pipeline — the real-time audio processing chain that listens, thinks, and speaks.

**The pipeline in order:**

```
transport.input()                # Raw audio from Twilio WebSocket
    --> stt (Deepgram)           # Speech-to-text: audio becomes words
    --> transcript_proc.user()   # Log what the receptionist said
    --> context_agg.user()       # Collect into conversation context
    --> llm (Claude Haiku)       # Generate the patient's response
    --> silence_filter           # Drop "(silence)" markers before TTS
    --> tts (Deepgram)           # Text-to-speech: words become audio
    --> transport.output()       # Send audio back through Twilio
    --> transcript_proc.assistant()  # Log what the bot said
    --> context_agg.assistant()  # Update conversation context
    --> audiobuffer              # Capture audio for MP3 recording
```

Each step is a "processor" in Pipecat. Audio frames flow through left to right. When the receptionist speaks, the audio gets transcribed (STT), fed to Claude who generates a patient response, then that response is spoken aloud (TTS) and sent back through Twilio to the phone call.

**Why Pipecat?** It's an open-source Python framework purpose-built for real-time voice AI. It gives us a pipeline abstraction — you define a chain of processors (STT, LLM, TTS, etc.) and Pipecat handles streaming audio frames between them, managing turn-taking, and coordinating async I/O across multiple services simultaneously. It also has built-in integrations for Twilio, Deepgram, and Anthropic, so we don't have to write our own WebSocket handling, audio buffering, or provider-specific adapters. Without it, we'd need hundreds of lines of low-level async code just to get audio flowing between services in real time.

**Key components:**

- **VAD (Voice Activity Detection):** `SileroVADAnalyzer` with `stop_secs=0.8` — detects when someone stops talking. Tuned through testing: 0.6 was too aggressive (cut the receptionist off mid-pause), 1.0 felt sluggish, 0.8 balances responsiveness against mid-sentence interruptions. We use Silero instead of Pipecat's "Smart Turn" feature because Smart Turn has a known bug at 8kHz (Twilio's sample rate).

- **TwilioFrameSerializer:** The bridge between Twilio and Pipecat. Twilio sends audio as base64-encoded mulaw chunks in JSON messages over WebSocket — that's not something Pipecat can work with directly. The serializer decodes incoming Twilio messages into raw audio frames that the pipeline can process, and encodes outgoing audio frames back into Twilio's expected format. It also handles auto-hangup when the pipeline finishes by calling the Twilio REST API to end the call (which is why it needs the call SID and Twilio credentials).

- **LLM (Claude Haiku 4.5, model ID `claude-haiku-4-5-20251001`):** The "brain" that generates patient responses. We use Haiku because it's the fastest Claude model — critical for real-time conversation where every millisecond of latency matters. The system prompt is set on the context object (not in LLM settings) because Pipecat's Anthropic integration reads it from there when using the aggregator path. The system prompt from the scenario defines the patient's personality, reason for calling, and personal details. `temperature=0.5` and `max_tokens=100` keep responses short, predictable, and natural-sounding for phone speech (lower than typical text-bot defaults).

- **STT/TTS (Deepgram):** We use Deepgram for both speech-to-text and text-to-speech because it's one of the lowest-latency providers available — important for keeping the conversation feeling natural. Each scenario uses a different Deepgram Aura 2 voice to sound like a different person.

- **TranscriptProcessor:** Captures both sides of the conversation as it happens. Placed at two points in the pipeline — after STT (to capture what the receptionist said) and after TTS (to capture what our bot said).

- **AudioBufferProcessor:** Records the call audio for later saving. It captures both sides of the conversation — not because of its pipeline position, but because it listens for two different frame types: `InputAudioRawFrame` (the receptionist's voice) and `OutputAudioRawFrame` (our bot's voice). It maintains separate internal buffers for each side and mixes them together into a single mono stream. Recording must be explicitly started with `start_recording()` and stopped with `stop_recording()`. When stopped, it fires an `on_audio_data` event with the complete mixed audio buffer, which we then pass to `recorder.py` to save as an MP3. **Critical timing detail:** `start_recording()` is called from a `transport.event_handler("on_client_connected")` callback rather than before `runner.run()` — calling it earlier races the StartFrame propagation and the processor silently no-ops, leaving the buffer empty.

- **SilenceFilter (custom processor):** A small `FrameProcessor` we wrote that sits between the LLM and TTS. The system prompt instructs the bot to output `...` when the receptionist is mid-hold/mid-pause and there's nothing to respond to. But the LLM can't output literally nothing, so it sometimes emits markers like `(silence)` or `[silence]` that TTS would happily speak aloud. The filter accumulates each LLM response, checks it against a regex of silence patterns, and drops the entire response if it matches — otherwise it flushes the buffered frames downstream.

- **Context + Aggregators:** In a voice conversation, the STT service sends transcriptions as they come in, and the bot needs to know *when* a complete thought has been spoken before responding. Aggregators coordinate this timing. The user aggregator listens for VAD signals (silence detection) to know when the receptionist has finished speaking, then packages the accumulated transcription as a single "user" message and sends it to the LLM. The assistant aggregator collects the bot's response text the same way. Both write into a shared `OpenAILLMContext` object — the running conversation history that Claude sees each time it generates a response. Despite the "OpenAI" in the name, this is Pipecat's universal context class used by all providers; calling `llm.create_context_aggregator(context)` on an `AnthropicLLMService` produces Anthropic-specific aggregators that format messages correctly for the Claude API. This context is what gives the bot memory within a call: Claude can reference what was said earlier because the full conversation is stored there.

**Why does the bot listen first?** The AI receptionist (Athena) at the test number speaks first with a greeting. Our bot is the caller, so it waits to hear the greeting before responding — just like a real patient would.

**End-of-call save logic.** Pipecat's `runner.run(task)` hangs when Twilio drops the WebSocket — the pipeline never gets a clean EndFrame, so a `try/finally` around the runner is unreachable on its own. To handle this we wire an `on_client_disconnected` handler that does the save inline (calls `audiobuffer.stop_recording()` to flush the MP3, writes the transcript) and then calls `task.cancel()` to force `runner.run()` to return. A `do_save(reason)` helper guards both this path and a backup `finally` block with a `saved` flag so we never write twice. The WebSocket handler in `server.py` then sets a `threading.Event` from its `finally` block, which is what unblocks the CLI menu.

---

## `src/scenarios.py` — Patient Personas

**What it does:** Defines 12 test scenarios as simple dataclasses. Each has a unique patient name, personality, voice, and reason for calling.

**Why 12 scenarios?** The challenge requires minimum 10. We have 12 to cover the required categories:
- **Standard flows** (1-4): scheduling, rescheduling, canceling, medication refill
- **Information queries** (5-7): office hours, location, insurance
- **Urgent** (8): same-day appointment
- **Edge cases** (9-12): vague/confused patient, multiple requests, interruptions, out-of-scope request

Each scenario's `system_prompt` is what gets fed to Claude as instructions. It's built from a shared `SYSTEM_PREAMBLE` (rules that apply to every persona) plus a short scenario-specific block (who the patient is, why they're calling, personal details for if asked).

**The preamble rules** are the most load-bearing part of conversation quality. The key ones:
- **Spoken-only output** (no asterisks, stage directions, parentheticals) — TTS will read whatever the LLM emits, so this has to be a hard rule.
- **Sound human (rule 2)** — contractions, casual filler ("um", "oh", "hmm"), varied sentence length, and explicit permission to use sentence fragments and self-correction ("I was — well, actually..."). Targets the most audible robotic tell: every utterance being a clean grammatical sentence.
- **Purely reactive (rule 3)** — the patient never invents details the receptionist hasn't said first. No doctor names, times, or appointment types pulled from thin air. They open with only a high-level goal and let the receptionist drive the specifics.
- **Hold-phrase silence (rule 4)** — if the receptionist's final sentence is just "one moment" / "let me check," output `...` so the bot doesn't speak over the hold. The SilenceFilter then drops that marker before it reaches TTS.
- **Graceful rejection (rule 7)** — if the receptionist says they can't help, accept it; don't insist or re-pitch. Real callers don't fight receptionists.
- **Listen to the greeting (rule 8)** — wait for the receptionist to finish, answer specific questions before launching into the goal, work within whatever scope they announce, follow any test-call instructions they give.
- **Memory (rule 9)** — everything the receptionist said earlier in the call is ground truth. Don't re-ask about things they already covered.

Each scenario's persona block is intentionally short — a sentence on identity, a sentence on goal, and any fixed details (DOB, insurance) gated behind "ONLY if asked." The opening phrasing is "When invited to speak, say…" rather than "Open by…" so the bot doesn't talk over the receptionist's greeting. Each block also ends with a one-sentence "Tics:" line — 2-3 signature filler phrases plus a tonal cue (e.g., Tony: *"yeah yeah", "right", "so what's available?". Clipped two-to-four word replies.*). These persona-specific fingerprints stop every "human" voice from sounding like the same human.

**Ortho-fit vs. off-domain mix.** The target test number is an orthopedics practice (Pivot Point Orthopaedics). 7 of 12 scenarios are written to fit that domain (knee pain eval, post-op follow-ups, anti-inflammatory refill, rolled-ankle same-day, etc.) so the bulk of calls stress-test real workflows. 4 are domain-neutral (cancellation, location, insurance, confused elderly). 1 is deliberately off-domain (a pet prescription request that pivots to a wrist complaint) to test how Athena handles graceful scope rejection.

**Why different voices?** Each scenario uses a different Deepgram Aura 2 voice so the calls sound like different people. The 12 voices are cast against the live Aura 2 catalog (gender + perceived-age + tone descriptors) for persona fit — e.g., Robert (62-year-old post-op patient) gets `mars` (patient, baritone), Tony (impatient 50-year-old) gets `saturn` (no-warmth baritone), Dorothy (confused 72-year-old) gets `pandora` (calm, breathy — closest the catalog has to elderly).

---

## `src/recorder.py` — Saving Recordings + Transcripts

**What it does:** Two simple functions — one saves audio as MP3, one saves conversation turns as text.

- **`save_recording()`** — Takes raw PCM audio bytes, wraps them in a `pydub.AudioSegment`, and exports as MP3. Uses `codec="libmp3lame"` explicitly because on Windows, pydub silently creates empty files without it. Also sets the ffmpeg path explicitly as a safety net for Windows.

- **`save_transcript()`** — Takes the list of conversation turns and writes them as timestamped text: `[01:23] USER: Hello, I'd like to schedule...`

**File naming:** `{scenario_id}_{timestamp}.mp3` — e.g., `01_scheduling_20260314_143022.mp3`. Timestamps prevent overwrites when re-running scenarios.

**Why pydub + ffmpeg?** Pipecat gives us raw PCM audio data. We need MP3 files for the submission. pydub is the standard Python library for audio format conversion, and it uses ffmpeg under the hood.

---

## Audio Format: Why 8kHz Everywhere?

Twilio transmits phone audio at 8kHz (standard telephony rate). Every audio component — transport, pipeline params, audio buffer, STT, TTS — must be set to 8000 Hz to match. A sample rate mismatch would produce garbled audio or silence.
