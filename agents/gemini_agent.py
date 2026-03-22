#!/usr/bin/env python3
"""Gemini scene agent — autonomous loop for XR scene pipeline.

Observe/Reason/Act/Evaluate loop that:
1. Scans disk for available .usdz/.glb assets and backgrounds
2. Calls Gemini to interpret the prompt (supports multiple characters)
3. Validates assets, swaps missing ones to fallbacks, writes scene.json
4. Checks if scene is complete and valid; if not, adjusts and loops

Usage:
    python agents/gemini_agent.py "Place a witch and a punk girl in the scene"
    python agents/gemini_agent.py --verbose "Beach scene with characters"
    python agents/gemini_agent.py --backgroundcreate "Ocean scene with a surfer"
    python agents/gemini_agent.py --dry-run --verbose "Test prompt"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "models"
BACKGROUNDS_DIR = PROJECT_ROOT / "assets" / "backgrounds"
XCODE_RESOURCES = PROJECT_ROOT / "VercelDeepmindHack" / "VercelDeepmindHack"
OUTPUT_DIR = PROJECT_ROOT / "output"

FALLBACK_ASSET = "bruja"
MODEL_EXTENSIONS = {".usdz", ".glb", ".blend", ".obj", ".fbx"}
BACKGROUND_EXTENSIONS = {".jpg", ".jpeg", ".png", ".hdr", ".exr"}
POSITION_BOUNDS = (-20, 20)
DEFAULT_POSITION = [0, 1, -3]

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are an AI agent for an XR scene pipeline.

You decide what action to take and return structured JSON.

Always respond with valid JSON only. No markdown. No explanation.

Schema:
{
  "characters": [
    {
      "type": "<description>",
      "asset": "<logical asset name>",
      "position": [number, number, number]
    }
  ]
}

Rules:
- Always return a "characters" array (even for one character)
- Each character needs "type", "asset", and "position"
- Use simple values
- Default asset = "character"
- Available asset names: AVAILABLE_ASSETS
- Space characters apart — avoid duplicate positions
"""

SYSTEM_INSTRUCTION_WITH_BG = SYSTEM_INSTRUCTION + """
Also include a "background" field for the environment sphere:
{
  "characters": [...],
  "background": {
    "type": "360_sphere",
    "asset": "<background name>",
    "description": "<what the 360 environment looks like>"
  }
}

Available background names: AVAILABLE_BACKGROUNDS
If no background matches, suggest a descriptive name for a new one.
"""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str, verbose: bool):
    if verbose:
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Phase: OBSERVE
# ---------------------------------------------------------------------------

def observe(verbose: bool = False) -> dict:
    """Scan filesystem for available assets, backgrounds, and existing scene."""
    t0 = time.time()

    available_assets = {}
    # Scan assets/models/
    if ASSETS_DIR.is_dir():
        for model_dir in sorted(ASSETS_DIR.iterdir()):
            if not model_dir.is_dir():
                continue
            name = model_dir.name
            exts = set()
            for f in model_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in MODEL_EXTENSIONS:
                    exts.add(f.suffix.lower())
            if exts:
                available_assets[name] = sorted(exts)

    # Scan Xcode resources for .usdz
    if XCODE_RESOURCES.is_dir():
        for f in XCODE_RESOURCES.iterdir():
            if f.is_file() and f.suffix.lower() == ".usdz":
                name = f.stem
                if name not in available_assets:
                    available_assets[name] = [".usdz"]
                elif ".usdz" not in available_assets[name]:
                    available_assets[name].append(".usdz")
                    available_assets[name].sort()

    # Scan backgrounds
    available_backgrounds = []
    if BACKGROUNDS_DIR.is_dir():
        for f in sorted(BACKGROUNDS_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in BACKGROUND_EXTENSIONS:
                available_backgrounds.append(f.name)

    # Load existing scene
    existing_scene = None
    scene_path = OUTPUT_DIR / "scene.json"
    if scene_path.is_file():
        try:
            existing_scene = json.loads(scene_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    state = {
        "available_assets": available_assets,
        "available_backgrounds": available_backgrounds,
        "existing_scene": existing_scene,
    }

    elapsed = time.time() - t0
    log(f"\U0001f50d OBSERVE ({elapsed:.2f}s) — Assets: {available_assets}", verbose)
    log(f"   Backgrounds: {available_backgrounds}", verbose)
    if existing_scene:
        log(f"   Existing scene.json found", verbose)

    return state


# ---------------------------------------------------------------------------
# Phase: REASON
# ---------------------------------------------------------------------------

def reason(prompt: str, state: dict, backgroundcreate: bool = False,
           verbose: bool = False) -> dict:
    """Call Gemini to interpret the prompt. Returns parsed JSON."""
    t0 = time.time()

    asset_names = list(state["available_assets"].keys()) or ["character"]
    bg_names = state["available_backgrounds"] or ["none available"]

    if backgroundcreate:
        instruction = SYSTEM_INSTRUCTION_WITH_BG
        instruction = instruction.replace("AVAILABLE_BACKGROUNDS",
                                          json.dumps(bg_names))
    else:
        instruction = SYSTEM_INSTRUCTION

    instruction = instruction.replace("AVAILABLE_ASSETS",
                                      json.dumps(asset_names))

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "system_instruction": instruction,
            "response_mime_type": "application/json",
        },
    )
    result = json.loads(response.text)

    # Backward compat: wrap old single-character format into array
    if "character" in result and "characters" not in result:
        result["characters"] = [result.pop("character")]
    if "characters" not in result:
        result["characters"] = []

    n = len(result["characters"])
    elapsed = time.time() - t0
    log(f"\U0001f9e0 REASON ({elapsed:.2f}s) — Gemini returned {n} character(s)", verbose)
    if backgroundcreate and "background" in result:
        log(f"   Background: {result['background'].get('asset', 'unknown')}", verbose)

    return result


