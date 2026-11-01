"""Command line for clients that cannot start the MCP server."""

from __future__ import annotations

import argparse
import json
import sys

from video_editor.brief import BRIEF
from video_editor.errors import EditorError
from video_editor.frames import extract_frames
from video_editor.probe import probe_path
from video_editor.reference import study_reference
from video_editor.render import render_edit
from video_editor.schema import RENDER_HELP
from video_editor.score import make_score
from video_editor.server import editor_status


def _print(payload) -> None:
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="video-editor", description="Local video editor.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Show Python, FFmpeg, and the brief.")
    sub.add_parser("brief", help="Print the questions to ask before a cut.")

    probe = sub.add_parser("probe", help="Probe a local file.")
    probe.add_argument("path")

    study = sub.add_parser("study", help="Study a reference video.")
    study.add_argument("path")
    study.add_argument("--out")
    study.add_argument("--frames", type=int, default=12)

    frames = sub.add_parser("frames", help="Extract stills at timestamps.")
    frames.add_argument("path")
    frames.add_argument("--at", required=True, help="Comma-separated seconds.")
    frames.add_argument("--out", required=True)

    score = sub.add_parser("score", help="Write an original wav.")
    score.add_argument("--style", required=True, choices=["boutique", "cinematic"])
    score.add_argument("--duration", type=float, required=True)
    score.add_argument("--bpm", type=float, default=120)
    score.add_argument("--out", required=True)

    render = sub.add_parser("render", help="Render an edit JSON file.")
    render.add_argument("edit")
    render.add_argument("--brief-confirmed", action="store_true")

    schema = sub.add_parser("schema", help="Print the edit document.")
    schema.set_defaults(command="schema")

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            _print(editor_status())
        elif args.command == "brief":
            print(BRIEF)
        elif args.command == "probe":
            _print(probe_path(args.path))
        elif args.command == "study":
            _print(study_reference(args.path, args.out, max_frames=args.frames))
        elif args.command == "frames":
            times = [float(item) for item in args.at.split(",") if item.strip()]
            _print({"frames": extract_frames(args.path, times, args.out)})
        elif args.command == "score":
            _print(make_score(args.out, args.style, args.duration, args.bpm))
        elif args.command == "schema":
            print(RENDER_HELP)
        elif args.command == "render":
            if not args.brief_confirmed:
                print(BRIEF, file=sys.stderr)
                print("\nPass --brief-confirmed after the user has answered.", file=sys.stderr)
                return 2
            data = json.loads(open(args.edit, encoding="utf-8").read())
            _print(render_edit(data))
    except EditorError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
