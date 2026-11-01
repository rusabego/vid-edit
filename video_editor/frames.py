"""Still frames the model can open and look at."""

from __future__ import annotations

from pathlib import Path

from video_editor.binutil import local_file, output_file, run_ffmpeg
from video_editor.errors import EditorError


def extract_frames(path: str, times: list[float], out_dir: str, *, width: int = 960) -> list[dict]:
    src = local_file(path)
    dest_dir = Path(out_dir).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not times:
        raise EditorError("Give at least one timestamp.")
    saved = []
    for index, time in enumerate(times):
        time = max(0.0, float(time))
        stamp = f"{time:.2f}".replace(".", "p")
        name = f"f_{index:02d}_{stamp}.jpg"
        dest = dest_dir / name
        output_file(str(dest))
        run_ffmpeg(
            [
                "-ss",
                f"{time:.3f}",
                "-i",
                str(src),
                "-frames:v",
                "1",
                "-vf",
                f"scale={width}:-2",
                str(dest),
            ]
        )
        saved.append({"time": round(time, 3), "path": str(dest)})
    return saved
