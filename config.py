import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")

print("CONFIG LOADED:", BOT_TOKEN)

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",")]
SERVICE_FEE = 10