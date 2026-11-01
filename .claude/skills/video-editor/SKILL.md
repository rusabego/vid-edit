---
name: video-editor
description: >
  Edit local footage into a finished video. Before cutting, ask the concept,
  the use case (Reel, Story, TikTok, YouTube, commercial, presentation, or
  another placement), the background music, a reference video, and anything
  related that is still missing. Then study the reference video, cut, grade,
  title, and render with the video-editor tools. Use when the user wants to
  edit, cut, merge, or grade video, match a reference video, make a commercial,
  reel, or lookbook, or runs /video-editor.
argument-hint: footage, reference video, and where it will play
compatibility: >
  Requires the video-editor MCP tools, or the video-editor CLI from the
  project venv. install.ps1, install.cmd, and install.sh put Python packages
  and FFmpeg inside that venv.
---

# Video editor

## Ask first

Do not probe, study, or render until the concept, the use case, and the music choice are known. If any item below is missing, ask it in one message and wait. Skip an item the user already answered.

1. Concept. What should this video say, and what should it feel like?
2. Use case. Where will it play: an Instagram Reel, a Story, TikTok, YouTube, a 16:9 commercial, a presentation, or something else? Include the length and the aspect ratio.
3. Background music. An original score (name the mood and the tempo) or a track the user has the rights to use. Audio from a reference video is not a choice.
4. Reference video. Is there a video the cut should follow? A file path is enough. If they name one, study that file before choosing shots.
5. Anything related. On-screen words, the call to action, colors, a logo, and anything that should stay out of the picture. Do not invent a URL, a handle, or a slogan.

A concept can come from a reference they told you to follow. Still ask the use case and the music when those are missing.

Pass `brief_confirmed` true to `render_edit` only after they answer. The same questions are printed by `editor_status` and by `video-editor brief`.

## Reference video

When they name a reference video, call `study_reference_video` on that file, or on the folder if they gave several. Then open the contact sheet and the frame files it returns and look at them.

Match shot length, transition, framing, type, and color. Leave the reference's pictures, people, music, and on-screen words behind. Read `references/edit-rules.md` before the first render.

## Tools

Use the MCP tools when they are in the catalog:

- `editor_status` shows the venv Python, the venv FFmpeg, and the brief.
- `probe_media` reads duration, size, fps, and audio.
- `study_reference_video` studies a reference.
- `extract_frames` saves stills. Use it again on the finished file.
- `make_original_score` writes a boutique or cinematic wav.
- `render_edit` takes `edit_json` and `brief_confirmed`. The tool description is the edit document.

Reel and Story default to 1080x1920. YouTube and a 16:9 commercial default to 1920x1080. A square post is 1080x1080.

## If the MCP tools are missing

Omnirush blocks MCP servers that are not on its supported list. The skill still loads there. Read `%USERPROFILE%\.video-editor\home.txt` and run `<that folder>\bin\video-editor.cmd`. The commands are `brief`, `doctor`, `probe`, `study`, `frames`, `score`, and `render --brief-confirmed`.

## Check the picture

After the render, `extract_frames` across the output and look at every still before you say the video is done. If a safe-zone warning comes back, move the type and render again.
