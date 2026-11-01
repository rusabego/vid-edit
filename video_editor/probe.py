"""Read duration, size, and audio from a local file with the venv FFmpeg."""

from __future__ import annotations

import re
import subprocess

from video_editor.binutil import NOWINDOW, ffmpeg_exe, local_file
from video_editor.errors import EditorError

_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_SIZE = re.compile(r"(\d{2,5})x(\d{2,5})")
_FPS = re.compile(r"(\d+(?:\.\d+)?)\s*fps")
_TBR = re.compile(r"(\d+(?:\.\d+)?)\s*tbr")


def probe_path(path: str) -> dict:
    src = local_file(path)
    proc = subprocess.run(
        [str(ffmpeg_exe()), "-hide_banner", "-i", str(src)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=NOWINDOW,
        check=False,
    )
    text = (proc.stderr or b"").decode("utf-8", "replace")
    if "Invalid data found" in text or "No such file" in text:
        raise EditorError(text[-1500:])
    info = {
        "path": str(src),
        "duration": None,
        "width": None,
        "height": None,
        "fps": None,
        "video_codec": None,
        "has_audio": False,
        "audio_codec": None,
        "still": False,
    }
    for line in text.splitlines():
        if "Duration:" in line and "N/A" not in line.split("Duration:", 1)[-1][:12]:
            match = _DURATION.search(line)
            if match:
                hours, minutes, seconds = match.groups()
                info["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        if "Video:" in line:
            info["video_codec"] = line.split("Video:", 1)[1].split(",", 1)[0].strip()
            size = _SIZE.search(line)
            if size:
                info["width"], info["height"] = int(size.group(1)), int(size.group(2))
            fps = _FPS.search(line) or _TBR.search(line)
            if fps:
                info["fps"] = float(fps.group(1))
        if "Audio:" in line:
            info["has_audio"] = True
            info["audio_codec"] = line.split("Audio:", 1)[1].split(",", 1)[0].strip()
    if info["width"] is None:
        raise EditorError(f"No video stream in {src}\n{text[-800:]}")
    if info["duration"] is None:
        info["still"] = True
        info["duration"] = 0.0
    return info
