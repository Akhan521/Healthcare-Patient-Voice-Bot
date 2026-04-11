import os
import re
import time

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.transcript_processor import TranscriptProcessor

from src.recorder import save_recording, save_transcript


class SilenceFilter(FrameProcessor):
    """Filters out LLM responses that are silence markers before they reach TTS.

    The LLM can't output truly empty responses, so when instructed to be silent
    it outputs markers like "(silence)" or "...". This filter accumulates the
    full LLM response and drops it if it matches a silence pattern.
    """

    SILENCE_PATTERN = re.compile(
        r"^[\s.…]*$|^\(silence\)$|^\[silence\]$|^\.{2,}$",
        re.IGNORECASE,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._accumulator = []
        self._buffered_frames = []
        self._in_response = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._in_response = True
            self._accumulator = []
            self._buffered_frames = [frame]
            return

        if self._in_response:
            self._buffered_frames.append(frame)

            if isinstance(frame, TextFrame):
                self._accumulator.append(frame.text)

            if isinstance(frame, LLMFullResponseEndFrame):
                full_text = "".join(self._accumulator).strip()
                self._in_response = False

                if self.SILENCE_PATTERN.match(full_text):
                    logger.debug(f"SilenceFilter: dropped silence marker [{full_text}]")
                    self._buffered_frames = []
                    self._accumulator = []
                    return

                # Not silence — flush all buffered frames
                for buffered in self._buffered_frames:
                    await self.push_frame(buffered, direction)
                self._buffered_frames = []
                self._accumulator = []
                return

            return

        await self.push_frame(frame, direction)


async def run_bot(websocket, call_data, scenario):
    logger.info(f"Starting bot for scenario: {scenario.name} ({scenario.id})")

    stream_sid = call_data.get("stream_id")
    call_sid = call_data.get("call_id")
    call_start = time.time()
    turns = []

    # --- VAD ---
    # Higher stop_secs = bot waits longer before responding, reducing interruptions.
    # 1.0s gives the receptionist time to pause mid-sentence without the bot jumping in.
    vad = SileroVADAnalyzer(params=VADParams(stop_secs=1.0))

    # --- Transport (VAD goes here, not PipelineParams) ---
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            serializer=TwilioFrameSerializer(
                stream_sid=stream_sid,
                call_sid=call_sid,
                account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            ),
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            vad_analyzer=vad,
        ),
    )

    # --- Services ---
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-3-general",
        language="en-US",
    )

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice=scenario.voice,
    )

    llm = AnthropicLLMService(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        settings=AnthropicLLMService.Settings(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            temperature=0.5,
        ),
    )

    # --- Silence filter (drops "(silence)" etc. before TTS) ---
    silence_filter = SilenceFilter()

    # --- Context (system prompt must be in context, not Settings) ---
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": scenario.system_prompt},
            {"role": "user", "content": "(waiting for the receptionist to greet me)"},
        ]
    )
    context_agg = llm.create_context_aggregator(context)

    # --- Transcript tracking (captures both sides) ---
    transcript_proc = TranscriptProcessor()

    @transcript_proc.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        elapsed = int(time.time() - call_start)
        minutes, seconds = divmod(elapsed, 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        for msg in frame.messages:
            turns.append({
                "role": msg.role,
                "text": msg.content,
                "time": timestamp,
            })
            role_label = "RECEPTIONIST" if msg.role == "user" else "BOT"
            logger.info(f"[{timestamp}] {role_label}: {msg.content}")

    # --- Recording ---
    audiobuffer = AudioBufferProcessor(num_channels=1, sample_rate=8000)

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        filepath = save_recording(audio, scenario.id, sample_rate, num_channels)
        logger.info(f"Recording saved: {filepath}")

    # --- Pipeline ---
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            transcript_proc.user(),
            context_agg.user(),
            llm,
            silence_filter,
            tts,
            transport.output(),
            transcript_proc.assistant(),
            context_agg.assistant(),
            audiobuffer,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        ),
    )

    # Start recording and run — save transcript/recording even if pipeline crashes
    await audiobuffer.start_recording()
    try:
        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)
    finally:
        logger.info("Pipeline ended, saving recording and transcript...")
        try:
            await audiobuffer.stop_recording()
        except Exception:
            logger.warning("Could not stop audio buffer cleanly")
        if turns:
            filepath = save_transcript(turns, scenario.id)
            logger.info(f"Transcript saved: {filepath}")
        else:
            logger.warning("No transcript turns captured")
    logger.info(f"Call completed for scenario: {scenario.id}")
