#!/usr/bin/env python3
"""Resolve logical asset names in scene JSON to platform-specific file paths.

Usage:
    python generators/resolve_assets.py realitykit < output/scene.json
    python generators/resolve_assets.py webxr < output/scene.json

Reads scene JSON from stdin, replaces the "asset" field with the resolved
file path for the given platform, and prints the updated JSON to stdout.
"""

import sys
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_MAP_PATH = os.path.join(SCRIPT_DIR, "asset_map.json")


def load_asset_map() -> dict:
    with open(ASSET_MAP_PATH) as f:
        return json.load(f)


def resolve_character(char: dict, platform: str, asset_map: dict) -> dict:
    """Replace logical asset name with platform-specific path for one character."""
    logical_name = char.get("asset", "")
    if logical_name and logical_name in asset_map and platform in asset_map[logical_name]:
        char["resolved_asset"] = asset_map[logical_name][platform]
    elif logical_name:
        char["resolved_asset"] = f"{logical_name}.usdz" if platform == "realitykit" else f"{logical_name}.glb"
    return char


def resolve(scene: dict, platform: str, asset_map: dict) -> dict:
    """Replace logical asset name with platform-specific path."""
    # Handle characters array format
    if "characters" in scene:
        scene["characters"] = [
            resolve_character(c, platform, asset_map) for c in scene["characters"]
        ]
    # Handle single character format
    if "character" in scene and "asset" in scene["character"]:
        resolve_character(scene["character"], platform, asset_map)
    return scene


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("realitykit", "webxr"):
        print('Usage: python generators/resolve_assets.py <realitykit|webxr>', file=sys.stderr)
        sys.exit(1)

    platform = sys.argv[1]
    scene = json.load(sys.stdin)
    asset_map = load_asset_map()
    resolved = resolve(scene, platform, asset_map)
    print(json.dumps(resolved, indent=2))


if __name__ == "__main__":
    main()
