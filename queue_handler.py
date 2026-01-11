import asyncio
import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from telegram import Bot
from telegram.error import TelegramError

from config import TEMP_DIR, MAX_EDIT_INTERVAL
from utils import (
    get_video_info,
    calculate_sample_params,
    create_sample_video,
    delete_file,
    format_progress_bar
)

logger = logging.getLogger(__name__)


@dataclass
class VideoJob:
    """Represents a video processing job"""
    user_id: int
    chat_id: int
    message_id: int
    input_path: Path
    output_path: Path
    status_message_id: Optional[int] = None


class QueueManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.is_processing = False
        self.current_job: Optional[VideoJob] = None
        self.queue_counter = 0
        self.last_edit_time = {}
    
    async def add_job(self, job: VideoJob) -> int:
        """Add job to queue and return position"""
        await self.queue.put(job)
        self.queue_counter += 1
        position = self.queue.qsize()
        logger.info(f"Job added to queue. Position: {position}")
        return position
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
    
    async def start_worker(self):
        """Start the queue worker task"""
        logger.info("Starting queue worker")
        while True:
            try:
                job = await self.queue.get()
                self.current_job = job
                self.is_processing = True
                
                await self._process_job(job)
                
                self.queue.task_done()
                self.current_job = None
                self.is_processing = False
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                self.is_processing = False
    
    async def _update_status(self, job: VideoJob, text: str, force: bool = False):
        """Update status message with rate limiting"""
        try:
            if not job.status_message_id:
                return
            
            current_time = time.time()
            last_time = self.last_edit_time.get(job.status_message_id, 0)
            
            if force or (current_time - last_time) >= MAX_EDIT_INTERVAL:
                await self.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=text
                )
                self.last_edit_time[job.status_message_id] = current_time
                
        except TelegramError as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Failed to update status: {e}")
    
    async def _process_job(self, job: VideoJob):
        """Process a single video job"""
        logger.info(f"Processing job for user {job.user_id}")
        
        try:
            # Stage 1: Analyze video
            await self._update_status(job, "📏 Analyzing video...", force=True)
            
            video_info = await get_video_info(job.input_path)
            
            if not video_info:
                await self._update_status(
                    job,
                    "❌ Failed to analyze video. File may be corrupted.",
                    force=True
                )
                self._cleanup_job(job)
                return
            
            duration = video_info["duration"]
            width = video_info["width"]
            height = video_info["height"]
            
            if duration <= 0:
                await self._update_status(
                    job,
                    "❌ Invalid video duration detected.",
                    force=True
                )
                self._cleanup_job(job)
                return
            
            logger.info(f"Video info: {duration}s, {width}x{height}")
            
            # Stage 2: Calculate sample parameters
            start_time, sample_duration = calculate_sample_params(duration)
            
            await self._update_status(
                job,
                f"✂️ Cutting {sample_duration}s sample from middle...",
                force=True
            )
            
            # Stage 3: Create sample with progress tracking
            async def progress_callback(progress: float):
                bar = format_progress_bar(progress)
                await self._update_status(
                    job,
                    f"🎬 Processing sample...\n{bar}"
                )
            
            success = await create_sample_video(
                job.input_path,
                job.output_path,
                start_time,
                sample_duration,
                width,
                height,
                progress_callback
            )
            
            if not success:
                await self._update_status(
                    job,
                    "❌ Failed to create sample. FFmpeg error.",
                    force=True
                )
                self._cleanup_job(job)
                return
            
            # Stage 4: Upload result
            await self._update_status(job, "📤 Uploading sample...", force=True)
            
            with open(job.output_path, "rb") as video_file:
                await self.bot.send_video(
                    chat_id=job.chat_id,
                    video=video_file,
                    caption="✅ Sample Ready | Watermarked Preview",
                    supports_streaming=True
                )
            
            # Delete status message
            try:
                await self.bot.delete_message(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id
                )
            except:
                pass
            
            logger.info(f"Job completed for user {job.user_id}")
        
        except Exception as e:
            logger.error(f"Job processing error: {e}", exc_info=True)
            await self._update_status(
                job,
                f"❌ Processing failed: {str(e)[:100]}",
                force=True
            )
        
        finally:
            self._cleanup_job(job)
    
    def _cleanup_job(self, job: VideoJob):
        """Clean up job files"""
        logger.info(f"Cleaning up job files for user {job.user_id}")
        delete_file(job.input_path)
        delete_file(job.output_path)
