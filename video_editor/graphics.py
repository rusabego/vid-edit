"""Titles and lookbook pages drawn in code, so the words are exact."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from video_editor.binutil import REPO
from video_editor.errors import EditorError

_DISPLAY = (
    REPO / "fonts" / "LibreBaskerville-Regular.ttf",
    Path(r"C:\Windows\Fonts\palab.ttf"),
    Path(r"C:\Windows\Fonts\georgia.ttf"),
    Path(r"C:\Windows\Fonts\times.ttf"),
)
_SANS = (
    REPO / "fonts" / "DMSans-Regular.ttf",
    Path(r"C:\Windows\Fonts\segoeuil.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\calibri.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
)


def parse_color(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise EditorError(f"Color must be #RRGGBB, got {value!r}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def load_font(role: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    choices = _DISPLAY if role == "display" else _SANS
    for path in choices:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def tracked(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill, tracking: int, canvas_w: int, x=None) -> None:
    widths = []
    for char in text:
        box = font.getbbox(char)
        widths.append(box[2] - box[0])
    total = sum(widths) + tracking * max(0, len(text) - 1)
    cursor = (canvas_w - total) / 2 if x is None else x
    for char, width in zip(text, widths):
        draw.text((cursor, y), char, font=font, fill=fill)
        cursor += width + tracking


def cover(image: Image.Image, width: int, height: int, box: list[float] | None) -> Image.Image:
    if box:
        src_w, src_h = image.size
        image = image.crop(
            (
                int(src_w * box[0]),
                int(src_h * box[1]),
                int(src_w * box[2]),
                int(src_h * box[3]),
            )
        )
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    resized = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def iter_card(width: int, height: int, fps: int, duration: float, background: str, lines: list[dict]):
    count = max(1, round(duration * fps))
    bg = parse_color(background)
    prepared = []
    auto_y = int(height * 0.40)
    for line in lines:
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        size = int(line.get("size") or max(24, height // 18))
        font = load_font(line.get("font") or "display", size)
        y = line.get("y")
        if y is None:
            y = auto_y
            auto_y += size + int(height * 0.03)
        fill = parse_color(line.get("color") or "#FFFFFF") + (255,)
        tracked(draw, str(line.get("text") or ""), font, int(y), fill, int(line.get("tracking") or 0), width)
        prepared.append((float(line.get("start") or 0), float(line.get("fade") or 0.25), layer))
    for index in range(count):
        t = index / fps
        frame = Image.new("RGB", (width, height), bg)
        for start, fade, layer in prepared:
            if t < start:
                alpha = 0.0
            elif fade <= 0 or t >= start + fade:
                alpha = 1.0
            else:
                alpha = (t - start) / fade
            if alpha <= 0:
                continue
            if alpha >= 0.999:
                frame.paste(layer, (0, 0), layer)
            else:
                red, green, blue, band = layer.split()
                band = band.point(lambda p, alpha=alpha: int(p * alpha))
                faded = Image.merge("RGBA", (red, green, blue, band))
                frame.paste(faded, (0, 0), faded)
        yield frame.tobytes()


def _page(width: int, height: int, photo: Image.Image, title: str, caption: str, index: int, total: int, background, ink) -> Image.Image:
    canvas = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(canvas)
    muted = tuple(min(255, channel + 70) for channel in ink)
    kicker_size = max(12, int(height * 0.018))
    title_size = max(18, int(height * 0.036))
    caption_size = max(12, int(height * 0.018))
    kicker = load_font("sans", kicker_size)
    title_font = load_font("display", title_size)
    caption_font = load_font("sans", caption_size)
    kicker_y = int(height * 0.055)
    title_y = kicker_y + kicker_size + int(height * 0.012)
    frame_top = title_y + title_size + int(height * 0.02)
    frame_h = int(height * 0.78) - frame_top
    frame_w = int(width * 0.84)
    fx = (width - frame_w) // 2
    fy = frame_top
    draw.rounded_rectangle((fx + 8, fy + 10, fx + frame_w + 8, fy + frame_h + 10), radius=18, fill=(0, 0, 0))
    cream = (255, 252, 248)
    draw.rounded_rectangle((fx, fy, fx + frame_w, fy + frame_h), radius=18, fill=cream)
    pad = max(8, int(width * 0.012))
    inner_w, inner_h = frame_w - pad * 2, frame_h - pad * 2
    shot = cover(photo, inner_w, inner_h, None)
    mask = Image.new("L", (inner_w, inner_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, inner_h), radius=12, fill=255)
    canvas.paste(shot, (fx + pad, fy + pad), mask)
    tracked(draw, "LOOKBOOK", kicker, kicker_y, muted, 6, width)
    tracked(draw, title, title_font, title_y, ink, 2, width)
    caption_y = fy + frame_h + int(height * 0.016)
    if caption:
        tracked(draw, caption, caption_font, caption_y, ink, 2, width)
    widths = [max(16, width // 40) if dot == index else max(6, width // 90) for dot in range(total)]
    gap = max(8, width // 80)
    total_w = sum(widths) + (total - 1) * gap
    x = (width - total_w) / 2
    y = caption_y + int(caption_size * 1.8)
    for dot, dot_w in enumerate(widths):
        color = ink if dot == index else muted
        draw.rounded_rectangle((x, y, x + dot_w, y + max(6, height // 160)), radius=4, fill=color)
        x += dot_w + gap
    return canvas


def iter_lookbook(width, height, fps, duration, pages: list[Image.Image], page_duration: float, crossfade: float, background, ink, titles, captions):
    rendered = [
        _page(width, height, photo, titles[i], captions[i], i, len(pages), background, ink)
        for i, photo in enumerate(pages)
    ]
    hold = page_duration if page_duration > 0 else duration / max(1, len(rendered))
    count = max(1, round(duration * fps))
    for index in range(count):
        t = index / fps
        if len(rendered) == 1 or t >= hold * (len(rendered) - 1):
            frame = rendered[-1]
        else:
            page = min(int(t / hold), len(rendered) - 2)
            frac = t / hold - page
            start = 1 - min(0.9, crossfade / hold if hold else 0)
            if frac > start:
                alpha = (frac - start) / (1 - start)
                frame = Image.blend(rendered[page], rendered[page + 1], max(0.0, min(1.0, alpha)))
            else:
                frame = rendered[page]
        yield frame.convert("RGB").tobytes()


def overlay_png(text: str, width: int, height: int, y: int, size: int, color: str, font: str, tracking: int, dest: Path) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    tracked(draw, text, load_font(font, size), y, parse_color(color) + (255,), tracking, width)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest)


def font_status() -> dict:
    display = next((str(path) for path in _DISPLAY if path.is_file()), None)
    sans = next((str(path) for path in _SANS if path.is_file()), None)
    return {"display": display, "sans": sans, "default_bitmap": display is None or sans is None, "os": os.name}
