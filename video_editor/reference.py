"""Study a reference video: pacing, frames, and a contact sheet."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from video_editor.binutil import REPO, local_file, run_ffmpeg
from video_editor.errors import EditorError
from video_editor.frames import extract_frames
from video_editor.probe import probe_path

_PTS = re.compile(r"pts_time:([0-9.]+)")
_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def _palette(path: Path, count: int = 5) -> list[str]:
    image = Image.open(path).convert("RGB").resize((48, 48))
    quant = image.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    colors = quant.getcolors() or []
    palette = quant.getpalette() or []
    picked = []
    for _n, index in sorted(colors, reverse=True):
        rgb = palette[index * 3 : index * 3 + 3]
        if len(rgb) < 3:
            continue
        picked.append(f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
    return picked


def _scene_times(path: Path, threshold: float, limit: float) -> list[float]:
    text = ""
    try:
        text = run_ffmpeg(
            [
                "-i",
                str(path),
                "-t",
                f"{limit:.3f}",
                "-vf",
                f"select='gt(scene,{threshold:.3f})',showinfo",
                "-an",
                "-f",
                "null",
                "-",
            ],
            timeout=180,
            check=False,
        )
    except EditorError as exc:
        # showinfo writes to stderr and ffmpeg may exit 0. A real failure still
        # raises. Scene detection is optional if the file is too odd to scan.
        text = str(exc)
    times = []
    for match in _PTS.finditer(text):
        times.append(float(match.group(1)))
    return times


def _contact(frames: list[dict], dest: Path) -> None:
    thumbs = []
    for item in frames:
        image = Image.open(item["path"]).convert("RGB")
        image.thumbnail((320, 180))
        thumbs.append(image)
    if not thumbs:
        return
    columns = 4
    rows = (len(thumbs) + columns - 1) // columns
    cell_w = max(thumb.width for thumb in thumbs)
    cell_h = max(thumb.height for thumb in thumbs) + 22
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (16, 16, 16))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, thumb in enumerate(thumbs):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        sheet.paste(thumb, (x, y))
        draw.text((x + 6, y + thumb.height + 2), f"{frames[index]['time']:.2f}s", fill=(240, 240, 240), font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, quality=85)


def study_file(path: str, out_dir: str | None, *, max_frames: int = 12, scene_threshold: float = 0.3) -> dict:
    src = local_file(path)
    info = probe_path(str(src))
    duration = float(info["duration"] or 0.0)
    limit = duration if duration > 0 else 0.0
    if limit <= 0:
        raise EditorError(f"{src} has no duration to study.")
    limit = min(limit, 180.0)
    max_frames = max(4, min(int(max_frames), 24))
    scenes = _scene_times(src, scene_threshold, limit)
    step = limit / max_frames
    sampled = [round(step * i, 3) for i in range(max_frames)]
    times = [0.0]
    for value in scenes + sampled:
        if value < 0 or value >= limit:
            continue
        if all(abs(value - kept) > 0.08 for kept in times):
            times.append(round(value, 3))
    times = sorted(times)[:max_frames]
    folder = Path(out_dir).expanduser().resolve() if out_dir else REPO / "build" / "reference" / src.stem
    folder.mkdir(parents=True, exist_ok=True)
    frames = extract_frames(str(src), times, str(folder))
    sheet = folder / "contact.jpg"
    _contact(frames, sheet)
    shot_count = max(1, len(scenes) + 1)
    average = round(limit / shot_count, 2)
    notes = (
        f"{src.name} is {info['width']}x{info['height']} at {info['fps']} fps, {limit:.2f}s. "
        f"About {shot_count} shots, average {average:.2f}s. "
        + ("Scene changes are sparse, so this reads as one moving shot. " if len(scenes) < 2 else "Cuts are visible as scene changes. ")
        + "Open the contact sheet and the frame files before you match the cut. Do not reuse this video's pictures, people, or audio."
    )
    return {
        "probe": info,
        "scene_times": [round(t, 3) for t in scenes],
        "shot_count": shot_count,
        "average_shot_seconds": average,
        "frames": frames,
        "contact_sheet": str(sheet),
        "palette": _palette(Path(frames[len(frames) // 2]["path"])) if frames else [],
        "notes": notes,
    }


def study_reference(path: str, out_dir: str | None = None, *, max_frames: int = 12, scene_threshold: float = 0.3) -> dict:
    raw = str(path).strip()
    if "://" in raw:
        raise EditorError("Only a local reference video is allowed.")
    candidate = Path(raw).expanduser().resolve()
    if candidate.is_dir():
        videos = [item for item in sorted(candidate.iterdir()) if item.suffix.lower() in _VIDEO_EXT]
        if not videos:
            raise EditorError(f"No video files in {candidate}")
        items = []
        for video in videos[:8]:
            folder = str(Path(out_dir) / video.stem) if out_dir else None
            items.append(study_file(str(video), folder, max_frames=max_frames, scene_threshold=scene_threshold))
        return {"count": len(items), "items": items}
    return study_file(str(candidate), out_dir, max_frames=max_frames, scene_threshold=scene_threshold)
