#!/usr/bin/env python3
"""Prepare timestamp-linked caption artifacts for semantic sermon extraction."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


TIMING = re.compile(
    r"^((?:(\d{2}):)?(\d{2}):(\d{2})\.\d{3})\s+-->\s+"
    r"((?:(\d{2}):)?(\d{2}):(\d{2})\.\d{3})(?:\s+.*)?$"
)
INLINE_TIMESTAMP = re.compile(r"<(?:\d{2}:)?\d{2}:\d{2}\.\d{3}>")
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
CAPTION_CHEVRON = re.compile(r"(?<!\S)>{1,2}(?=\s|[A-Za-z])\s*")
SENTENCE_END = re.compile(r"[.!?](?:[\"'”’)]*)$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass
class Cue:
    start_seconds: int
    end_seconds: int
    lines: list[str]


def seconds_from_match(hours: str | None, minutes: str, seconds: str) -> int:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)


def format_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def clean_line(line: str) -> str:
    line = INLINE_TIMESTAMP.sub("", line)
    line = TAG.sub("", line)
    # YouTube uses > or >> as speaker-change cues. If retained at the start of
    # a Markdown paragraph, they accidentally render the transcript as a quote.
    line = CAPTION_CHEVRON.sub("", line)
    return SPACE.sub(" ", html.unescape(line)).strip()


def parse_vtt(path: Path) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig"))
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if TIMING.match(line)), None)
        if timing_index is None:
            continue
        match = TIMING.match(lines[timing_index])
        assert match is not None
        start = seconds_from_match(match.group(2), match.group(3), match.group(4))
        end = seconds_from_match(match.group(6), match.group(7), match.group(8))
        payload = [clean_line(line) for line in lines[timing_index + 1 :]]
        payload = [line for line in payload if line]
        if payload:
            cues.append(Cue(start, end, payload))
    return cues


def append_new_text(transcript: str, caption: str) -> tuple[str, str]:
    if not caption or caption == transcript or transcript.endswith(caption):
        return transcript, ""
    lower_transcript = transcript.lower()
    lower_caption = caption.lower()
    overlap = 0
    for size in range(min(len(transcript), len(caption)), 0, -1):
        if lower_transcript[-size:] == lower_caption[:size]:
            overlap = size
            break
    addition = caption[overlap:].strip()
    if not addition:
        return transcript, ""
    return (f"{transcript} {addition}" if transcript else addition), addition


def build_segments(cues: list[Cue]) -> list[dict[str, object]]:
    transcript = ""
    segments: list[dict[str, object]] = []
    for cue in cues:
        additions: list[str] = []
        for line in cue.lines:
            transcript, addition = append_new_text(transcript, line)
            if addition:
                additions.append(addition)
        text = " ".join(additions).strip()
        if not text:
            continue
        if segments and segments[-1]["start_seconds"] == cue.start_seconds:
            segments[-1]["text"] = f'{segments[-1]["text"]} {text}'
            segments[-1]["end_seconds"] = cue.end_seconds
        else:
            segments.append(
                {
                    "start": format_time(cue.start_seconds),
                    "start_seconds": cue.start_seconds,
                    "end": format_time(cue.end_seconds),
                    "end_seconds": cue.end_seconds,
                    "text": text,
                }
            )
    return segments


def paragraph_markdown(segments: list[dict[str, object]], sentence_limit: int) -> str:
    paragraphs: list[str] = []
    text_parts: list[str] = []
    timestamp = "00:00:00"
    sentence_count = 0
    for segment in segments:
        if not text_parts:
            timestamp = str(segment["start"])
        part = str(segment["text"])
        text_parts.append(part)
        sentence_count += len(re.findall(r"[.!?](?:[\"'”’)]*)(?=\s|$)", part))
        if sentence_count >= sentence_limit and SENTENCE_END.search(part):
            paragraphs.append(f"[{timestamp}]\n\n{' '.join(text_parts)}")
            text_parts = []
            sentence_count = 0
    if text_parts:
        paragraphs.append(f"[{timestamp}]\n\n{' '.join(text_parts)}")
    return "\n\n".join(paragraphs).strip() + "\n"


def youtube_id(source: str) -> str | None:
    parsed = urlparse(source)
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.hostname and "youtube.com" in parsed.hostname:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    else:
        return None
    return candidate if VIDEO_ID.match(candidate) else None


def download_vtt(url: str, directory: Path) -> tuple[Path, dict[str, object]]:
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp is required for YouTube URLs but was not found in PATH")
    command = [
        "yt-dlp",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs",
        "en.*",
        "--sub-format",
        "vtt",
        "--skip-download",
        "--write-info-json",
        "--no-playlist",
        "-o",
        str(directory / "%(title)s [%(id)s].%(ext)s"),
        url,
    ]
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip())
    candidates = list(directory.glob("*.vtt"))
    if not candidates:
        raise SystemExit("No English VTT captions were available for this video")
    candidates.sort(key=lambda path: (".en.vtt" not in path.name, len(path.name)))
    info_files = list(directory.glob("*.info.json"))
    video_metadata: dict[str, object] = {}
    if info_files:
        video_metadata = json.loads(info_files[0].read_text(encoding="utf-8"))
    return candidates[0], video_metadata


def iso_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    digits = value.replace("-", "")
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    return None


def select_video_metadata(info: dict[str, object]) -> dict[str, object]:
    """Keep useful, human-readable metadata without copying yt-dlp internals."""
    release_date = iso_date(info.get("release_date"))
    upload_date = iso_date(info.get("upload_date"))
    service_date_candidate = release_date or upload_date
    date_source = "release_date" if release_date else "upload_date" if upload_date else None
    return {
        "title": info.get("title"),
        "description": info.get("description"),
        "channel": info.get("channel") or info.get("uploader"),
        "webpage_url": info.get("webpage_url") or info.get("original_url"),
        "live_status": info.get("live_status"),
        "release_date": release_date,
        "upload_date": upload_date,
        "service_date_candidate": service_date_candidate,
        "service_date_source": date_source,
    }


def safe_stem(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"\.(?:en(?:-[A-Za-z]+)?|en-orig)$", "", stem)
    return re.sub(r"[^A-Za-z0-9._ -]+", "", stem).strip() or "transcript"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download or parse captions into timestamp-linked transcript artifacts."
    )
    parser.add_argument("source", help="YouTube URL or local .vtt file")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--paragraph-sentences", type=int, default=5, metavar="N")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.paragraph_sentences < 1:
        raise SystemExit("--paragraph-sentences must be at least 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    video_id = youtube_id(args.source)
    video_metadata: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="sermon-transcript-") as temporary:
        source_path = Path(args.source).expanduser()
        if source_path.is_file():
            vtt_path = source_path
        elif video_id:
            vtt_path, raw_metadata = download_vtt(args.source, Path(temporary))
            video_metadata = select_video_metadata(raw_metadata)
        else:
            raise SystemExit(f"Not a local VTT file or recognized YouTube URL: {args.source}")

        segments = build_segments(parse_vtt(vtt_path))
        if not segments:
            raise SystemExit("No caption text could be extracted from the VTT file")
        stem = safe_stem(vtt_path)
        json_path = args.output_dir / f"{stem}.segments.json"
        markdown_path = args.output_dir / f"{stem}.cleaned.md"
        metadata = {
            "source": args.source,
            "video_id": video_id,
            "video_metadata": video_metadata,
            "segment_count": len(segments),
            "segments": segments,
        }
        json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        markdown_path.write_text(
            paragraph_markdown(segments, args.paragraph_sentences), encoding="utf-8"
        )

    print(f"Segments: {json_path}")
    print(f"Cleaned transcript: {markdown_path}")


if __name__ == "__main__":
    main()
