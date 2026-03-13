import asyncio
import sys
import threading
import time

# Windows asyncio fix — must be before any async code
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from dotenv import load_dotenv
from loguru import logger

from src.scenarios import list_scenarios
from src.server import app, make_call, start_ngrok, stop_ngrok

load_dotenv()

SERVER_PORT = 8765


def print_menu():
    print("\n" + "=" * 50)
    print("  Patient Voice Bot — Scenario Menu")
    print("=" * 50)
    scenarios = list_scenarios()
    for i, s in enumerate(scenarios, 1):
        print(f"  {i:2d}. [{s.id}] {s.name}")
    print(f"  {'q':>3}. Quit")
    print("=" * 50)


def run_server():
    """Run uvicorn in a background thread."""
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="warning")


def main():
    # Start FastAPI server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # Let server start
    logger.info(f"Server running on port {SERVER_PORT}")

    # Start ngrok tunnel
    try:
        url = start_ngrok(SERVER_PORT)
        logger.info(f"ngrok ready: {url}")
    except Exception:
        logger.exception("Failed to start ngrok")
        return

    scenarios = list_scenarios()

    try:
        while True:
            print_menu()
            choice = input("\nSelect scenario (number or 'q'): ").strip()

            if choice.lower() == "q":
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(scenarios):
                    scenario = scenarios[idx]
                    print(f"\nCalling with scenario: {scenario.name} ({scenario.id})")
                    print(f"Patient: {scenario.patient_name}")
                    print(f"Target: +1-805-439-8008")
                    print()

                    confirm = input("Start call? (y/n): ").strip().lower()
                    if confirm != "y":
                        print("Skipped.")
                        continue

                    call_sid = make_call(scenario.id)
                    print(f"Call started (SID: {call_sid})")
                    print("Waiting for call to complete... (check logs for progress)")
                    print("Press Enter when done to return to menu.")
                    input()
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
            except Exception:
                logger.exception("Call failed")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_ngrok()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    main()
