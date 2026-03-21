#!/usr/bin/env python3
"""Scene manager — handles scene creation, listing, and indexing.

Usage:
    python agents/scene_manager.py add --prompt "Place a witch" < output/scene.json
    python agents/scene_manager.py list
    python agents/scene_manager.py set-default scene_002
    python agents/scene_manager.py delete scene_002
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCENES_DIR = os.path.join(PROJECT_ROOT, "output", "scenes")
INDEX_PATH = os.path.join(SCENES_DIR, "index.json")
MAX_SCENES = 20


def load_index() -> dict:
    """Load or create the scene index."""
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH) as f:
            return json.load(f)
    return {"default": None, "scenes": []}


def save_index(index: dict):
    """Write the scene index to disk."""
    os.makedirs(SCENES_DIR, exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def next_id(index: dict) -> str:
    """Generate the next scene ID (scene_001, scene_002, ...)."""
    existing = {s["id"] for s in index["scenes"]}
    n = 1
    while f"scene_{n:03d}" in existing:
        n += 1
    return f"scene_{n:03d}"


def make_label(prompt: str | None) -> str:
    """Auto-generate a label from the prompt."""
    if not prompt:
        return "Untitled scene"
    label = prompt.strip()
    if len(label) > 40:
        label = label[:37] + "..."
    return label


def cmd_add(args):
    """Add a new scene from stdin JSON."""
    scene_data = json.load(sys.stdin)
    index = load_index()

    scene_id = next_id(index)
    label = make_label(args.prompt)
    filename = f"{scene_id}.json"
    filepath = os.path.join(SCENES_DIR, filename)

    os.makedirs(SCENES_DIR, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(scene_data, f, indent=2)

    entry = {
        "id": scene_id,
        "label": label,
        "file": filename,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    index["scenes"].append(entry)

    # First scene becomes the default
    if index["default"] is None:
        index["default"] = scene_id

    # Enforce max scenes limit — remove oldest beyond limit
    while len(index["scenes"]) > MAX_SCENES:
        oldest = index["scenes"].pop(0)
        old_path = os.path.join(SCENES_DIR, oldest["file"])
        if os.path.exists(old_path):
            os.remove(old_path)
        if index["default"] == oldest["id"]:
            index["default"] = index["scenes"][0]["id"] if index["scenes"] else None

    save_index(index)
    print(f"Added {scene_id}: {label}", file=sys.stderr)
    # Output the scene ID to stdout for scripts to capture
    print(scene_id)


def cmd_list(args):
    """List all scenes."""
    index = load_index()
    if not index["scenes"]:
        print("No scenes.")
        return
    for s in index["scenes"]:
        marker = " *" if s["id"] == index["default"] else ""
        print(f"  {s['id']}: {s['label']}{marker}")


def cmd_set_default(args):
    """Set the default scene."""
    index = load_index()
    ids = {s["id"] for s in index["scenes"]}
    if args.scene_id not in ids:
        print(f"Error: {args.scene_id} not found", file=sys.stderr)
        sys.exit(1)
    index["default"] = args.scene_id
    save_index(index)
    print(f"Default set to {args.scene_id}")


def cmd_delete(args):
    """Delete a scene."""
    index = load_index()
    found = None
    for i, s in enumerate(index["scenes"]):
        if s["id"] == args.scene_id:
            found = i
            break
    if found is None:
        print(f"Error: {args.scene_id} not found", file=sys.stderr)
        sys.exit(1)

    removed = index["scenes"].pop(found)
    old_path = os.path.join(SCENES_DIR, removed["file"])
    if os.path.exists(old_path):
        os.remove(old_path)

    if index["default"] == args.scene_id:
        index["default"] = index["scenes"][0]["id"] if index["scenes"] else None

    save_index(index)
    print(f"Deleted {args.scene_id}")


def main():
    parser = argparse.ArgumentParser(description="Scene manager")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a new scene (reads JSON from stdin)")
    add_p.add_argument("--prompt", default=None, help="Prompt used to generate the scene")

    sub.add_parser("list", help="List all scenes")

    sd_p = sub.add_parser("set-default", help="Set the default scene")
    sd_p.add_argument("scene_id", help="Scene ID to set as default")

    del_p = sub.add_parser("delete", help="Delete a scene")
    del_p.add_argument("scene_id", help="Scene ID to delete")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "set-default":
        cmd_set_default(args)
    elif args.command == "delete":
        cmd_delete(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
