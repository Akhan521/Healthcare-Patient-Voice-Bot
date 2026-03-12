# Implementation Plan — Healthcare Patient Voice Bot

## CTO Review Summary (Revision 3)

Three rounds of technical validation uncovered 7 issues — 1 plan-breaker, 3 high-risk, 3 medium-risk. All are addressed below.

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Twilio trial cannot call the test number | **PLAN-BREAKER** | Fixed: require paid account |
| 2 | Twilio trial plays announcement before TwiML | **PLAN-BREAKER** | Fixed: same — paid account |
| 3 | `OpenAILLMContext` wrong for Anthropic | **High** | Fixed: use `AnthropicLLMService` directly |
| 4 | `aura-2-theron-en` voice ID doesn't exist | **High** | Fixed: verified voice IDs only |
| 5 | ffmpeg PATH broken via `winget` on Windows | **High** | Fixed: manual install + explicit path in code |
| 6 | pydub MP3 export silently fails on Windows | **Medium** | Fixed: explicit `codec="libmp3lame"` |
| 7 | Pipecat issue #3844: Smart Turn breaks at 8kHz | **Medium** | Fixed: use basic SileroVAD, not Smart Turn |
| 8 | `pipecat-ai[twilio]` extra doesn't exist | **Medium** | Fixed: install `twilio` separately |
| 9 | Windows asyncio event loop | **Low** | Fixed: set ProactorEventLoop at startup |
| 10 | File paths with backslashes on Windows | **Low** | Fixed: `pathlib.Path` everywhere |

---

## Stack

| Component | Technology | Package |
|-----------|-----------|---------|
| Framework | Pipecat | `pipecat-ai[deepgram,anthropic,silero]` |
| Telephony | Twilio (**paid account required**) | `twilio` |
| STT | Deepgram Nova 3 | (included in pipecat extras) |
| TTS | Deepgram Aura 2 | (included in pipecat extras) |
| LLM | Claude Haiku 4.5 | (included in pipecat extras) |
| Web server | FastAPI | `fastapi`, `uvicorn` |
| Tunneling | ngrok (managed via pyngrok) | `pyngrok` |
| Audio export | pydub + ffmpeg | `pydub` |
| Config | dotenv | `python-dotenv` |
| Logging | loguru | `loguru` |

### Install Command

```bash
uv add "pipecat-ai[deepgram,anthropic,silero]" twilio fastapi uvicorn python-dotenv pydub pyngrok loguru
```

---

## Phase 0: Prerequisites

### Accounts (must complete before coding)

1. **Twilio — PAID account required (not trial)**
   - Sign up at https://www.twilio.com/try-twilio
   - **Upgrade to paid account immediately** — add $20 credit
   - Trial accounts CANNOT call unverified numbers (the test line +1-805-439-8008 can't be verified since we don't own it)
   - Trial accounts also play an announcement message before your TwiML runs, which breaks automated conversation
   - After upgrading: get Account SID + Auth Token from console, buy a US phone number ($1/month)

2. **Deepgram** — https://console.deepgram.com
   - Sign up → get API key
   - Free tier includes $200 credit (more than enough)

3. **ngrok** — https://ngrok.com
   - Sign up for free account → get auth token from dashboard
   - Do NOT install ngrok via `winget` — let `pyngrok` manage the binary automatically

4. **ffmpeg** — required for MP3 conversion
   - Do NOT use `winget install ffmpeg` — PATH configuration is broken on Windows
   - Manual install:
     1. Download from https://www.gyan.dev/ffmpeg/builds/ (get "release full" build)
     2. Extract to `C:\ffmpeg\`
     3. Add `C:\ffmpeg\bin` to system PATH
     4. Restart terminal, verify: `ffmpeg -version`
   - As a safety net, also set the path explicitly in code:
     ```python
     from pydub import AudioSegment
     AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
     ```

5. **Anthropic API key** — already have

6. **Create `.env` file:**
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxx
   TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
   DEEPGRAM_API_KEY=xxxxxxxxxx
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx
   NGROK_AUTH_TOKEN=xxxxxxxxxx
   ```

