"""
Transcription Module
Handles YouTube caption extraction with Whisper fallback.
"""

import subprocess
import shutil
import tempfile
import json
import re
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))
from db import DATA_DIR

SOURCES_DIR = DATA_DIR / "sources"


def _run_with_caffeinate(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command with caffeinate on macOS, or directly on other platforms."""
    if shutil.which("caffeinate"):
        cmd = ["caffeinate", "-i"] + cmd
    return subprocess.run(cmd, **kwargs)


def get_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_metadata(url: str) -> dict:
    """Get video metadata using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", "Unknown"),
                "channel": data.get("channel", "Unknown"),
                "duration": data.get("duration", 0),
                "upload_date": data.get("upload_date", ""),
                "description": data.get("description", "")[:500],
                "view_count": data.get("view_count", 0),
            }
    except Exception as e:
        print(f"Error getting metadata: {e}")
    return {"title": "Unknown", "channel": "Unknown", "duration": 0}


def download_captions(url: str) -> Optional[str]:
    """
    Download captions using yt-dlp.
    Tries auto-generated captions if manual ones aren't available.
    Returns transcript text with timestamps.
    """
    video_id = get_youtube_id(url)
    if not video_id:
        return None

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", "en",
                "--sub-format", "vtt",
                "--skip-download",
                "-o", f"{tmpdir}/%(id)s.%(ext)s",
                url
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if vtt_files:
            vtt_path = vtt_files[0]
            transcript = parse_vtt(vtt_path.read_text())

            transcript_path = SOURCES_DIR / f"{video_id}.txt"
            transcript_path.write_text(transcript)

            return transcript

    return None


def parse_vtt(vtt_content: str) -> str:
    """
    Parse VTT subtitle file into readable transcript with timestamps.
    Deduplicates repeated lines from auto-captions.
    """
    lines = vtt_content.split('\n')
    transcript_parts = []
    current_text = ""
    current_timestamp = ""
    seen_texts = set()

    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2})\.\d{3} --> ')

    for line in lines:
        line = line.strip()

        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue

        match = timestamp_pattern.match(line)
        if match:
            current_timestamp = match.group(1)
            continue

        if not line or line.startswith('align:') or '-->' in line:
            continue

        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = re.sub(r'&nbsp;', ' ', clean_line)
        clean_line = clean_line.strip()

        if clean_line and clean_line not in seen_texts:
            seen_texts.add(clean_line)
            if current_timestamp:
                transcript_parts.append(f"[{current_timestamp}] {clean_line}")
            else:
                transcript_parts.append(clean_line)

    return '\n'.join(transcript_parts)


def transcribe_with_whisper(url: str, model: str = "base") -> Optional[str]:
    """
    Download audio and transcribe with Whisper.
    Used as fallback when captions aren't available.
    """
    video_id = get_youtube_id(url)
    if not video_id:
        return None

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.mp3"

        print(f"Downloading audio for {video_id}...")
        result = _run_with_caffeinate(
            [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "-o", str(audio_path),
                url
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            print(f"Error downloading audio: {result.stderr}")
            return None

        audio_files = list(Path(tmpdir).glob("audio*"))
        if not audio_files:
            print("No audio file found")
            return None

        actual_audio = audio_files[0]

        print(f"Transcribing with Whisper ({model} model)...")
        result = _run_with_caffeinate(
            [
                "whisper",
                str(actual_audio),
                "--model", model,
                "--output_format", "txt",
                "--output_dir", tmpdir
            ],
            capture_output=True,
            text=True,
            timeout=1800
        )

        if result.returncode != 0:
            print(f"Whisper error: {result.stderr}")
            return None

        txt_files = list(Path(tmpdir).glob("*.txt"))
        if txt_files:
            transcript = txt_files[0].read_text()

            transcript_path = SOURCES_DIR / f"{video_id}_whisper.txt"
            transcript_path.write_text(transcript)

            return transcript

    return None


def transcribe_audio_file(audio_path: str, model: str = "base") -> Optional[str]:
    """
    Transcribe a local audio file with Whisper.

    Args:
        audio_path: Path to audio file (mp3, wav, m4a, etc.)
        model: Whisper model to use (tiny, base, small, medium, large)

    Returns:
        Transcript text or None on failure
    """
    path = Path(audio_path)
    if not path.exists():
        print(f"Audio file not found: {audio_path}")
        return None

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Transcribing {path.name} with Whisper ({model} model)...")

        result = _run_with_caffeinate(
            [
                "whisper",
                str(path.absolute()),
                "--model", model,
                "--output_format", "txt",
                "--output_dir", tmpdir
            ],
            capture_output=True,
            text=True,
            timeout=3600
        )

        if result.returncode != 0:
            print(f"Whisper error: {result.stderr}")
            return None

        txt_files = list(Path(tmpdir).glob("*.txt"))
        if txt_files:
            transcript = txt_files[0].read_text()
            return transcript

    return None


def transcribe_youtube(url: str, force_whisper: bool = False) -> tuple[Optional[str], dict]:
    """
    Main entry point for YouTube transcription.
    Tries captions first, falls back to Whisper.

    Returns: (transcript, metadata)
    """
    metadata = get_video_metadata(url)

    if not force_whisper:
        print("Attempting to download captions...")
        transcript = download_captions(url)
        if transcript:
            metadata["transcription_method"] = "captions"
            return transcript, metadata
        print("No captions found, falling back to Whisper...")

    transcript = transcribe_with_whisper(url)
    if transcript:
        metadata["transcription_method"] = "whisper"
        return transcript, metadata

    return None, metadata


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Transcribing: {url}")
        transcript, metadata = transcribe_youtube(url)
        if transcript:
            print(f"\nTitle: {metadata.get('title')}")
            print(f"Duration: {metadata.get('duration')}s")
            print(f"Method: {metadata.get('transcription_method')}")
            print(f"\nTranscript preview:\n{transcript[:500]}...")
        else:
            print("Failed to transcribe")
    else:
        print("Usage: python transcribe.py <youtube_url>")
