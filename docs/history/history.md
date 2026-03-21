# Project History

## 2026-03-21: Hackathon Entry Point

### run.sh
Created a universal entry point (`run.sh`) in the project root to simplify testing and evaluation for the hackathon. It handles environment setup (Python venv, requirements), prompts for the Gemini API key if missing, and wraps the core pipeline (`agents/generate_scene.sh`) to generate and deploy scenes to both RealityKit and WebXR simultaneously.

## 2026-03-21: Gemini-to-RealityKit Pipeline

### generate_scene.sh

Shell script that takes natural language and produces scene JSON via Gemini.

```
# Usage:
#   ./agents/generate_scene.sh "Place a surfer witch at position 0,1,-3"
```

Uses `agents/gemini_agent.py` under the hood, outputs `scene.json` into the Xcode project folder.

### SceneLoader.swift

Decodes Gemini-generated `scene.json` and creates RealityKit entities. For each character entry:
1. Loads `{asset}.usdz` from the app bundle
2. Falls back to a purple placeholder sphere if the model is missing
3. Places it at the position specified in the JSON

### ImmersiveView.swift changes

Updated to call `SceneLoader.loadFromBundle()` after loading the base "Immersive" scene (skybox, ground).

### bruja.usdz test

- Copied `assets/models/bruja/bruja_model.usdz` → `VercelDeepmindHack/VercelDeepmindHack/bruja.usdz`
- Generated scene.json targeting "bruja" asset at position [0, 1, -3]
- Files must be added to Xcode project manually (drag into file navigator, add to target)

## 2026-03-21: Unified Pipeline + generate_all.sh

### generate_scene.sh now outputs to both platforms

Previously `generate_scene.sh` only copied scene.json to the Xcode bundle. Now it also runs the WebXR pipeline (`resolve_assets.py` → `generate_aframe.py`), so a single command produces output for both visionOS and WebXR.

### generate_all.sh — batch generation without prompts

New script that scans `assets/models/` for all model directories and generates a scene with every model, no prompt or API key needed.

```
# Usage:
#   ./agents/generate_all.sh
```

- Auto-discovers model directories (bruja, punkgirl, world, etc.)
- Spaces models along the X axis (3 units apart)
- Outputs to both Xcode bundle and `webXR/index.html`
- Copies `.glb` files into `webXR/` for browser loading

### Generator updates for multi-character support

- `resolve_assets.py` — updated to handle `characters` array format (not just single `character` object)
- `generate_aframe.py` — updated to loop over `characters` array, deduplicating asset tags and .glb copies

## 2026-03-21: Gemini Agent Rewrite (Observe/Reason/Act/Evaluate)

### Agent loop replaces single-shot skill

`gemini_agent.py` rewritten from a single-shot API call into an autonomous agent with:
- **Observe** — scans `assets/models/` and `assets/backgrounds/` for available files
- **Reason** — calls Gemini with prompt + available asset context
- **Act** — validates assets (swaps missing to fallback), writes `scene.json`
- **Evaluate** — checks validity, retries with adjusted prompt if needed

Original skill version preserved as `gemini_agent_skill.py`.

### CLI flags added

`--verbose`, `--dry-run`, `--clean`, `--max-loops N`, `--backgroundcreate`

### Multi-character + 360° background support

- Output format changed from single `character` object to `characters` array
- `--backgroundcreate` flag adds `background` field with 360° sphere info
- Agent scans `assets/backgrounds/` for available panoramas

### punkgirl model added

- `punkgirl` added to available assets in agent and `asset_map.json`
- `punkgirl.usdz` copied into Xcode bundle
- `.glb` mapped from `assets/models/punkgirl/glb/punk_girl.glb`

## 2026-03-21: WebXR Lighting + Panorama Fixes

### Dark scene fix

A-Frame scenes were too dark — models barely visible against black sky.

**Lighting changes:**
- Ambient light: `#445` at 0.6 → `#fff` at 2.0
- Directional: single at 0.8 → two lights at 2.5 and 1.2 (pink-tinted fill)
- Added hemisphere light at 1.5 with pink ground color

**Sky changes:**
- Default sky is now pastel pink (`#FFD6E0`) instead of black
- 360° panorama (`Mexican Punk House Surf_pano.png`) used as default `<a-sky>` texture
- Fixed filename with spaces — panorama copied as `punk_house.png` into `webXR/`
- If panorama fails to load, pastel pink fallback shows instead of black

**Model positioning:**
- Models raised to minimum Y=0.5 so full body is visible above floor
- `generate_all.sh` places models at Y=0.5 instead of Y=0
- Ground plane removed — the `<a-plane>` was showing as a white band cutting across the panorama. With a 360° sky sphere, no separate floor is needed

## 2026-03-21: SceneLoader.swift JSON Format Fix

### Mismatched JSON schema

`SceneLoader.swift` expected a single-action format (`{ "action": "add_character", "character": {...} }`) but the pipeline produces a multi-character format (`{ "characters": [...] }`). This meant positions and models from `scene.json` never actually loaded in visionOS.

### Changes

- Replaced `SceneInstruction` (single action + single character) with `SceneDescription` (characters array)
- `buildEntities` now iterates over `scene.characters` instead of switching on an `action` string
- Positions from `scene.json` now flow correctly: `[Float]` → `SIMD3<Float>` → `entity.position`
- RealityKit output now matches WebXR A-Frame positioning (e.g. bruja at `[0, 0.5, -3]`, punkgirl at `[3, 0.5, -3]`)

## 2026-03-21: Documentation Updates

### README.md
- Updated RealityKit pipeline diagram to show `SceneDescription.characters` decode step
- Clarified that SceneLoader decodes the `characters` array and positions match A-Frame output

### assets/HOW-TO.md
- Updated RealityKit pipeline section with characters array decode details
- Added note that positions are identical across both platforms
- Updated asset fallback section to describe SceneLoader's array-based decoding