### Cost Estimate (Paid Twilio Account)

| Service | Per-Call Cost (~2min) | 12 Calls Total |
|---------|---------------------|----------------|
| Twilio outbound calling | ~$0.03 | ~$0.36 |
| Twilio Media Streams | ~$0.008 | ~$0.10 |
| Twilio phone number | $1.00/mo | $1.00 |
| Deepgram STT | ~$0.03 | ~$0.36 |
| Deepgram TTS | ~$0.02 | ~$0.24 |
| Claude Haiku | ~$0.005 | ~$0.06 |
| **Total** | | **~$2.12** |

Well under $20. Deepgram's $200 free credit covers STT/TTS entirely.

---

## File Structure

```
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore                  # Only .env and .venv/ excluded
├── run.py                      # CLI entry point
├── src/
│   ├── bot.py                  # Pipecat pipeline setup + event handlers
│   ├── server.py               # FastAPI app + WebSocket + call initiation
│   ├── scenarios.py            # Patient scenario definitions
│   └── recorder.py             # Audio save (MP3) + transcript save
├── recordings/                 # MP3 files (committed to repo)
│   └── .gitkeep
├── transcripts/                # Conversation transcripts (committed to repo)
│   └── .gitkeep
└── docs/
    ├── architecture.md
    └── bug_report.md
```

---

## Phase 1: Project Init

