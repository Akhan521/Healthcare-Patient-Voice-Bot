# CLAUDE.md — Healthcare Patient Voice Bot

## Project Overview

This is a **PGAI Engineering Challenge** submission. The goal is to build a Python voice bot that:

1. Calls a specific test phone number (+1-805-439-8008) — this is the ONLY number we ever call
2. Simulates realistic patient scenarios (scheduling, refills, questions, edge cases)
3. Records and transcribes ALL conversations as MP3 files
4. Identifies bugs or quality issues in the AI agent's responses

The bot acts as a **simulated patient** calling into PGAI's AI healthcare receptionist ("Athena"). Context on the product: pgai.us/athena

## Critical Constraints

- **Test number:** +1-805-439-8008 — NEVER call any other number
- **Minimum 10 calls** with full MP3 recordings and transcripts — no exceptions
- **MP3 recordings are mandatory** — transcripts-only submissions are rejected
- **Both sides** of the conversation must be captured in transcripts
- **Budget:** Keep total API + telephony costs under ~$20
- **Language:** Python only

## Package Manager

**Use `uv` as the package manager.** All dependency management must go through `uv`:

```bash
# Initialize project (if pyproject.toml doesn't exist)
uv init

# Add dependencies
uv add <package>

# Install all dependencies
uv sync

# Run scripts
uv run python <script.py>
```

Do NOT use pip, pip install, or requirements.txt. All dependencies go in `pyproject.toml` managed by `uv`. When adding a new dependency, always use `uv add <package>`.

## Architecture Principles

### SIMPLE AND MODULAR — Do Not Over-Engineer

The evaluation criteria explicitly says:

> "NOT looking for: Perfect code or over-engineering, fancy diagrams, production-grade infrastructure"

Follow these rules:

1. **Flat file structure** — avoid deep nesting. A few well-named Python files beats a complex package hierarchy
2. **No abstraction layers unless reused** — if something is used once, inline it
3. **No design patterns for their own sake** — no factories, builders, registries, or strategy patterns
4. **Minimal classes** — prefer functions. Use a class only when it genuinely holds state
5. **No custom frameworks** — use libraries directly
6. **One file per concern** — e.g., `caller.py` for telephony, `scenarios.py` for patient scripts, `transcribe.py` for transcription
7. **Config via .env file** — no complex config systems

### Suggested File Structure

```
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .env                    # API keys (gitignored)
├── .env.example            # Template for required env vars
├── src/
│   ├── caller.py           # Makes outbound calls via Twilio/telephony
│   ├── voice.py            # TTS/STT — converts text to speech and speech to text
│   ├── brain.py            # LLM logic — generates patient responses
│   ├── scenarios.py        # Patient scenario definitions
│   ├── recorder.py         # Records calls, saves MP3s
│   └── transcribe.py       # Generates transcripts from recordings
├── run.py                  # Main entry point — orchestrates calls
├── recordings/             # MP3 files from calls (committed to repo)
├── transcripts/            # Text transcripts of each call
├── docs/
│   ├── architecture.md     # 1-2 paragraph architecture explanation
│   └── bug_report.md       # Bugs found during testing
└── tasks/
    ├── todo.md
    └── lessons.md
```

This is a suggestion, not a mandate. Adapt as needed but keep it flat and simple.

## Technology Stack (Decided)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Framework | **Pipecat** (`pipecat-ai`) | Open-source Python voice AI framework |
| Telephony | **Twilio** (PAID account, not trial) | Trial cannot call unverified numbers + plays announcement |
| STT | **Deepgram Nova 3** | Via pipecat extras |
| TTS | **Deepgram Aura 2** | Via pipecat extras. Voices: `aura-2-helena-en`, `aura-2-hermes-en`, etc. |
| LLM | **Claude Haiku 4.5** | Via pipecat extras. Fastest/cheapest for real-time conversation |
| Tunneling | **pyngrok** | Manages ngrok programmatically. Do NOT install ngrok separately |
| Audio | **pydub + ffmpeg** | ffmpeg must be manually installed on Windows |
| Logging | **loguru** | Clean structured logging |

### Critical Technical Notes

