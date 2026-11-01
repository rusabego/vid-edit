"""FFmpeg from the project venv, never a system-wide install."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from video_editor.errors import EditorError

REPO = Path(__file__).resolve().parents[1]
NOWINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ffmpeg_exe() -> Path:
    env = os.environ.get("VIDEO_EDITOR_FFMPEG")
    if env:
        path = Path(env)
        if path.is_file():
            return path
    sibling = Path(sys.executable).resolve().parent / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if sibling.is_file():
        return sibling
    import imageio_ffmpeg

    bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if bundled.is_file():
        return bundled
    raise EditorError("FFmpeg is not in this venv. Run install.ps1, install.cmd, or install.sh.")


def run_ffmpeg(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None, check: bool = True) -> str:
    cmd = [str(ffmpeg_exe()), "-hide_banner", "-y", *args]
    try:
        proc = subprocess.run(
            cmd,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=NOWINDOW,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EditorError(f"FFmpeg timed out after {timeout}s") from exc
    text = (proc.stderr or b"").decode("utf-8", "replace")
    if check and proc.returncode != 0:
        tail = text[-2500:]
        raise EditorError(f"FFmpeg failed ({proc.returncode}):\n{tail}")
    return text


def pipe_raw(width: int, height: int, fps: int, frames, dest: Path) -> None:
    """Stream RGB frames into an h264 file. `frames` yields raw rgb24 bytes."""
    cmd = [
        str(ffmpeg_exe()),
        "-hide_banner",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "cfr",
        str(dest),
    ]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=NOWINDOW,
    )
    assert proc.stdin is not None
    try:
        for frame in frames:
            proc.stdin.write(frame)
    finally:
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        code = proc.wait()
    if code != 0:
        raise EditorError(f"FFmpeg frame pipe failed ({code}):\n{err[-2500:]}")


def local_file(path: str) -> Path:
    raw = str(path).strip()
    if "://" in raw or raw.lower().startswith("pipe:"):
        raise EditorError("Only a local file path is allowed.")
    found = Path(raw).expanduser().resolve()
    if not found.exists():
        raise EditorError(f"Not found: {found}")
    if not found.is_file():
        raise EditorError(f"Not a file: {found}")
    return found


def output_file(path: str) -> Path:
    raw = str(path).strip()
    if "://" in raw or raw.lower().startswith("pipe:"):
        raise EditorError("Only a local output path is allowed.")
    dest = Path(raw).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest
