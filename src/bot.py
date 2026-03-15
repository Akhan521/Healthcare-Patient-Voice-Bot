import os
import time

from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
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


async def run_bot(websocket, call_data, scenario):
    logger.info(f"Starting bot for scenario: {scenario.name} ({scenario.id})")

    stream_sid = call_data.get("stream_id")
    call_sid = call_data.get("call_id")
    call_start = time.time()
    turns = []

    # --- VAD ---
    vad = SileroVADAnalyzer(params=VADParams(stop_secs=0.6))

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
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            vad_analyzer=vad,
        ),
    )

    # --- Services ---
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice=scenario.voice,
    )

    llm = AnthropicLLMService(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        settings=AnthropicLLMService.Settings(
            model="claude-haiku-4-5-20250315",
            max_tokens=200,
            temperature=0.7,
        ),
    )

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
        for msg in frame.messages:
            turns.append({
                "role": msg.role,
                "text": msg.content,
                "time": f"{minutes:02d}:{seconds:02d}",
            })

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

    @task.event_handler("on_pipeline_finished")
    async def on_pipeline_finished(task, frame):
        await audiobuffer.stop_recording()
        if turns:
            filepath = save_transcript(turns, scenario.id)
            logger.info(f"Transcript saved: {filepath}")

    # Start recording and run
    await audiobuffer.start_recording()
    runner = PipelineRunner()
    await runner.run(task)
    logger.info(f"Call completed for scenario: {scenario.id}")
