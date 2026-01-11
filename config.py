import os
from pathlib import Path

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
print(f"DEBUG: BOT_TOKEN value: {BOT_TOKEN[:10] if BOT_TOKEN else 'NOT FOUND'}...")
print(f"DEBUG: All env vars: {list(os.environ.keys())}")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# File Paths
TEMP_DIR = Path("./temp")
TEMP_DIR.mkdir(exist_ok=True)

# Watermark Configuration
WATERMARK_TEXT = "Search ON TG @Linkz_Wallah"
WATERMARK_OPACITY = 0.6

# Sample Duration Rules (in seconds)
LONG_VIDEO_THRESHOLD = 120  # Videos longer than this
LONG_VIDEO_SAMPLE = 30      # Get 30 sec sample
SHORT_VIDEO_SAMPLE = 10     # Otherwise 10 sec

# FFmpeg Settings
FFMPEG_PRESET = "veryfast"
FFMPEG_CRF = 23  # Quality (lower = better, 18-28 recommended)

# Telegram Settings
MAX_EDIT_INTERVAL = 1.0  # Minimum seconds between message edits

# Supported Formats
SUPPORTED_FORMATS = [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".m4v"]
