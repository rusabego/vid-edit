"""Render a tiny edit and check that the skill still asks the brief."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from video_editor.binutil import ffmpeg_exe, run_ffmpeg
from video_editor.brief import BRIEF
from video_editor.probe import probe_path
from video_editor.reference import study_reference
from video_editor.render import render_edit

BUILD = ROOT / "build" / "smoke"


def main() -> None:
    skill = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    for line in BRIEF.splitlines():
        if line[:2] in {"1.", "2.", "3.", "4.", "5."}:
            if line not in skill:
                raise SystemExit(f"skill is missing brief line: {line}")
    BUILD.mkdir(parents=True, exist_ok=True)
    source = BUILD / "src.mp4"
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=30:duration=2",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ]
    )
    print("ffmpeg", ffmpeg_exe())
    studied = study_reference(str(source), str(BUILD / "ref"), max_frames=4)
    if not Path(studied["contact_sheet"]).is_file():
        raise SystemExit("contact sheet missing")
    edit = {
        "output": str(BUILD / "out.mp4"),
        "width": 640,
        "height": 360,
        "fps": 30,
        "segments": [
            {"type": "clip", "src": str(source), "start": 0.1, "duration": 1.0, "grade": "clean"},
            {
                "type": "card",
                "duration": 1.0,
                "background": "#102018",
                "lines": [{"text": "HELLO", "start": 0.05, "size": 72, "y": 140, "font": "display", "color": "#F4F1E8", "tracking": 6}],
            },
        ],
        "transitions": [{"type": "fadeblack", "duration": 0.15}],
        "audio": {"style": "boutique", "bpm": 120, "fade_out": 0.3},
    }
    result = render_edit(edit)
    print(json.dumps(result, indent=2))
    info = probe_path(result["output"])
    if not info["has_audio"]:
        raise SystemExit("output has no audio")
    if abs(float(info["duration"]) - float(result["duration"])) > 0.15:
        raise SystemExit(f"duration drifted: {info['duration']} vs {result['duration']}")
    print("smoke ok")


if __name__ == "__main__":
    main()
