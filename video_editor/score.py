"""Original scores. Drums are not ducked by the kick."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

from video_editor.errors import EditorError

SR = 48000
TWO_PI = 2.0 * math.pi


def _sin(freq: float, t: float) -> float:
    return math.sin(TWO_PI * freq * t)


def _tone(freq: float, length: float, decay: float) -> list[float]:
    count = int(length * SR)
    return [_sin(freq, i / SR) * math.exp(-(i / SR) * decay) for i in range(count)]


def _kick() -> list[float]:
    count = int(0.42 * SR)
    out = [0.0] * count
    phase = 0.0
    for i in range(count):
        u = i / SR
        freq = 48 + 130 * math.exp(-u * 32)
        phase += TWO_PI * freq / SR
        body = math.sin(phase) * math.exp(-u * 9.5)
        click = ((i * 17) ^ 91) % 1000 / 500.0 - 1.0
        click *= math.exp(-u * 90) * 0.35
        out[i] = (body + click) * 0.95
    return out


def _clap() -> list[float]:
    count = int(0.22 * SR)
    out = [0.0] * count
    seed = 17
    for i in range(count):
        u = i / SR
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        noise = (seed % 2000) / 1000.0 - 1.0
        burst = 0.0
        for delay, amp in ((0.0, 1.0), (0.012, 0.65), (0.024, 0.35)):
            if u >= delay:
                burst += amp * math.exp(-(u - delay) * 28)
        out[i] = noise * burst * 0.55
    return out


def _hat() -> list[float]:
    count = int(0.045 * SR)
    out = [0.0] * count
    seed = 3
    prev = 0.0
    for i in range(count):
        u = i / SR
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        noise = (seed % 2000) / 1000.0 - 1.0
        high = noise - prev
        prev = noise
        out[i] = high * math.exp(-u * 70) * 0.45
    return out


def _hit(buf: list[float], pos: int, sound: list[float]) -> None:
    end = min(len(buf), pos + len(sound))
    for i in range(end - pos):
        buf[pos + i] += sound[i]


def _write(path: Path, left: list[float], right: list[float]) -> float:
    peak = max(1e-9, max(max(abs(a), abs(b)) for a, b in zip(left, right)))
    scale = 0.89 / peak
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        frames = bytearray()
        for sample_l, sample_r in zip(left, right):
            frames += struct.pack(
                "<hh",
                int(math.tanh(sample_l * scale) * 32767),
                int(math.tanh(sample_r * scale) * 32767),
            )
        handle.writeframes(frames)
    return peak


def _smooth(t: float, start: float, end: float) -> float:
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    x = (t - start) / (end - start)
    return x * x * (3.0 - 2.0 * x)


def _boutique(duration: float, bpm: float, dest: Path) -> dict:
    count = int(duration * SR)
    drum_l = [0.0] * count
    drum_r = [0.0] * count
    music_l = [0.0] * count
    music_r = [0.0] * count
    duck = [1.0] * count
    beat = 60.0 / bpm
    tail = 3.0 if duration >= 8 else duration * 0.2
    kick, clap, hat = _kick(), _clap(), _hat()
    duck_curve = [math.exp(-(i / SR) * 12) for i in range(int(0.28 * SR))]

    def place(sound, times, gain, pan=0.0, bus="drum"):
        left = drum_l if bus == "drum" else music_l
        right = drum_r if bus == "drum" else music_r
        for when in times:
            if when >= duration:
                continue
            pos = int(round(when * SR))
            scaled = [sample * gain for sample in sound]
            _hit(left, pos, [sample * (1 - max(0.0, pan)) for sample in scaled])
            _hit(right, pos, [sample * (1 - max(0.0, -pan)) for sample in scaled])

    kicks = []
    cursor = 0.0
    while cursor < duration - tail - 1e-6:
        kicks.append(round(cursor, 5))
        cursor += beat
    if duration >= 8:
        kicks.extend([round(duration - tail, 5), round(duration - tail + beat * 2, 5)])
    kicks = [item for item in kicks if 0 <= item < duration - 0.05]
    claps = []
    cursor = beat
    while cursor < duration - tail:
        claps.append(round(cursor, 5))
        cursor += beat * 2
    hats = []
    cursor = 0.0
    while cursor < duration - tail:
        hats.append(round(cursor, 5))
        cursor += beat / 2
    place(kick, kicks, 0.72, 0.0)
    place(clap, claps, 0.34, 0.08)
    place(hat, hats, 0.16, -0.15)
    for when in kicks:
        pos = int(when * SR)
        for i, envelope in enumerate(duck_curve):
            if pos + i < count:
                duck[pos + i] *= 1 - 0.72 * envelope

    roots = [87.31, 65.41, 73.42, 58.27]
    bar = beat * 4
    offsets = (0.0, 0.1875, 0.375, 0.625, 0.75)
    bar_index = 0
    bar_t = 0.0
    while bar_t < duration - tail:
        root = roots[bar_index % 4]
        freqs = [root, root, root * 1.5, root, root * 1.25]
        for offset, freq in zip(offsets, freqs):
            place(_tone(freq, 0.20, 10), [bar_t + offset * bar], 0.22, 0.0, bus="music")
        bar_index += 1
        bar_t += bar

    # Plucks stay on the drum bus so the kick envelope does not mute them.
    plucks = [349.23, 440.0, 523.25, 392.0, 293.66, 349.23, 440.0, 392.0]
    when = bar * 2
    for freq in plucks:
        if when < duration - tail:
            place(_tone(freq, 0.35, 7), [when], 0.07, 0.25 if int(when) % 2 else -0.25)
        when += bar
    if duration >= 8:
        for extra, freq in (
            (duration - tail + 0.05, 523.25),
            (duration - tail + 1.0, 659.25),
            (duration - tail + 1.5, 783.99),
        ):
            if extra < duration:
                place(_tone(freq, 0.8, 3.2), [extra], 0.06, 0.0, bus="music")

    pad = [0.0] * count
    for i in range(count):
        t = i / SR
        root = roots[int(t / bar) % 4] if bar else roots[0]
        tone = (
            math.sin(TWO_PI * root * t)
            + 0.6 * math.sin(TWO_PI * root * 1.25 * t)
            + 0.45 * math.sin(TWO_PI * root * 1.5 * t)
        )
        fade = min(1.0, t / 0.4) * (1.0 if t < duration - 1.4 else max(0.0, 1 - (t - (duration - 1.4)) / 1.2))
        pad[i] = tone * 0.045 * fade * duck[i]

    left = [0.0] * count
    right = [0.0] * count
    fade_at = max(0.2, duration - 0.85)
    for i in range(count):
        t = i / SR
        fade = min(1.0, t / 0.12)
        if t > fade_at:
            fade *= max(0.0, 1 - (t - fade_at) / 0.85)
        left[i] = (drum_l[i] + music_l[i] * duck[i] + pad[i]) * fade
        right[i] = (drum_r[i] + music_r[i] * duck[i] + pad[i]) * fade
    peak = _write(dest, left, right)
    return {"path": str(dest), "style": "boutique", "bpm": bpm, "duration": duration, "peak": round(peak, 3)}


def _cinematic(duration: float, dest: Path) -> dict:
    count = int(duration * SR)
    rng = random.Random(7)
    left = [0.0] * count
    right = [0.0] * count
    delay_n = max(1, int(0.0129 * SR))
    delay = [0.0] * delay_n
    dpos = 0
    low = 0.0
    phase = 0.0

    def chord_a(t):
        return (
            0.34 * _sin(73.42, t)
            + 0.14 * _sin(73.60, t)
            + 0.18 * _sin(110.00, t)
            + 0.10 * _sin(146.83, t)
            + 0.07 * _sin(174.61, t)
        )

    def chord_b(t):
        return (
            0.30 * _sin(87.31, t)
            + 0.12 * _sin(87.55, t)
            + 0.16 * _sin(130.81, t)
            + 0.10 * _sin(174.61, t)
            + 0.08 * _sin(220.00, t)
        )

    for i in range(count):
        t = i / SR
        unit = t / duration
        blend = _smooth(unit, 0.415, 0.505)
        pad = chord_a(t) * (1 - blend) + chord_b(t) * blend
        breath = 0.86 + 0.14 * (0.5 + 0.5 * math.sin(TWO_PI * 0.45 * t))
        lift = 1.0 + 0.35 * _smooth(unit, 0.36, 0.47)
        fade_in = _smooth(unit, 0.005, 0.08)
        fade_out = 1.0 - _smooth(unit, 0.925, 0.995)
        pad *= breath * lift * fade_in * fade_out
        sub = _sin(36.71, t) * 0.22 * fade_in * fade_out
        sub += _sin(43.65, t) * 0.16 * blend * fade_out
        riser = 0.0
        if 0.355 <= unit <= 0.490:
            p = (unit - 0.355) / 0.135
            freq = 160.0 + 1100.0 * p * p
            phase += TWO_PI * freq / SR
            riser = math.sin(phase) * (p ** 2) * 0.16 * (1.0 - _smooth(unit, 0.462, 0.490))
        white = rng.uniform(-1.0, 1.0)
        low += 0.08 * (white - low)
        high = white - low
        air = low * 0.045 * fade_in * fade_out
        whoosh = high * (
            0.55 * math.exp(-((unit - 0.474) / 0.012) ** 2)
            + 0.28 * math.exp(-((unit - 0.715) / 0.014) ** 2)
        )
        impact = 0.0
        if unit >= 0.470:
            impact += math.sin(TWO_PI * 52.0 * t) * math.exp(-(unit - 0.470) * duration * 0.8) * 0.45
        if unit >= 0.715:
            impact += math.sin(TWO_PI * 65.0 * t) * math.exp(-(unit - 0.715) * duration * 0.7) * 0.18
        chime = 0.0
        if unit >= 0.750:
            decay = math.exp(-(unit - 0.750) * duration * 0.42)
            chime = (_sin(880.0, t) * 0.55 + _sin(1318.5, t) * 0.30) * decay * 0.09
        mono = pad + sub + riser + air + impact + chime
        delayed = delay[dpos]
        delay[dpos] = mono
        dpos = (dpos + 1) % delay_n
        left[i] = mono * 0.82 + delayed * 0.18 + whoosh * (0.75 if unit < 0.6 else 0.35)
        right[i] = delayed * 0.82 + mono * 0.18 + whoosh * (0.35 if unit < 0.6 else 0.75)
    peak = _write(dest, left, right)
    return {"path": str(dest), "style": "cinematic", "duration": duration, "peak": round(peak, 3)}


def make_score(output: str, style: str, duration: float, bpm: float = 120) -> dict:
    if duration <= 0 or duration > 180:
        raise EditorError("Score duration must be between 0 and 180 seconds.")
    style = style.lower().strip()
    dest = Path(output).expanduser().resolve()
    if style == "boutique":
        if bpm < 60 or bpm > 180:
            raise EditorError("bpm must be between 60 and 180.")
        return _boutique(duration, bpm, dest)
    if style == "cinematic":
        return _cinematic(duration, dest)
    raise EditorError("style must be boutique or cinematic.")
