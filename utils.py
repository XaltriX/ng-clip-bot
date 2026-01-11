import asyncio
import json
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, Callable
import logging

from config import (
    TEMP_DIR, WATERMARK_TEXT, WATERMARK_OPACITY,
    FFMPEG_PRESET, FFMPEG_CRF, SUPPORTED_FORMATS
)

logger = logging.getLogger(__name__)


async def cleanup_temp_files():
    """Clean all files in temp directory"""
    try:
        if TEMP_DIR.exists():
            for file in TEMP_DIR.iterdir():
                try:
                    if file.is_file():
                        file.unlink()
                        logger.info(f"Deleted: {file}")
                except Exception as e:
                    logger.error(f"Failed to delete {file}: {e}")
        logger.info("Temp directory cleaned")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


def delete_file(file_path: Path):
    """Safely delete a file"""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete {file_path}: {e}")


async def get_video_info(file_path: Path) -> Optional[dict]:
    """Get video duration and resolution using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height",
            "-of", "json",
            str(file_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"FFprobe error: {stderr.decode()}")
            return None
        
        data = json.loads(stdout.decode())
        
        duration = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])
        
        width = height = 0
        for stream in streams:
            if "width" in stream:
                width = stream["width"]
                height = stream["height"]
                break
        
        return {
            "duration": duration,
            "width": width,
            "height": height
        }
    
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        return None


def calculate_sample_params(duration: float) -> Tuple[float, float]:
    """Calculate sample duration and start time"""
    from config import LONG_VIDEO_THRESHOLD, LONG_VIDEO_SAMPLE, SHORT_VIDEO_SAMPLE
    
    if duration > LONG_VIDEO_THRESHOLD:
        sample_duration = LONG_VIDEO_SAMPLE
    else:
        sample_duration = SHORT_VIDEO_SAMPLE
    
    # Cut from middle
    start_time = max(0, (duration / 2) - (sample_duration / 2))
    
    return start_time, sample_duration


def get_bitrate_for_resolution(width: int, height: int) -> str:
    """Determine appropriate bitrate based on resolution"""
    pixels = width * height
    
    if pixels <= 640 * 480:  # 480p or lower
        return "500k"
    elif pixels <= 1280 * 720:  # 720p
        return "1000k"
    elif pixels <= 1920 * 1080:  # 1080p
        return "2000k"
    else:  # 4K+
        return "4000k"


def build_watermark_filter(width: int, height: int) -> str:
    """Build FFmpeg drawtext filter for centered watermark"""
    # Auto-scale font size based on resolution
    font_size = int(min(width, height) * 0.04)  # 4% of smaller dimension
    
    # Escape text for FFmpeg
    text = WATERMARK_TEXT.replace(":", r"\:")
    
    return (
        f"drawtext=text='{text}':"
        f"fontsize={font_size}:"
        f"fontcolor=white@{WATERMARK_OPACITY}:"
        f"borderw=2:"
        f"bordercolor=black@0.8:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2"
    )


async def create_sample_video(
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration: float,
    width: int,
    height: int,
    progress_callback: Optional[Callable[[float], None]] = None
) -> bool:
    """
    Create sample video with watermark using FFmpeg
    Returns True on success, False on failure
    """
    try:
        bitrate = get_bitrate_for_resolution(width, height)
        watermark_filter = build_watermark_filter(width, height)
        
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(start_time),
            "-i", str(input_path),
            "-t", str(duration),
            "-vf", watermark_filter,
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-crf", str(FFMPEG_CRF),
            "-b:v", bitrate,
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-loglevel", "error",
            str(output_path)
        ]
        
        logger.info(f"Starting FFmpeg: {' '.join(cmd)}")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Monitor progress
        last_progress = 0.0
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # Parse out_time_ms for progress
            if "out_time_ms=" in line_str:
                match = re.search(r"out_time_ms=(\d+)", line_str)
                if match:
                    time_ms = int(match.group(1))
                    time_sec = time_ms / 1_000_000
                    progress = min(time_sec / duration, 1.0)
                    
                    if progress_callback and progress - last_progress >= 0.05:
                        await progress_callback(progress)
                        last_progress = progress
        
        await proc.wait()
        
        if proc.returncode == 0 and output_path.exists():
            logger.info("FFmpeg completed successfully")
            return True
        else:
            stderr = await proc.stderr.read()
            logger.error(f"FFmpeg failed: {stderr.decode()}")
            return False
    
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return False


def format_progress_bar(progress: float, length: int = 10) -> str:
    """Create a text progress bar"""
    filled = int(progress * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(progress * 100)
    return f"{bar} {percent}%"


def is_supported_format(filename: str) -> bool:
    """Check if file format is supported"""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_FORMATS
