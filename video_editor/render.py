"""Turn an edit document into one mp4."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from PIL import Image

from video_editor.binutil import REPO, local_file, output_file, pipe_raw, run_ffmpeg
from video_editor.errors import EditorError
from video_editor.graphics import iter_card, iter_lookbook, overlay_png, parse_color
from video_editor.probe import probe_path
from video_editor.schema import normalize_edit
from video_editor.score import make_score


def _grade(name: str) -> str:
    if name == "clean":
        return "eq=contrast=1.05:saturation=1.08:brightness=0.01,unsharp=5:5:0.8:5:5:0.0,vignette=PI/5,"
    if name == "night":
        return "eq=contrast=1.08:saturation=0.92:brightness=-0.03:gamma=0.95,vignette=PI/4,"
    return ""


def _encode_clip(src: Path, start: float, duration: float, width: int, height: int, fps: int, grade: str, dest: Path) -> None:
    info = probe_path(str(src))
    if not info["still"] and start + 0.05 > float(info["duration"]):
        raise EditorError(f"{src.name} is {info['duration']:.2f}s. start {start:.2f} is past the end.")
    frames = max(1, round(duration * fps))
    video_filter = (
        f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,{_grade(grade)}format=yuv420p"
    )
    run_ffmpeg(
        [
            "-i",
            str(src),
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-vf",
            video_filter,
            "-frames:v",
            str(frames),
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )


def _still(src: Path, when: float, dest: Path) -> Path:
    info = probe_path(str(src))
    if info["still"] or src.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        return src
    run_ffmpeg(
        ["-ss", f"{max(0.0, when):.3f}", "-i", str(src), "-frames:v", "1", str(dest)]
    )
    return dest


def _encode_segment(segment: dict, width: int, height: int, fps: int, dest: Path, work: Path, index: int) -> None:
    kind = segment["type"]
    if kind == "clip":
        _encode_clip(local_file(segment["src"]), segment["start"], segment["duration"], width, height, fps, segment["grade"], dest)
        return
    if kind == "card":
        pipe_raw(
            width,
            height,
            fps,
            iter_card(width, height, fps, segment["duration"], segment["background"], segment["lines"]),
            dest,
        )
        return
    if kind == "lookbook":
        photos = []
        titles = []
        captions = []
        background = parse_color(segment["background"])
        ink = parse_color(segment["ink"])
        for page_index, page in enumerate(segment["pages"]):
            src = local_file(page["src"])
            still = _still(src, float(page.get("time") or 0.4), work / f"still-{index}-{page_index}.jpg")
            image = Image.open(still).convert("RGB")
            crop = page.get("crop")
            if crop:
                w, h = image.size
                image = image.crop((int(w * float(crop[0])), int(h * float(crop[1])), int(w * float(crop[2])), int(h * float(crop[3]))))
            photos.append(image)
            titles.append(str(page.get("title") or ""))
            captions.append(str(page.get("caption") or ""))
        pipe_raw(
            width,
            height,
            fps,
            iter_lookbook(
                width,
                height,
                fps,
                segment["duration"],
                photos,
                float(segment["page_duration"]),
                float(segment["crossfade"]),
                background,
                ink,
                titles,
                captions,
            ),
            dest,
        )
        return
    _encode_collage(segment, width, height, fps, dest)


def _cell_filter(label: str, width: int, height: int, fps: int) -> str:
    return (
        f"{label}fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,format=yuv420p"
    )


def _encode_collage(segment: dict, width: int, height: int, fps: int, dest: Path) -> None:
    layout = segment["layout"]
    gap = int(segment["gap"])
    cells = segment["cells"]
    sources = [local_file(cell["src"]) for cell in cells]
    if layout == "2v":
        cell_w = (width - gap) // 2
        cell_w -= cell_w % 2
        gap = width - cell_w * 2
        positions = [(0, 0), (cell_w + gap, 0)]
        sizes = [(cell_w, height), (cell_w, height)]
    elif layout == "2h":
        cell_h = (height - gap) // 2
        cell_h -= cell_h % 2
        gap = height - cell_h * 2
        positions = [(0, 0), (0, cell_h + gap)]
        sizes = [(width, cell_h), (width, cell_h)]
    else:
        cell_w = (width - gap) // 2
        cell_h = (height - gap) // 2
        cell_w -= cell_w % 2
        cell_h -= cell_h % 2
        positions = [(0, 0), (width - cell_w, 0), (0, height - cell_h), (width - cell_w, height - cell_h)]
        sizes = [(cell_w, cell_h)] * 4
    color = segment["background"].replace("#", "0x")
    duration = segment["duration"]
    args: list[str] = []
    filters = [f"color=c={color}:s={width}x{height}:r={fps}:d={duration:.3f}[bg]"]
    last = "[bg]"
    for index, src in enumerate(sources):
        start = float(cells[index].get("start") or 0)
        args += ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src)]
        cw, ch = sizes[index]
        filters.append(f"[{index}:v]{_cell_filter('', cw, ch, fps)}[c{index}]")
        x, y = positions[index]
        out = "[v]" if index == len(sources) - 1 else f"[p{index}]"
        filters.append(f"{last}[c{index}]overlay={x}:{y}{out}")
        last = out
    run_ffmpeg(
        [
            *args,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[v]",
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-t",
            f"{duration:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )


def _concat(paths: list[Path], dest: Path, fps: int) -> None:
    if len(paths) == 1:
        shutil.copy(paths[0], dest)
        return
    args: list[str] = []
    for path in paths:
        args += ["-i", str(path)]
    graph = "".join(f"[{i}:v]" for i in range(len(paths))) + f"concat=n={len(paths)}:v=1:a=0[v]"
    run_ffmpeg(
        [
            *args,
            "-filter_complex",
            graph,
            "-map",
            "[v]",
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )


def _xfade(paths: list[Path], durations: list[float], transitions: list[dict], dest: Path, fps: int) -> None:
    args: list[str] = []
    for path in paths:
        args += ["-i", str(path)]
    parts = []
    last = "[0:v]"
    elapsed = durations[0]
    for index, transition in enumerate(transitions):
        out = "[v]" if index == len(transitions) - 1 else f"[x{index}]"
        offset = elapsed - transition["duration"]
        parts.append(
            f"{last}[{index + 1}:v]xfade=transition={transition['type']}:"
            f"duration={transition['duration']:.3f}:offset={offset:.3f}{out}"
        )
        elapsed = elapsed + durations[index + 1] - transition["duration"]
        last = out
    run_ffmpeg(
        [
            *args,
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[v]",
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )


def _assemble(paths: list[Path], durations: list[float], transitions: list[dict], dest: Path, fps: int, work: Path) -> float:
    groups: list[list[int]] = [[0]]
    group_duration = [durations[0]]
    fades: list[dict] = []
    for index, transition in enumerate(transitions):
        if transition["type"] == "cut" or transition["duration"] <= 0:
            groups[-1].append(index + 1)
            group_duration[-1] += durations[index + 1]
        else:
            fades.append(transition)
            groups.append([index + 1])
            group_duration.append(durations[index + 1])
    group_files = []
    for index, group in enumerate(groups):
        group_dest = work / f"group-{index}.mp4"
        _concat([paths[item] for item in group], group_dest, fps)
        group_files.append(group_dest)
    if len(group_files) == 1:
        shutil.copy(group_files[0], dest)
    else:
        _xfade(group_files, group_duration, fades, dest, fps)
    return sum(group_duration) - sum(item["duration"] for item in fades)


def _apply_overlays(video: Path, overlays: list[dict], dest: Path, width: int, height: int, fps: int, duration: float, work: Path) -> None:
    if not overlays:
        shutil.copy(video, dest)
        return
    args = ["-i", str(video)]
    filters = []
    last = "[0:v]"
    for index, overlay in enumerate(overlays):
        png = work / f"overlay-{index}.png"
        overlay_png(
            str(overlay.get("text") or ""),
            width,
            height,
            int(overlay.get("y") or int(height * 0.12)),
            int(overlay.get("size") or 32),
            str(overlay.get("color") or "#FFFFFF"),
            str(overlay.get("font") or "sans"),
            int(overlay.get("tracking") or 2),
            png,
        )
        args += ["-loop", "1", "-i", str(png)]
        start = float(overlay.get("start") or 0)
        end = float(overlay.get("end") or duration)
        out = "[v]" if index == len(overlays) - 1 else f"[o{index}]"
        filters.append(f"{last}[{index + 1}:v]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'{out}")
        last = out
    run_ffmpeg(
        [
            *args,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[v]",
            "-r",
            str(fps),
            "-t",
            f"{duration:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )


def _mux(video: Path, wav: Path, dest: Path, duration: float, fade: float) -> None:
    start = max(0.0, duration - fade)
    audio = (
        f"atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={start:.3f}:d={max(0.05, fade):.3f},"
        "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    )
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-i",
            str(wav),
            "-filter:a",
            audio,
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-t",
            f"{duration:.3f}",
            str(dest),
        ]
    )


def _safe_warnings(edit: dict) -> list[str]:
    if edit["height"] <= edit["width"]:
        return []
    top = edit["height"] * (250 / 1920)
    bottom = edit["height"] * (1520 / 1920)
    warnings = []
    for index, segment in enumerate(edit["segments"]):
        if segment["type"] != "card":
            continue
        for line in segment["lines"]:
            y = line.get("y")
            if y is None:
                continue
            if y < top or y > bottom:
                warnings.append(
                    f"Card {index} text at y={y} sits in the Reel caption band. Keep type between y={int(top)} and y={int(bottom)}."
                )
    return warnings


def render_edit(data: dict) -> dict:
    edit = normalize_edit(data)
    work = REPO / "build" / "jobs" / uuid.uuid4().hex[:10]
    work.mkdir(parents=True, exist_ok=True)
    width, height, fps = edit["width"], edit["height"], edit["fps"]
    segment_files = []
    for index, segment in enumerate(edit["segments"]):
        dest = work / f"seg-{index}.mp4"
        _encode_segment(segment, width, height, fps, dest, work, index)
        segment_files.append(dest)
    picture = work / "picture.mp4"
    duration = _assemble(
        segment_files,
        [item["duration"] for item in edit["segments"]],
        edit["transitions"],
        picture,
        fps,
        work,
    )
    with_type = work / "typed.mp4"
    _apply_overlays(picture, edit["overlays"], with_type, width, height, fps, duration, work)
    output = output_file(edit["output"])
    audio = edit["audio"]
    score_info = None
    if audio["style"] == "none":
        shutil.copy(with_type, output)
    else:
        wav = work / "score.wav"
        if audio["style"] == "file":
            shutil.copy(local_file(audio["src"]), wav)
            score_info = {"path": str(wav), "style": "file"}
        else:
            score_info = make_score(str(wav), audio["style"], duration, audio["bpm"])
        _mux(with_type, wav, output, duration, audio["fade_out"])
    probed = probe_path(str(output))
    if isinstance(score_info, dict):
        score_info.pop("path", None)
    shutil.rmtree(work, ignore_errors=True)
    return {
        "output": str(output),
        "duration": round(duration, 3),
        "probed_duration": probed["duration"],
        "width": width,
        "height": height,
        "fps": fps,
        "audio": score_info,
        "safe_zone_warnings": _safe_warnings(edit),
    }