- **Twilio MUST be a paid account** — trial accounts cannot call the test number and play an announcement
- **Use `SileroVADAnalyzer`**, NOT Smart Turn — Smart Turn v3 breaks at 8kHz (Pipecat issue #3844)
- **Use `AnthropicLLMService` directly** — do NOT use `OpenAILLMContext` or `AnthropicLLMContext` (deprecated)
- **Bot listens first** — the AI receptionist speaks first. Pipecat does NOT auto-generate at startup
- **All audio is 8kHz** — Twilio requirement. Set `sample_rate=8000` everywhere
- **On Windows:** set `asyncio.WindowsProactorEventLoopPolicy()` at startup
- **On Windows:** use `pathlib.Path` for all file paths, specify `codec="libmp3lame"` in pydub exports

## Required Environment Variables

```
TWILIO_ACCOUNT_SID=        # From Twilio console (paid account)
TWILIO_AUTH_TOKEN=         # From Twilio console
TWILIO_PHONE_NUMBER=       # Your Twilio number in E.164 format (+1XXXXXXXXXX)
DEEPGRAM_API_KEY=          # From Deepgram console
ANTHROPIC_API_KEY=         # Claude API key
NGROK_AUTH_TOKEN=          # From ngrok dashboard
```

**NOTE:** The target number (+18054398008) is a HARDCODED CONSTANT in code, NOT an env var. This prevents accidentally calling the wrong number.

## Test Scenarios to Implement

The bot must handle these patient scenarios (minimum):

1. **Simple appointment scheduling** — "I'd like to schedule an appointment with Dr. Smith"
2. **Rescheduling** — "I need to move my appointment to next week"
3. **Canceling** — "I need to cancel my appointment"
4. **Medication refill** — "I need a refill on my prescription"
5. **Office hours inquiry** — "What are your office hours?"
6. **Location question** — "Where is your office located?"
7. **Insurance question** — "Do you accept Blue Cross Blue Shield?"
8. **Edge case: interruption** — Interrupt the agent mid-sentence
9. **Edge case: unclear request** — Give a vague or confusing request
10. **Edge case: unusual scenario** — Something unexpected (e.g., emergency, wrong number behavior, speaking another language briefly)

Each scenario should be defined with:
- A persona (name, reason for calling)
- An opening line
- Key information to convey
- Expected flow

## Deliverables Checklist

All of these are required for submission:

- [ ] **Working code** — Bot can make real calls to +1-805-439-8008
- [ ] **README.md** — Setup instructions (ideally single command after initial setup)
- [ ] **Architecture doc** — 1-2 paragraphs in `docs/architecture.md`
- [ ] **10+ MP3 recordings** — One per call, saved in `recordings/`
- [ ] **10+ transcripts** — Both sides of conversation, saved in `transcripts/`
- [ ] **Bug report** — Issues found in `docs/bug_report.md`. Each bug: scenario, what happened, what was expected, severity. Categorize by type. Reference specific recordings. Quality over quantity.
- [ ] **Loom video** — Max 5 min walkthrough (external, not in repo)

## Evaluation Priority (What Matters Most)

Ranked by importance:

1. **Coherent, natural voice conversation** — The bot must sound like a real person having a real conversation. This is the #1 criterion. Prioritize natural flow, appropriate pauses, and realistic dialogue over everything else.
2. **Quality of bugs found** — Thoughtful, well-described bugs beat long nitpick lists. Focus on real issues: wrong information, conversation breakdowns, logic errors.
3. **Working code** — It must actually make real calls. A working simple solution beats a broken complex one.
4. **Clear thinking** — Architecture doc and code should show reasoning.
5. **Evidence of iteration** — Show improvement after early results.
6. **Clean code** — Readable and understandable, not perfect.

## What NOT To Do

- Do NOT over-engineer — no microservices, no complex abstractions, no production infrastructure
- Do NOT create fancy diagrams or documentation beyond what's required
- Do NOT nitpick punctuation or minor transcript formatting in the bug report
- Do NOT add features beyond what's needed (no web UI, no database, no auth system)
- Do NOT spend time on perfect error handling for every edge case — handle the common paths
- Do NOT create deep class hierarchies or use design patterns unnecessarily
- Do NOT add type annotations, docstrings, or comments to code that is self-explanatory

## Workflow

1. Set up the project with `uv` and install core dependencies
2. Get a basic outbound call working first (prove telephony works)
3. Add TTS so the bot can speak
4. Add STT so the bot can hear responses
5. Add LLM so the bot can generate contextual replies
6. Wire it all together into a conversational loop
7. Add recording and transcription
8. Define and run the 10+ scenarios
9. Review recordings, write bug report
10. Write architecture doc and README
11. Record Loom video

## Git Practices

- Commit working increments, not huge dumps
- Use clear commit messages describing what changed
- Keep `.env` in `.gitignore` — NEVER commit API keys
- **Both `recordings/` and `transcripts/` MUST be committed to the repo** — evaluators need direct access to MP3 files and transcripts without extra steps
- MP3 files at 8kHz mono ~2min each are small (~1-2MB). 12 files ≈ 12-24MB total — well within GitHub limits, no Git LFS needed
- Add `.gitkeep` files in empty directories so they exist before recordings are generated

## Submission Details

- Repository must be **public** on GitHub
- Email to: kevin@prettygoodai.com
- Subject: `PGAI BUILT IT: <Full Name> <Bot Phone Number in E.164>`
- Include: GitHub link, Loom video link, phone number
