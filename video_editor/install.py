"""Register the venv FFmpeg, the skill, and the MCP clients."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from video_editor.binutil import REPO

HOME = Path.home()
STATE = HOME / ".video-editor"


def _python() -> Path:
    return Path(sys.executable).resolve()


def _ffmpeg_dest() -> Path:
    scripts = _python().parent
    return scripts / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")


def install_ffmpeg() -> Path:
    import imageio_ffmpeg

    src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    dest = _ffmpeg_dest()
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def _copy_skill(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "skill" / "SKILL.md", dest / "SKILL.md")
    references = dest / "references"
    references.mkdir(exist_ok=True)
    shutil.copy2(REPO / "skill" / "references" / "edit-rules.md", references / "edit-rules.md")


def install_skills() -> list[Path]:
    name = "video-editor"
    places = [
        REPO / ".grok" / "skills" / name,
        REPO / ".claude" / "skills" / name,
        REPO / ".agents" / "skills" / name,
        REPO / ".opencode" / "skills" / name,
        HOME / ".grok" / "skills" / name,
        HOME / ".claude" / "skills" / name,
        HOME / ".agents" / "skills" / name,
        HOME / ".gemini" / "config" / "skills" / name,
        HOME / ".gemini" / "antigravity-cli" / "skills" / name,
        HOME / ".config" / "opencode" / "skills" / name,
        HOME / ".cursor" / "skills" / name,
    ]
    for place in places:
        _copy_skill(place)
    return places


def _server(ffmpeg: Path) -> dict:
    return {
        "type": "stdio",
        "command": str(_python()),
        "args": ["-m", "video_editor"],
        "env": {
            "VIDEO_EDITOR_FFMPEG": str(ffmpeg),
            "VIDEO_EDITOR_HOME": str(REPO),
        },
    }


def _backup(path: Path) -> None:
    if not path.is_file():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = STATE / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, folder / f"{path.name}.{stamp}")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def _merge_mcp_servers(path: Path, server: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    data = _read_json(path)
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    servers["video-editor"] = server
    data["mcpServers"] = servers
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _merge_opencode(path: Path, ffmpeg: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    data = _read_json(path)
    mcp = data.get("mcp")
    if not isinstance(mcp, dict):
        mcp = {}
    mcp["video-editor"] = {
        "type": "local",
        "command": [str(_python()), "-m", "video_editor"],
        "enabled": True,
        "environment": {
            "VIDEO_EDITOR_FFMPEG": str(ffmpeg),
            "VIDEO_EDITOR_HOME": str(REPO),
        },
    }
    data["mcp"] = mcp
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _merge_grok(path: Path, ffmpeg: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    begin = "# BEGIN video-editor\n"
    end = "# END video-editor\n"
    block = (
        f"{begin}"
        "[mcp_servers.video-editor]\n"
        f"command = {json.dumps(str(_python()))}\n"
        'args = ["-m", "video_editor"]\n'
        "startup_timeout_sec = 60\n"
        "tool_timeout_sec = 3600\n"
        "[mcp_servers.video-editor.env]\n"
        f"VIDEO_EDITOR_FFMPEG = {json.dumps(str(ffmpeg))}\n"
        f"VIDEO_EDITOR_HOME = {json.dumps(str(REPO))}\n"
        f"{end}"
    )
    if begin in text and end in text:
        pre, rest = text.split(begin, 1)
        _old, post = rest.split(end, 1)
        text = pre + block + post
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    path.write_text(text, encoding="utf-8")


def install_clients(ffmpeg: Path) -> list[str]:
    server = _server(ffmpeg)
    notes = []
    jobs = [
        ("Grok CLI", HOME / ".grok" / "config.toml", "grok"),
        ("Claude Code", HOME / ".claude.json", "mcp"),
        ("Agy", HOME / ".gemini" / "config" / "mcp_config.json", "mcp"),
        ("Freebuff", HOME / ".agents" / "mcp.json", "mcp"),
        ("Omnirush", HOME / ".config" / "omnirush" / "opencode.json", "opencode"),
        ("OpenCode", HOME / ".config" / "opencode" / "opencode.json", "opencode"),
        ("Claude project", REPO / ".mcp.json", "mcp"),
        ("Freebuff project", REPO / ".agents" / "mcp.json", "mcp"),
        ("Agy project", REPO / ".agents" / "mcp_config.json", "mcp"),
        ("Omnirush project", REPO / "opencode.json", "opencode"),
        ("Grok project", REPO / ".grok" / "config.toml", "grok"),
    ]
    for label, path, kind in jobs:
        try:
            if kind == "grok":
                _merge_grok(path, ffmpeg)
            elif kind == "opencode":
                _merge_opencode(path, ffmpeg)
            else:
                _merge_mcp_servers(path, server)
            notes.append(f"ok {label}: {path}")
        except Exception as exc:
            notes.append(f"skip {label}: {path} ({exc})")
    return notes


def write_home(ffmpeg: Path) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "home.txt").write_text(str(REPO) + "\n", encoding="utf-8")
    (STATE / "omnirush.txt").write_text(
        "Omnirush only starts MCP servers on its supported package list. "
        "The video-editor skill still loads. When the MCP tools are missing, "
        "run the CLI in home.txt: bin\\\\video-editor.cmd on Windows.\n",
        encoding="utf-8",
    )
    (STATE / "ffmpeg.txt").write_text(str(ffmpeg) + "\n", encoding="utf-8")


def main() -> None:
    ffmpeg = install_ffmpeg()
    skills = install_skills()
    notes = install_clients(ffmpeg)
    write_home(ffmpeg)
    print(f"python {sys.executable}")
    print(f"ffmpeg {ffmpeg}")
    print(f"skills {len(skills)}")
    for note in notes:
        print(note)


if __name__ == "__main__":
    main()
