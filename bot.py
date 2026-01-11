import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, TEMP_DIR
from utils import cleanup_temp_files, is_supported_format
from queue_handler import QueueManager, VideoJob

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global queue manager
queue_manager: QueueManager = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = (
        "🎬 **Video Sample Generator Bot**\n\n"
        "Send me any video and I'll create a watermarked sample!\n\n"
        "**Features:**\n"
        "• Auto sample generation (10-30 sec)\n"
        "• Centered watermark\n"
        "• Live progress updates\n"
        "• Unlimited queue support\n\n"
        "**Commands:**\n"
        "/start - Show this message\n"
        "/queue - Check queue status\n"
        "/help - Get help\n\n"
        "Just send me a video to begin! 🚀"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **How to Use:**\n\n"
        "1. Send me a video file\n"
        "2. Wait for processing (I'll show progress)\n"
        "3. Receive your watermarked sample!\n\n"
        "**Sample Rules:**\n"
        "• Videos >2 min → 30 sec sample\n"
        "• Videos ≤2 min → 10 sec sample\n"
        "• Sample cut from middle of video\n\n"
        "**Supported Formats:**\n"
        "MP4, MKV, WebM, AVI, MOV, FLV, M4V\n\n"
        "**Note:** All files are deleted after processing for privacy."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /queue command"""
    queue_size = queue_manager.get_queue_size()
    is_processing = queue_manager.is_processing
    
    if is_processing:
        status = f"🔄 **Currently processing a video**\n📋 Videos in queue: {queue_size}"
    elif queue_size > 0:
        status = f"📋 Videos in queue: {queue_size}"
    else:
        status = "✅ Queue is empty. Send a video to start!"
    
    await update.message.reply_text(status, parse_mode="Markdown")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video files"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    
    # Get video file
    if update.message.video:
        video = update.message.video
        filename = f"{video.file_id}.mp4"
    elif update.message.document:
        video = update.message.document
        filename = video.file_name or f"{video.file_id}.mp4"
    else:
        await update.message.reply_text("❌ No video detected. Please send a video file.")
        return
    
    # Check format
    if not is_supported_format(filename):
        await update.message.reply_text(
            "❌ Unsupported format. Please send: MP4, MKV, WebM, AVI, MOV, FLV, or M4V"
        )
        return
    
    # Check file size (optional, Telegram already limits this)
    file_size_mb = video.file_size / (1024 * 1024) if video.file_size else 0
    logger.info(f"Received video from user {user_id}: {filename} ({file_size_mb:.2f} MB)")
    
    # Send initial status
    status_msg = await update.message.reply_text("📥 Downloading video...")
    
    try:
        # Download file
        file = await context.bot.get_file(video.file_id)
        input_path = TEMP_DIR / f"{user_id}_{message_id}.input"
        output_path = TEMP_DIR / f"{user_id}_{message_id}.output.mp4"
        
        await file.download_to_drive(input_path)
        logger.info(f"Downloaded to: {input_path}")
        
        # Create job
        job = VideoJob(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            input_path=input_path,
            output_path=output_path,
            status_message_id=status_msg.message_id
        )
        
        # Add to queue
        position = await queue_manager.add_job(job)
        
        if position == 1 and not queue_manager.is_processing:
            await status_msg.edit_text("🎬 Processing your video...")
        else:
            await status_msg.edit_text(f"🎬 Video added to queue | Position: #{position}")
    
    except Exception as e:
        logger.error(f"Error handling video: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Download failed: {str(e)[:100]}")


async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unsupported message types"""
    await update.message.reply_text(
        "⚠️ Please send a video file.\n\n"
        "Use /help for more information."
    )


async def post_init(application: Application):
    """Initialize after app is set up"""
    global queue_manager
    
    logger.info("Starting bot initialization...")
    
    # Clean temp directory
    await cleanup_temp_files()
    
    # Initialize queue manager
    queue_manager = QueueManager(application.bot)
    
    # Start queue worker
    asyncio.create_task(queue_manager.start_worker())
    
    logger.info("Bot initialized successfully!")


def main():
    """Start the bot"""
    logger.info("Starting Video Sample Generator Bot...")
    
    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("queue", queue_command))
    
    # Video handlers
    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            handle_video
        )
    )
    
    # Catch-all for other messages
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND & ~filters.VIDEO & ~filters.Document.VIDEO,
            handle_unsupported
        )
    )
    
    # Start bot
    logger.info("Bot is now running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
