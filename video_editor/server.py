"""MCP server. stdout is the protocol. Logs stay on stderr."""

from __future__ import annotations

import json
import os
import sys
from functools import wraps
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from video_editor import __version__
from video_editor.binutil import ffmpeg_exe
from video_editor.brief import BRIEF
from video_editor.errors import EditorError
from video_editor.frames import extract_frames as save_frames
from video_editor.graphics import font_status
from video_editor.probe import probe_path
from video_editor.reference import study_reference
from video_editor.render import render_edit as render_document
from video_editor.schema import RENDER_HELP
from video_editor.score import make_score

mcp = MCPServer("video-editor")


def _json(payload: dict) -> str:
    return json.dumps(payload, indent=2)


def _guard(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError:
            raise
        except EditorError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    return wrapped


@mcp.tool()
@_guard
def editor_status() -> str:
    """Report the venv Python, the venv FFmpeg, and the brief to ask before cutting."""
    binary = ffmpeg_exe()
    version = "unknown"
    try:
        import subprocess

        proc = subprocess.run(
            [str(binary), "-version"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        version = (proc.stdout or "").splitlines()[0]
    except OSError as exc:
        version = str(exc)
    return _json(
        {
            "version": __version__,
            "python": sys.executable,
            "venv": Path(sys.prefix).name == ".venv" or (Path(sys.prefix) / "pyvenv.cfg").is_file(),
            "ffmpeg": str(binary),
            "ffmpeg_version": version,
            "fonts": font_status(),
            "home": os.environ.get("VIDEO_EDITOR_HOME", ""),
            "brief": BRIEF,
        }
    )


@mcp.tool()
@_guard
def probe_media(path: str) -> str:
    """Probe a local video or still: duration, size, fps, and whether it has audio."""
    return _json(probe_path(path))


@mcp.tool()
@_guard
def study_reference_video(path: str, out_dir: str = "", max_frames: int = 12, scene_threshold: float = 0.3) -> str:
    """Study a reference video or a folder of them.

    Returns scene times, a contact sheet, and frame files. Read those images
    before matching the cut. Do not reuse the reference pictures, people, or audio.
    """
    return _json(study_reference(path, out_dir or None, max_frames=max_frames, scene_threshold=scene_threshold))


@mcp.tool()
@_guard
def extract_frames(path: str, times: list[float], out_dir: str) -> str:
    """Save JPEG stills at timestamps so you can look at a source or a finished video."""
    return _json({"frames": save_frames(path, times, out_dir)})


@mcp.tool()
@_guard
def make_original_score(output: str, style: str, duration: float, bpm: float = 120) -> str:
    """Write an original wav. style is boutique or cinematic. Do not use a reference video's audio."""
    return _json(make_score(output, style, duration, bpm))


@mcp.tool(description="Render one finished video.\n\n" + RENDER_HELP)
@_guard
def render_edit(edit_json: str, brief_confirmed: bool = False) -> str:
    """Render the edit document. brief_confirmed must be true only after the user answered the brief."""
    if not brief_confirmed:
        raise ToolError("Ask the brief and wait for the answer before rendering.\n\n" + BRIEF)
    data = json.loads(edit_json)
    return _json(render_document(data))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
