# Gemini Agent Plan

## Goal

Use the Gemini API in an autonomous observe/reason/act/evaluate loop that scans for available assets, calls Gemini, validates results, and writes scene.json with multi-character and 360° background support.

## Status

- [x] Agent implemented with observe/reason/act/evaluate loop (`agents/gemini_agent.py`)
- [x] Skill version preserved (`agents/gemini_agent_skill.py`)
- [x] API key verified working
- [x] Output directory (`output/`) for generated artifacts
- [x] Asset resolver (`generators/resolve_assets.py` + `asset_map.json`)
- [x] RealityKit pipeline wired end-to-end
- [x] WebXR A-Frame pipeline (`generators/generate_aframe.py`)
- [x] Multi-character support (characters array)
- [x] Asset observation (filesystem scan)
- [x] Asset fallback + validation
- [x] 360° background support (`--backgroundcreate`)
- [x] CLI flags: `--verbose`, `--dry-run`, `--clean`, `--max-loops`, `--backgroundcreate`
- [x] Demo-ready emoji trace in `--verbose` mode
- [ ] Additional asset files (.usdz / .glb) for each logical name
- [ ] 360° background images in `assets/backgrounds/`

## Language Choice: Python

**Why Python over JavaScript:**
- The [gemini-samples](https://github.com/philschmid/gemini-samples) reference repo is 97% Python
- Best structured output support via Pydantic models
- Runs directly from the command line (`python agents/gemini_agent.py "your prompt"`)
- No build step, no Node setup needed
- The WebXR side is static HTML (A-Frame) — no Node.js server to integrate with

## Prerequisites

- [x] `GEMINI_API_KEY` saved in `.env`
- [x] Python 3.10+ installed
- [x] `google-genai` package installed (via `.venv`)

## Step 1: Get and verify your Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **Create API Key** (or copy an existing one)
4. Paste it into your `.env` file:
   ```
   GEMINI_API_KEY=your-key-here
   ```
5. Verify the key works:
   ```bash
   source .venv/bin/activate
   python agents/gemini_agent.py "Say hello"
   ```

## Step 2: Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt`:
```
google-genai
python-dotenv
```

> **Note:** The old `google-generativeai` package is deprecated. Use `google-genai` instead.

## Step 3: Agent implementation (current)

Location: `agents/gemini_agent.py`

Uses the **new** `google-genai` SDK (not the deprecated `google-generativeai`):
- Model: `gemini-2.5-flash`
- `response_mime_type: "application/json"` forces valid JSON output
- Available asset names: `"character"`, `"witch"`, `"bruja"`, `"punkgirl"`

### Command-line usage

```bash
source .venv/bin/activate

# Basic usage
python agents/gemini_agent.py "Place a punk girl at position 0,1,-3"

# Full pipeline (generates, resolves, copies to Xcode)
./agents/generate_scene.sh "Place a punk girl at position 0,1,-3"
```

## Step 4: Pipeline — what's built

### RealityKit pipeline (DONE)

```
English prompt
  → agents/generate_scene.sh
  → agents/gemini_agent.py          → output/scene.json (raw Gemini output)
  → generators/resolve_assets.py    → output/scene_resolved.json (with resolved_asset)
  → cp to Xcode bundle              → VercelDeepmindHack/VercelDeepmindHack/scene.json
  → SceneLoader.swift               → decodes JSON, loads .usdz from bundle
  → ImmersiveView.swift             → adds entities to RealityKit scene
```

**Key files:**
| File | Role |
|---|---|
| `agents/gemini_agent.py` | Sends prompt to Gemini, returns structured JSON |
| `agents/generate_scene.sh` | Orchestrates the full pipeline |
| `generators/resolve_assets.py` | Maps logical names → platform-specific file paths |
| `generators/asset_map.json` | Asset name → file path lookup table |
| `SceneLoader.swift` | Decodes scene JSON, loads .usdz models into RealityKit entities |
| `ImmersiveView.swift` | Calls SceneLoader, adds entities to the immersive scene |

**How asset resolution works:**

1. Gemini returns a logical name like `"punkgirl"`
2. `resolve_assets.py` reads `asset_map.json` and adds `"resolved_asset": "punkgirl.usdz"`
3. `SceneLoader.swift` reads `resolved_asset`, strips the `.usdz` extension, and calls `Bundle.main.url(forResource: "punkgirl", withExtension: "usdz")`
4. If the `.usdz` file is missing, a purple placeholder sphere is shown instead

**Example resolved JSON:**
```json
{
  "action": "add_character",
  "character": {
    "type": "punk girl",
    "asset": "punkgirl",
    "resolved_asset": "punkgirl.usdz",
    "position": [0, 1, -3]
  }
}
```

### WebXR pipeline (TODO)

```
English prompt
  → agents/gemini_agent.py          → output/scene.json
  → generators/resolve_assets.py    → output/scene_resolved.json (webxr platform)
  → generators/generate_aframe.py   → webXR/index.html (A-Frame scene)
  → .glb assets copied to           → webXR/ (for browser loading)
```

**What needs to be built:**

1. **`generators/generate_aframe.py`** — reads resolved scene JSON and generates an A-Frame HTML file:
   - Creates an immersive sphere world (`<a-sky>` with environment)
   - Loads `.glb` models via `<a-gltf-model>` at the positions from the JSON
   - Outputs to `webXR/index.html`

2. **`agents/generate_webxr_scene.sh`** — shell script that orchestrates the WebXR pipeline:
   - Runs `gemini_agent.py` → `output/scene.json`
   - Runs `resolve_assets.py webxr` → `output/scene_resolved.json`
   - Runs `generate_aframe.py` → `webXR/index.html`
   - Copies resolved `.glb` files into `webXR/` so they load from the same directory

3. **Copy .glb assets into `webXR/`** — the browser needs the model files served alongside the HTML

**Target A-Frame output (`webXR/index.html`):**
```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://aframe.io/releases/1.7.0/aframe.min.js"></script>
</head>
<body>
  <a-scene>
    <!-- Immersive sphere world -->
    <a-sky color="#1a1a2e"></a-sky>
    <a-plane position="0 0 0" rotation="-90 0 0" width="20" height="20" color="#2d2d44"></a-plane>

    <!-- Character loaded from Gemini JSON -->
    <a-gltf-model src="punkgirl.glb" position="0 1 -3"></a-gltf-model>

    <!-- Camera -->
    <a-entity camera position="0 1.6 0" look-controls wasd-controls></a-entity>
  </a-scene>
</body>
</html>
```

**WebXR asset resolution:**

`resolve_assets.py webxr` maps logical names to `.glb` paths:
```json
{
  "action": "add_character",
  "character": {
    "type": "punk girl",
    "asset": "punkgirl",
    "resolved_asset": "assets/models/punkgirl/punkgirl.glb",
    "position": [0, 1, -3]
  }
}
```

The generator copies the `.glb` file into `webXR/` and references it by filename in the HTML.

## Step 5: Asset mapping

Gemini returns logical names only. The generator layer handles platform-specific resolution via `generators/asset_map.json`:

| Logical Name | RealityKit (.usdz) | WebXR (.glb) | Available? |
|---|---|---|---|
| `"character"` | `character.usdz` | `character.glb` | TBD |
| `"witch"` | `witch.usdz` | `witch.glb` | TBD |
| `"bruja"` | `bruja.usdz` | `bruja.glb` | `assets/models/bruja/` has files |
| `"punkgirl"` | `punkgirl.usdz` | `punkgirl.glb` | `assets/models/punkgirl/` has .usdz |

To add a new asset:
1. Add the model files to `assets/models/<name>/`
2. Add an entry to `generators/asset_map.json`
3. Add the name to the `Available asset names` list in `agents/gemini_agent.py`
4. For RealityKit: copy the `.usdz` into `VercelDeepmindHack/VercelDeepmindHack/`
5. For WebXR: the generator will copy `.glb` into `webXR/` at generation time

## Key Gemini API details

| Item | Value |
|---|---|
| API base URL | `https://generativelanguage.googleapis.com/v1beta/` |
| Model | `gemini-2.5-flash` |
| Auth | API key via `genai.Client(api_key=...)` |
| Structured output | Set `response_mime_type: "application/json"` in config |
| SDK (Python) | `google-genai` (NOT `google-generativeai`) |
| Pricing | Free tier: 15 RPM / 1M TPM for Flash |
| Docs | https://ai.google.dev/gemini-api/docs |
| Samples repo | https://github.com/philschmid/gemini-samples |

## Reference: gemini-samples repo highlights

From [philschmid/gemini-samples](https://github.com/philschmid/gemini-samples):
- **Structured Outputs with Pydantic** — enforcing JSON schemas
- **Function Calling Guide** — if we need tool-use later
- **Agentic Patterns** — ReAct agents, PydanticAI, CrewAI
- **Context Caching** — 75% cost savings for repeated prompts
- All examples are Python-first