# ---------------------------------------------------------------------------
# Phase: ACT
# ---------------------------------------------------------------------------

def _clamp(val, lo, hi):
    try:
        v = float(val)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return 0.0


def _validate_position(pos):
    if not isinstance(pos, list) or len(pos) != 3:
        return list(DEFAULT_POSITION)
    return [_clamp(v, *POSITION_BOUNDS) for v in pos]


def act(gemini_result: dict, state: dict, clean: bool = False,
        append: bool = False, dry_run: bool = False, verbose: bool = False) -> dict:
    """Resolve assets, validate, write scene.json. Returns report dict."""
    t0 = time.time()
    available = state["available_assets"]
    characters = []
    warnings = []

    for char in gemini_result.get("characters", []):
        asset = char.get("asset", "character")
        original_asset = None

        # Resolve asset
        if asset not in available:
            if FALLBACK_ASSET in available:
                original_asset = asset
                log(f"\U0001f504 \"{asset}\" \u2192 \"{FALLBACK_ASSET}\" (not found on disk)",
                    verbose)
                warnings.append(f"\"{asset}\" swapped to \"{FALLBACK_ASSET}\"")
                asset = FALLBACK_ASSET
            else:
                log(f"\u274c \"{asset}\" not found and fallback \"{FALLBACK_ASSET}\" "
                    f"also missing — skipping", verbose)
                warnings.append(f"\"{asset}\" skipped (no fallback)")
                continue

        entry = {
            "type": char.get("type", asset),
            "asset": asset,
            "position": _validate_position(char.get("position")),
        }
        if original_asset:
            entry["_original_asset"] = original_asset
        characters.append(entry)

    # Only merge with existing scene if --append is explicitly set
    if append and not clean and state.get("existing_scene"):
        existing_chars = state["existing_scene"].get("characters", [])
        characters = existing_chars + characters

    # Build scene
    scene = {"characters": characters}

    # Handle background
    bg = gemini_result.get("background")
    if bg:
        bg_asset = bg.get("asset", "")
        bg_exists = bg_asset in [Path(b).stem for b in state["available_backgrounds"]]
        if not bg_exists:
            # Check with extension
            bg_exists = bg_asset in state["available_backgrounds"]

        scene["background"] = {
            "type": bg.get("type", "360_sphere"),
            "asset": bg_asset,
            "description": bg.get("description", ""),
            "exists": bg_exists,
        }
        if bg_exists:
            log(f"\U0001f310 Background: {bg_asset} (found on disk)", verbose)
        else:
            log(f"\u26a0\ufe0f  Background: {bg_asset} (not found \u2014 needs creation)",
                verbose)
            warnings.append(f"Background \"{bg_asset}\" not found on disk")

    # Check for duplicate positions
    positions = [tuple(c["position"]) for c in characters]
    seen = set()
    for p in positions:
        if p in seen:
            warnings.append(f"Duplicate position {list(p)}")
            log(f"\u26a0\ufe0f  Duplicate position {list(p)}", verbose)
        seen.add(p)

    # Write files
    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        scene_path = OUTPUT_DIR / "scene.json"
        scene_path.write_text(json.dumps(scene, indent=2))
        log(f"\u26a1 ACT — Wrote {scene_path}", verbose)
    else:
        log(f"\u26a1 ACT (dry-run) — Would write scene.json", verbose)

    elapsed = time.time() - t0
    report = {
        "scene": scene,
        "characters_placed": len(characters),
        "warnings": warnings,
        "dry_run": dry_run,
        "elapsed": elapsed,
    }
    return report


