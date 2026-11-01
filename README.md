# video-editor

A local video editor for Claude Code, Agy, Freebuff, Omnirush, and Grok CLI. Python packages and FFmpeg stay in this repo's `.venv`. Nothing is installed into the system Python.

The model asks, in one message, before it cuts:

1. Concept
2. Use case (Reel, Story, TikTok, YouTube, 16:9 commercial, presentation, or another placement), plus length and aspect
3. Background music (an original score, or a track you have the rights to)
4. A reference video, if the cut should follow one
5. On-screen words and anything else that changes the picture

A reference is a video file. The `study_reference_video` tool saves a contact sheet and frames so the model can look at them. It does not copy that video's pictures, people, or audio.

## Install

One line from an empty folder. PowerShell:

```powershell
git clone git@github.com:rusabego/vid-edit.git; Set-Location vid-edit; powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

```powershell
git clone https://github.com/rusabego/vid-edit.git; Set-Location vid-edit; powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Git Bash:

```bash
git clone git@github.com:rusabego/vid-edit.git && cd vid-edit && bash install.sh
```

```bash
git clone https://github.com/rusabego/vid-edit.git && cd vid-edit && bash install.sh
```

Command Prompt:

```bat
git clone git@github.com:rusabego/vid-edit.git && cd vid-edit && install.cmd
```

```bat
git clone https://github.com/rusabego/vid-edit.git && cd vid-edit && install.cmd
```

The first line of each pair uses SSH. The second uses HTTPS.

From this folder, use one of:

- PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1`
- Windows command prompt: `install.cmd`
- Git Bash: `bash install.sh`

If this folder is already cloned, pull first so the script is current. PowerShell:

```powershell
git pull; powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Git Bash:

```bash
git pull && bash install.sh
```

Command Prompt:

```bat
git pull && install.cmd
```

If `py -3`, `python`, or `python3` is missing or older than Python 3.11, PowerShell, Git Bash, and Command Prompt download Python 3.13.7 and unpack it into `.python` in this folder. That copy stays with the project and does not ask for an administrator login. The script builds `.venv` from it. FFmpeg is copied into `.venv\Scripts` from the `imageio-ffmpeg` package. Git Bash calls the same PowerShell script when Python is missing, so the download happens there too.

The installer then registers the server and copies the `video-editor` skill. Restart the client after that.

| Client | MCP config | Skill |
| --- | --- | --- |
| Grok CLI | `%USERPROFILE%\.grok\config.toml` | `%USERPROFILE%\.grok\skills\video-editor` |
| Claude Code | `%USERPROFILE%\.claude.json` | `%USERPROFILE%\.claude\skills\video-editor` |
| Agy | `%USERPROFILE%\.gemini\config\mcp_config.json` | `%USERPROFILE%\.gemini\config\skills\video-editor` and `%USERPROFILE%\.agents\skills\video-editor` |
| Freebuff | `%USERPROFILE%\.agents\mcp.json` | `%USERPROFILE%\.agents\skills\video-editor` |
| Omnirush | `%USERPROFILE%\.config\omnirush\opencode.json` | `%USERPROFILE%\.config\opencode\skills\video-editor` and the Claude and agents skill folders |

Omnirush only starts MCP servers on its supported package list, so this local server can show up as blocked. The skill still loads. The model then runs `bin\video-editor.cmd` from the path in `%USERPROFILE%\.video-editor\home.txt`.

Project copies of the skill live in `.grok/skills`, `.claude/skills`, `.agents/skills`, and `.opencode/skills`.

## Tools

`editor_status`, `probe_media`, `study_reference_video`, `extract_frames`, `make_original_score`, `render_edit`.

`render_edit` refuses to render until `brief_confirmed` is true, which the model sets only after you answer the brief. The edit document is the tool description. `video-editor schema` prints it too.

## CLI

`bin\video-editor.cmd doctor`
`bin\video-editor.cmd brief`
`bin\video-editor.cmd study "C:\path\reference.mp4"`
`bin\video-editor.cmd render edit.json --brief-confirmed`
