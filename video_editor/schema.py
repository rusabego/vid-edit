"""The edit document. The tool description and the CLI both use this text."""

from __future__ import annotations

from video_editor.errors import EditorError

RENDER_HELP = """
edit_json is one JSON object:

{
  "output": "C:/path/out.mp4",
  "aspect": "9:16",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "segments": [
    {"type": "clip", "src": "a.mp4", "start": 0.4, "duration": 2.0, "grade": "clean"},
    {"type": "card", "duration": 2.0, "background": "#111111",
     "lines": [{"text": "THE NAME", "start": 0.2, "size": 72, "y": 800, "font": "display", "color": "#FFFFFF", "tracking": 8}]},
    {"type": "lookbook", "duration": 4.0, "page_duration": 1.0, "crossfade": 0.18,
     "background": "#E2EADC", "ink": "#1C3A2E",
     "pages": [{"src": "still.jpg", "time": 0.4, "crop": [0, 0, 1, 1], "title": "THE COLLECTION", "caption": ""}]},
    {"type": "collage", "duration": 2.0, "layout": "2v", "gap": 16, "background": "#000000",
     "cells": [{"src": "a.mp4", "start": 0.2}, {"src": "b.mp4", "start": 1.0}]}
  ],
  "transitions": [{"type": "fadeblack", "duration": 0.2}, {"type": "cut"}, {"type": "fadewhite", "duration": 0.12}],
  "overlays": [{"text": "BRAND", "start": 0.4, "end": 2.0, "y": 280, "size": 28, "font": "sans", "color": "#FFFFFF"}],
  "audio": {"style": "boutique", "bpm": 120, "fade_out": 0.85}
}

aspect may be 16:9, 9:16, 1:1, or 4:5. width and height override it. grade is clean, night, or none.
transitions sit between segments. type is cut, fade, fadeblack, fadewhite, or wipeleft.
A cut has duration 0. Keep fadewhite at or under 0.3 seconds.
audio.style is boutique, cinematic, or file. A file needs "src". Omit audio for a silent picture.
Output length is the sum of segment durations minus the sum of transition durations.
brief_confirmed must be true only after the user answered the brief.
""".strip()

_ASPECTS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}
_GRADES = {"clean", "night", "none"}
_TRANSITIONS = {"cut", "fade", "fadeblack", "fadewhite", "wipeleft"}


def _number(value, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EditorError(f"{name} must be a number.") from exc


def _even(value: int) -> int:
    value = int(value)
    return value if value % 2 == 0 else value - 1


def normalize_edit(data: dict) -> dict:
    if not isinstance(data, dict):
        raise EditorError("The edit document must be a JSON object.")
    if not data.get("output"):
        raise EditorError("output is required.")
    aspect = str(data.get("aspect") or "16:9")
    if aspect not in _ASPECTS:
        raise EditorError("aspect must be 16:9, 9:16, 1:1, or 4:5.")
    width, height = _ASPECTS[aspect]
    if data.get("width"):
        width = int(_number(data["width"], "width"))
    if data.get("height"):
        height = int(_number(data["height"], "height"))
    width, height = _even(width), _even(height)
    if width < 160 or height < 160:
        raise EditorError("width and height must be at least 160.")
    fps = int(_number(data.get("fps") or 30, "fps"))
    if fps not in {24, 25, 30, 50, 60}:
        raise EditorError("fps must be 24, 25, 30, 50, or 60.")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise EditorError("segments must be a non-empty list.")
    clean_segments = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise EditorError(f"segment {index} must be an object.")
        kind = str(segment.get("type") or "")
        duration = _number(segment.get("duration"), f"segment {index} duration")
        if duration <= 0:
            raise EditorError(f"segment {index} duration must be greater than 0.")
        item = {"type": kind, "duration": duration}
        if kind == "clip":
            if not segment.get("src"):
                raise EditorError(f"segment {index} needs src.")
            grade = str(segment.get("grade") or "clean")
            if grade not in _GRADES:
                raise EditorError("grade must be clean, night, or none.")
            item.update(src=segment["src"], start=max(0.0, _number(segment.get("start") or 0, "start")), grade=grade)
        elif kind == "card":
            item.update(
                background=str(segment.get("background") or "#111111"),
                lines=segment.get("lines") or [],
            )
            if not isinstance(item["lines"], list):
                raise EditorError(f"segment {index} lines must be a list.")
        elif kind == "lookbook":
            pages = segment.get("pages") or []
            if not isinstance(pages, list) or not pages:
                raise EditorError(f"segment {index} needs pages.")
            item.update(
                background=str(segment.get("background") or "#E2EADC"),
                ink=str(segment.get("ink") or "#1C3A2E"),
                page_duration=float(segment.get("page_duration") or 1.0),
                crossfade=float(segment.get("crossfade") or 0.18),
                pages=pages,
            )
        elif kind == "collage":
            cells = segment.get("cells") or []
            layout = str(segment.get("layout") or "2v")
            if layout not in {"2v", "2h", "4"}:
                raise EditorError("collage layout must be 2v, 2h, or 4.")
            need = 4 if layout == "4" else 2
            if len(cells) < need:
                raise EditorError(f"collage {layout} needs {need} cells.")
            item.update(
                layout=layout,
                gap=int(segment.get("gap") or 16),
                background=str(segment.get("background") or "#000000"),
                cells=cells[:need],
            )
        else:
            raise EditorError("segment type must be clip, card, lookbook, or collage.")
        clean_segments.append(item)
    transitions = data.get("transitions") or []
    if not isinstance(transitions, list):
        raise EditorError("transitions must be a list.")
    needed = len(clean_segments) - 1
    clean_transitions = []
    for index in range(needed):
        raw = transitions[index] if index < len(transitions) else {"type": "cut"}
        if not isinstance(raw, dict):
            raise EditorError(f"transition {index} must be an object.")
        kind = str(raw.get("type") or "cut")
        if kind not in _TRANSITIONS:
            raise EditorError("transition type must be cut, fade, fadeblack, fadewhite, or wipeleft.")
        duration = 0.0 if kind == "cut" else float(raw.get("duration") or 0.2)
        if duration < 0:
            raise EditorError("transition duration cannot be negative.")
        if kind != "cut" and duration >= clean_segments[index]["duration"]:
            raise EditorError(f"transition {index} is longer than the segment before it.")
        clean_transitions.append({"type": kind, "duration": duration})
    audio = data.get("audio") or {"style": "none"}
    if not isinstance(audio, dict):
        raise EditorError("audio must be an object.")
    style = str(audio.get("style") or "none")
    if style not in {"none", "boutique", "cinematic", "file"}:
        raise EditorError("audio.style must be none, boutique, cinematic, or file.")
    if style == "file" and not audio.get("src"):
        raise EditorError("audio.style file needs src.")
    overlays = data.get("overlays") or []
    if not isinstance(overlays, list):
        raise EditorError("overlays must be a list.")
    total = sum(item["duration"] for item in clean_segments) - sum(item["duration"] for item in clean_transitions)
    if total <= 0:
        raise EditorError("The edit duration is zero after transitions.")
    if total > 180 and not data.get("allow_long"):
        raise EditorError("This edit is longer than 180 seconds. Set allow_long true to render it.")
    return {
        "output": str(data["output"]),
        "width": width,
        "height": height,
        "fps": fps,
        "segments": clean_segments,
        "transitions": clean_transitions,
        "audio": {
            "style": style,
            "bpm": float(audio.get("bpm") or 120),
            "src": audio.get("src"),
            "fade_out": float(audio.get("fade_out") or 0.85),
        },
        "overlays": overlays,
        "duration": total,
    }