# ---------------------------------------------------------------------------
# Phase: EVALUATE
# ---------------------------------------------------------------------------

def evaluate(report: dict, backgroundcreate: bool = False,
             verbose: bool = False) -> tuple[bool, list[str]]:
    """Validate the report. Returns (success, list_of_issues)."""
    t0 = time.time()
    issues = []

    if report["characters_placed"] == 0:
        issues.append("No characters were placed")

    scene = report["scene"]
    if backgroundcreate:
        if "background" not in scene:
            issues.append("Background was requested but not included")
        elif not scene["background"].get("exists"):
            # Flag but don't block
            pass

    success = len(issues) == 0
    elapsed = time.time() - t0

    if success:
        n = report["characters_placed"]
        bg_str = ""
        if "background" in scene:
            bg_str = " + background"
        log(f"\U0001f4cb EVALUATE ({elapsed:.2f}s) — Valid: {n} character(s){bg_str}",
            verbose)
    else:
        log(f"\U0001f4cb EVALUATE ({elapsed:.2f}s) — Issues: {issues}", verbose)

    return success, issues


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(prompt: str, max_loops: int = 5, dry_run: bool = False,
              verbose: bool = False, clean: bool = False, append: bool = False,
              backgroundcreate: bool = False) -> dict:
    """Main agent loop: observe → reason → act → evaluate, with retry."""
    total_t0 = time.time()

    for loop_num in range(1, max_loops + 1):
        if loop_num > 1:
            log(f"\U0001f504 RETRY — loop {loop_num}/{max_loops}", verbose)

        state = observe(verbose=verbose)
        gemini_result = reason(prompt, state,
                               backgroundcreate=backgroundcreate,
                               verbose=verbose)
        report = act(gemini_result, state, clean=clean, append=append,
                     dry_run=dry_run, verbose=verbose)
        success, issues = evaluate(report,
                                   backgroundcreate=backgroundcreate,
                                   verbose=verbose)

        if success:
            total_elapsed = time.time() - total_t0
            n = report["characters_placed"]
            bg_str = ""
            if "background" in report["scene"]:
                bg_str = " + background"
            log(f"\U0001f389 {n} character(s){bg_str} placed in "
                f"{loop_num} loop(s) ({total_elapsed:.1f}s)", verbose)
            break

        # Adjust prompt for retry
        prompt = f"Fix: {'; '.join(issues)}. Original: {prompt}"

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gemini scene agent — autonomous XR scene generator"
    )
    parser.add_argument("prompt", help="Natural language scene description")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan without writing files")
    parser.add_argument("--max-loops", type=int, default=5,
                        help="Cap agent iterations (default: 5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show full agent trace")
    parser.add_argument("--clean", action="store_true",
                        help="Ignore existing scene.json, start fresh")
    parser.add_argument("--append", action="store_true",
                        help="Merge new characters into existing scene.json")
    parser.add_argument("--backgroundcreate", action="store_true",
                        help="Include 360 background sphere in scene")

    args = parser.parse_args()

    report = run_agent(
        prompt=args.prompt,
        max_loops=args.max_loops,
        dry_run=args.dry_run,
        verbose=args.verbose,
        clean=args.clean,
        append=args.append,
        backgroundcreate=args.backgroundcreate,
    )

    # Clean JSON to stdout
    print(json.dumps(report["scene"], indent=2))

    sys.exit(0 if report["characters_placed"] > 0 else 1)


if __name__ == "__main__":
    main()
