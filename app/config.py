import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env if exists
env_path = BASE_DIR / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "9196597210:AAHChWRsxuT7drlWweLWHGv5gK7XaeXt7eU")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Mini App URL (Cloudflare Tunnel live public HTTPS URL)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://partial-feeding-baker-discovery.trycloudflare.com")

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "bot_data.db"
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
