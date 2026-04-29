import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydub import AudioSegment

# Windows ffmpeg: set explicit path as safety net
if sys.platform == "win32":
    ffmpeg_path = Path(r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe")
    if ffmpeg_path.exists():
        AudioSegment.converter = str(ffmpeg_path)

RECORDINGS_DIR = Path("recordings")
TRANSCRIPTS_DIR = Path("transcripts")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"recorder.py: RECORDINGS_DIR resolved to {RECORDINGS_DIR.resolve()}")
logger.info(f"recorder.py: TRANSCRIPTS_DIR resolved to {TRANSCRIPTS_DIR.resolve()}")


def make_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_recording(audio_bytes, scenario_id, sample_rate=8000, channels=1):
    logger.info(
        f"save_recording: scenario={scenario_id}, "
        f"bytes={len(audio_bytes) if audio_bytes else 0}, "
        f"sample_rate={sample_rate}, channels={channels}"
    )
    if not audio_bytes:
        logger.warning("save_recording: audio_bytes is empty — skipping")
        return None
    audio = AudioSegment(
        data=audio_bytes,
        sample_width=2,
        frame_rate=sample_rate,
        channels=channels,
    )
    timestamp = make_timestamp()
    filepath = RECORDINGS_DIR / f"{scenario_id}_{timestamp}.mp3"
    logger.info(f"save_recording: exporting to {filepath.resolve()}")
    audio.export(str(filepath), format="mp3", codec="libmp3lame", bitrate="128k")
    logger.info(f"save_recording: export complete ({filepath.stat().st_size} bytes)")
    return filepath


def save_transcript(turns, scenario_id):
    logger.info(f"save_transcript: scenario={scenario_id}, turns={len(turns)}")
    timestamp = make_timestamp()
    filepath = TRANSCRIPTS_DIR / f"{scenario_id}_{timestamp}.txt"
    lines = []
    for turn in turns:
        role = turn["role"].upper()
        text = turn["text"]
        time_str = turn.get("time", "00:00")
        lines.append(f"[{time_str}] {role}: {text}")
    filepath.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"save_transcript: wrote {filepath.resolve()} ({filepath.stat().st_size} bytes)")
    return filepath
