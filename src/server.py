import os

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from loguru import logger
from pyngrok import ngrok
from twilio.rest import Client as TwilioClient

from pipecat.runner.utils import parse_telephony_websocket

from src.bot import run_bot
from src.scenarios import get_scenario

load_dotenv()

# --- Safety constants ---
TARGET_NUMBER = "+18054398008"  # ONLY number we ever call
MAX_CALL_DURATION_SECONDS = 180
MAX_CALLS_PER_SESSION = 15

# --- Twilio client ---
twilio_client = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN"),
)

# --- State ---
ngrok_url = None
call_count = 0

app = FastAPI()


def start_ngrok(port: int) -> str:
    """Start ngrok tunnel and return the public URL (without scheme)."""
    global ngrok_url
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if auth_token:
        ngrok.set_auth_token(auth_token)
    tunnel = ngrok.connect(port, "http")
    # tunnel.public_url is like "https://xxxx.ngrok-free.app"
    ngrok_url = tunnel.public_url.replace("https://", "").replace("http://", "")
    logger.info(f"ngrok tunnel: wss://{ngrok_url}/ws")
    return ngrok_url


def stop_ngrok():
    ngrok.kill()


def make_call(scenario_id: str) -> str:
    """Initiate a Twilio outbound call. Returns the call SID."""
    global call_count

    if call_count >= MAX_CALLS_PER_SESSION:
        raise RuntimeError(f"Session limit reached ({MAX_CALLS_PER_SESSION} calls)")

    if not ngrok_url:
        raise RuntimeError("ngrok tunnel not started — call start_ngrok() first")

    scenario = get_scenario(scenario_id)
    if not scenario:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    twiml = (
        f'<Response><Connect><Stream url="wss://{ngrok_url}/ws">'
        f'<Parameter name="scenario_id" value="{scenario.id}"/>'
        f'</Stream></Connect></Response>'
    )

    call = twilio_client.calls.create(
        to=TARGET_NUMBER,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        twiml=twiml,
        record=True,
        time_limit=MAX_CALL_DURATION_SECONDS,
    )

    call_count += 1
    logger.info(f"Call initiated: SID={call.sid}, scenario={scenario_id} ({call_count}/{MAX_CALLS_PER_SESSION})")
    return call.sid


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        transport_type, call_data = await parse_telephony_websocket(websocket)
        logger.info(f"WebSocket connected: transport={transport_type}")

        # Extract scenario from TwiML <Parameter>
        scenario_id = call_data.get("body", {}).get("scenario_id", "01_scheduling")
        scenario = get_scenario(scenario_id)
        if not scenario:
            logger.error(f"Unknown scenario: {scenario_id}")
            return

        await run_bot(websocket, call_data, scenario)

    except Exception:
        logger.exception("Error in WebSocket handler")
