"""Questions the model asks before it cuts. This is the only copy."""

BRIEF = """
Ask in one message, then wait. Skip any item the user already answered.

1. Concept. What should this video say, and what should it feel like?
2. Use case. Where will it play: an Instagram Reel, a Story, TikTok, YouTube, a 16:9 commercial, a presentation, or something else? Include the length and the aspect ratio.
3. Background music. An original score (name the mood and the tempo) or a track the user has the rights to use. Audio from a reference video is not a choice.
4. Reference video. Is there a video the cut should follow? A file path is enough. If they name one, study that file before choosing shots.
5. Anything related. On-screen words, the call to action, colors, a logo, and anything that should stay out of the picture. Do not invent a URL, a handle, or a slogan.
""".strip()
