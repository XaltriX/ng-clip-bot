# 🎬 Telegram Video Sample Generator Bot

A powerful Telegram bot that generates watermarked video samples with live progress tracking. Designed for personal use with unlimited queue support.

## ✨ Features

- **Automatic Sample Generation**: 10-30 second samples based on video length
- **Centered Watermark**: Professional "Search ON TG @Linkz_Wallah" watermark
- **Live Progress Updates**: Real-time FFmpeg progress bar
- **Unlimited Queue**: Process multiple videos sequentially
- **Smart Quality**: Auto-adjusts bitrate based on resolution
- **Auto Cleanup**: All files deleted after processing
- **Heroku Ready**: Full Heroku deployment support

## 📋 Sample Rules

- Videos **> 2 minutes** → 30 second sample
- Videos **≤ 2 minutes** → 10 second sample
- Sample cut from **middle** of video
- Watermark always **centered** and visible

## 🚀 Local Setup

### Prerequisites

- Python 3.10+
- FFmpeg installed (`sudo apt install ffmpeg` on Ubuntu/Debian)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd telegram-video-sample-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your BOT_TOKEN

# Run bot
python bot.py
```

## ☁️ Heroku Deployment

### Step 1: Prepare Files

Ensure you have all required files:
- `runtime.txt`
- `Procfile`
- `Aptfile` (for FFmpeg)
- `requirements.txt`

### Step 2: Create Heroku App

```bash
# Login to Heroku
heroku login

# Create new app
heroku create your-app-name

# Add buildpacks (ORDER MATTERS)
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/python
```

### Step 3: Configure Environment

```bash
# Set bot token
heroku config:set BOT_TOKEN=your_bot_token_here
```

### Step 4: Deploy

```bash
# Push to Heroku
git add .
git commit -m "Initial deployment"
git push heroku main

# Check logs
heroku logs --tail
```

### Step 5: Scale Worker

```bash
# Start the worker dyno
heroku ps:scale worker=1

# Check status
heroku ps
```

## 🎮 Bot Commands

- `/start` - Welcome message and bot info
- `/help` - Detailed usage instructions
- `/queue` - Check current queue status

## 📁 Supported Formats

MP4, MKV, WebM, AVI, MOV, FLV, M4V

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Watermark text
WATERMARK_TEXT = "Search ON TG @Linkz_Wallah"

# Sample durations
LONG_VIDEO_THRESHOLD = 120  # seconds
LONG_VIDEO_SAMPLE = 30      # seconds
SHORT_VIDEO_SAMPLE = 10     # seconds

# FFmpeg quality
FFMPEG_PRESET = "veryfast"  # ultrafast, superfast, veryfast, faster, fast, medium
FFMPEG_CRF = 23             # 18-28 (lower = better quality)
```

## 📊 How It Works

1. **User sends video** → Bot downloads to temp storage
2. **Added to queue** → Position shown to user
3. **Analysis** → FFprobe extracts duration and resolution
4. **Processing** → FFmpeg creates sample with watermark
5. **Progress tracking** → Live progress bar updates every 5%
6. **Upload** → Sample sent back to user
7. **Cleanup** → All files automatically deleted

## 🛡️ Privacy

- All files stored in `/temp` directory
- Files deleted immediately after processing
- Heroku ephemeral filesystem auto-cleans on restart
- No permanent storage of user videos

## 🐛 Troubleshooting

### Bot not responding
```bash
# Check Heroku logs
heroku logs --tail

# Restart worker
heroku ps:restart worker
```

### FFmpeg errors
```bash
# Verify buildpack
heroku buildpacks

# Should show:
# 1. heroku-community/apt
# 2. heroku/python
```

### Out of memory
```bash
# Upgrade dyno (Heroku)
heroku ps:resize worker=standard-1x
```

## 📝 Project Structure

```
telegram-video-sample-bot/
├── bot.py              # Main bot logic and handlers
├── queue_handler.py    # Queue processing system
├── utils.py            # FFmpeg/file utilities
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version
├── Procfile           # Heroku process type
├── Aptfile            # System dependencies (FFmpeg)
├── .env.example       # Environment template
└── README.md          # This file
```

## 🤝 Contributing

This is a personal project, but feel free to fork and customize!

## 📄 License

MIT License - Use freely for personal projects

## 🙏 Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [FFmpeg](https://ffmpeg.org/)
- [Heroku](https://heroku.com/)

---

**Made with ❤️ for video content creators**