- `uv init` (if pyproject.toml doesn't exist)
- Install all dependencies via `uv add`
- Create `.env.example` with empty values
- Create `.gitignore` — exclude ONLY `.env`, `.venv/`, `__pycache__/`, `*.pyc`
- Create directory structure with `.gitkeep` files in `recordings/` and `transcripts/`
- Verify `uv sync` succeeds

---

## Phase 2: Scenarios

Define 12 patient scenarios in `src/scenarios.py` as dataclasses:

| # | Scenario | Voice | Tests |
|---|----------|-------|-------|
| 1 | Simple scheduling | `aura-2-helena-en` (F) | Basic appointment booking |
| 2 | Rescheduling | `aura-2-hermes-en` (M) | Change existing appointment |
| 3 | Canceling | `aura-2-athena-en` (F) | Cancel appointment |
| 4 | Medication refill | `aura-2-apollo-en` (M) | Prescription refill request |
| 5 | Office hours | `aura-2-orpheus-en` (M) | Basic info inquiry |
| 6 | Location/directions | `aura-2-hera-en` (F) | Address and directions |
| 7 | Insurance question | `aura-2-zeus-en` (M) | Coverage inquiry |
| 8 | Urgent appointment | `aura-2-helena-en` (F) | Same-day/urgent request |
| 9 | Vague/confused patient | `aura-2-thalia-en` (F) | Edge: unclear requests |
| 10 | Multiple requests | `aura-2-hermes-en` (M) | Edge: compound request |
| 11 | Frequent interrupter | `aura-2-apollo-en` (M) | Edge: interruptions |
| 12 | Out of scope | `aura-2-aurora-en` (F) | Edge: unusual request |

Each scenario includes: patient persona, system prompt for Claude, voice ID, opening behavior, what's being tested.

---

## Phase 3: Server + Bot Pipeline

### `src/server.py` — FastAPI Application

- `POST /start-call` — accepts scenario ID, initiates Twilio outbound call via REST API
- `WebSocket /ws` — receives Twilio media stream, spins up Pipecat pipeline
- Starts ngrok tunnel on boot via `pyngrok` (no manual ngrok needed)
- Manages call lifecycle

**Outbound call initiation pattern:**
```python
call = twilio_client.calls.create(
    to=TARGET_NUMBER,               # Hardcoded constant, never from user input
    from_=TWILIO_PHONE_NUMBER,
    twiml=f'<Response><Connect><Stream url="wss://{ngrok_url}/ws">'
          f'<Parameter name="scenario_id" value="{scenario.id}"/>'
          f'</Stream></Connect></Response>',
    record=True,                    # Twilio-side backup recording
)
```

### `src/bot.py` — Pipecat Pipeline

**Correct wiring pattern (validated against Pipecat source):**

```python
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.anthropic import AnthropicLLMService
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.vad.silero import SileroVADAnalyzer

# Transport setup — serializer passed via params
transport = FastAPIWebsocketTransport(
    websocket=ws_connection,
    params=FastAPIWebsocketParams(
        serializer=TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=TWILIO_ACCOUNT_SID,
            auth_token=TWILIO_AUTH_TOKEN,
            params=TwilioFrameSerializer.InputParams(
                sample_rate=8000,
                auto_hang_up=True,
            ),
        ),
        add_wav_header=False,
    ),
)

# Pipeline order
pipeline = Pipeline([
    transport.input(),
    stt,
    context_aggregator.user(),
    llm,
    tts,
    transport.output(),
    context_aggregator.assistant(),
    audio_buffer,
])
```

**Critical implementation details:**

1. **Use `SileroVADAnalyzer`, NOT Smart Turn** — Pipecat issue #3844 confirms Smart Turn v3 breaks at 8kHz (Twilio's sample rate). Use basic Silero VAD instead.

2. **Bot listens first, does NOT speak first** — The AI receptionist greets first. Pipecat's `AnthropicLLMService` does NOT auto-generate at startup; it waits for user input. No special configuration needed.

3. **Use `AnthropicLLMService` directly** — NOT `AnthropicLLMContext` (deprecated) or `OpenAILLMContext` (wrong provider). The modern Pipecat API uses the service's built-in context management.

4. **8kHz audio throughout** — Set `sample_rate=8000` in TwilioFrameSerializer, and `audio_in_sample_rate=8000` / `audio_out_sample_rate=8000` in PipelineParams.

5. **Max call duration** — Add a 180-second timer that triggers graceful hangup.

6. **Windows asyncio** — At the top of `run.py`:
   ```python
   import sys, asyncio
   if sys.platform == "win32":
       asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
   ```

---

## Phase 4: Recording + Transcripts

### `src/recorder.py`

**Recording:**
- `AudioBufferProcessor` captures composite audio (both sides) as 16-bit PCM
- On call end → convert to MP3 via `pydub`
- Use `pathlib.Path` for all file operations (Windows backslash safety)

```python
from pathlib import Path
from pydub import AudioSegment

RECORDINGS_DIR = Path("recordings")

def save_recording(raw_audio_bytes: bytes, scenario_id: str, timestamp: str) -> Path:
    audio = AudioSegment(
        data=raw_audio_bytes,
        sample_width=2,       # 16-bit
        frame_rate=8000,      # Twilio's rate
        channels=1,           # Mono composite
    )
    filepath = RECORDINGS_DIR / f"{scenario_id}_{timestamp}.mp3"
    audio.export(
        str(filepath),
        format="mp3",
        codec="libmp3lame",   # MUST specify on Windows — silent failure without it
        bitrate="128k",
    )
    return filepath
```

**Transcription:**
- Track conversation turns via context aggregator events
- Format: `[MM:SS] PATIENT: ...` / `[MM:SS] AGENT: ...`
- Save to `transcripts/{scenario_id}_{timestamp}.txt`

**Backup recording:**
- Twilio's `record=True` stores a server-side copy
- If local recording fails, download from Twilio as fallback

**Git strategy:**
- Only commit good recordings (not test/debug runs)
- Commit in batches, separate from code commits
- Timestamped filenames prevent overwrites
- Final repo: 10-12 MP3 files + matching transcripts

---

## Phase 5: CLI Runner

### `run.py`

1. Set Windows asyncio policy (if applicable)
2. Load and validate `.env` configuration
3. Start FastAPI server in background thread
4. Start ngrok tunnel via `pyngrok` → get public URL
5. Display scenario menu
6. User picks scenario → POST to `/start-call`
7. Wait for call completion (with timeout)
8. Display result: recording path, transcript path, call duration
9. Handle errors gracefully — failed call doesn't crash the app
10. Ask: run another or quit?

---

## Phase 6: Execute All Scenarios

Run all 10+ calls. After each call:
- Verify MP3 plays correctly with both voices audible
- Review transcript for accuracy
- Note bugs or quality issues for the bug report
- Commit good recordings in batches

---

## Phase 7: Documentation & Bug Report

### `docs/bug_report.md` — REQUIRED DELIVERABLE

Each bug includes:
- **Scenario** where it occurred
- **Recording reference** (filename + timestamp in the call)
- **What happened** (actual behavior)
- **What was expected**
- **Severity** (Critical / Major / Minor)
- **Category** (Comprehension, Information Accuracy, Conversation Flow, Edge Case Handling)

Focus on real quality issues. Note patterns across calls.

### `docs/architecture.md` — 1-2 paragraphs on design choices

### `README.md` — Setup and run instructions

---

## Required Deliverables

| # | Deliverable | Location | In Git? |
|---|------------|----------|---------|
| 1 | Working code | `src/`, `run.py` | Yes |
| 2 | README | `README.md` | Yes |
| 3 | Architecture doc | `docs/architecture.md` | Yes |
| 4 | 10+ MP3 recordings | `recordings/` | Yes |
| 5 | 10+ transcripts | `transcripts/` | Yes |
| 6 | Bug report | `docs/bug_report.md` | Yes |
| 7 | Loom video (max 5 min) | External link in README | N/A |

---

## Hardcoded Safety Constants

```python
# src/server.py — module-level constants, NOT in .env
TARGET_NUMBER = "+18054398008"       # ONLY number we ever call
MAX_CALL_DURATION_SECONDS = 180      # 3 minutes max per call
MAX_CALLS_PER_SESSION = 15           # Cost safety valve
```

---

## Verification Checklist

- [ ] `uv sync` installs all deps without errors
- [ ] `.env` is in `.gitignore` BEFORE first commit with credentials
- [ ] Server starts, ngrok tunnel establishes, public URL is reachable
- [ ] Outbound call connects to +1-805-439-8008 (no trial announcement)
- [ ] Bot hears the AI receptionist's greeting and does NOT speak first
- [ ] Bot responds with contextual patient dialogue
- [ ] Conversation flows naturally for 1-3 minutes
- [ ] MP3 recording saved and playable (both voices audible)
- [ ] Transcript captures both sides with timestamps
- [ ] All 10+ scenarios executed successfully
- [ ] Bug report documents real issues with recording references
- [ ] All MP3s + transcripts committed to repo
- [ ] Repo size < 50 MB
- [ ] `git clone` gives evaluators immediate access to everything

---

## Windows-Specific Gotchas (Reference)

| Issue | Fix |
|-------|-----|
| ffmpeg not found after install | Manual install to `C:\ffmpeg\bin`, add to PATH, set `AudioSegment.converter` in code |
| pydub MP3 export creates empty files | Always use `codec="libmp3lame"` and `bitrate="128k"` |
| asyncio NotImplementedError | Set `WindowsProactorEventLoopPolicy()` at startup |
| ngrok binary not found | Let `pyngrok` manage the binary — don't install ngrok separately |
| Path backslash issues | Use `pathlib.Path` for all file operations |
| Pipecat audio quality on Windows | Known issue — test early, consider cloud deployment if quality is poor |
| Pipecat STT hangs on Windows | Known issue #3532 — restart pipeline if STT stops responding |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Twilio call doesn't connect | Low | High | Verify paid account + phone number, test with a personal number first |
| High conversation latency (>2s) | Medium | High | Use Haiku (fastest), Deepgram (lowest latency STT/TTS), monitor first call |
| AudioBufferProcessor loses audio | Medium | High | Twilio `record=True` as backup, commit after each good call |
| Pipecat audio quality poor on Windows | Medium | Medium | Test first call, consider WSL or cloud VM if unacceptable |
| ngrok tunnel drops mid-call | Low | Medium | Short calls (3 min max), retry on failure |
| Deepgram free credit runs out | Very Low | Medium | $200 credit covers hundreds of minutes |
| VAD too aggressive (bot interrupts agent) | High | Medium | Tune VAD params after first test call — expect iteration |
