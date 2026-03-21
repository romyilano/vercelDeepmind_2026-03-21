# Gemini Agent Plan

## Goal

Use the Google Gemini API as a structured JSON generator that produces scene instructions for the XR pipeline. Gemini is NOT a full autonomous agent -- it receives a prompt and returns structured JSON that the pipeline executes.

## Status

- [x] Agent implemented and tested (`agents/gemini_agent.py`)
- [x] API key verified working
- [x] Output directory (`output/`) for generated artifacts
- [x] Asset resolver (`generators/resolve_assets.py` + `asset_map.json`)
- [x] RealityKit pipeline wired end-to-end (Gemini → scene.json → SceneLoader.swift → ImmersiveView)
- [x] punkgirl model added as available asset
- [ ] WebXR pipeline (Gemini → scene.json → A-Frame HTML in `webXR/`)
- [ ] Additional asset files (.usdz / .glb) for each logical name

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

## Step 3: Create the agent module

Location: `agents/gemini_agent.py` (already created)

### Command-line usage

```bash
# Activate the venv first
source .venv/bin/activate

# Basic usage — pass a prompt as an argument
python agents/gemini_agent.py "Place a surfer witch at position 0,1,-3"

# Pipe output to a file
python agents/gemini_agent.py "Add a dragon at 2,0,-5" > output/scene.json

# Use with jq for pretty printing
python agents/gemini_agent.py "Add a witch character" | jq .
```

### Verified output

Tested on 2026-03-21 — returns valid JSON:
```json
{
  "action": "add_character",
  "character": {
    "type": "surfer witch",
    "asset": "witch",
    "position": [0, 1, -3]
  }
}
```

## Step 4: Agent implementation (Python)

Uses the **new** `google-genai` SDK (not the deprecated `google-generativeai`):

```python
#!/usr/bin/env python3
"""Gemini agent — structured JSON generator for XR scene pipeline."""

import sys
import json
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_INSTRUCTION = """
You are an AI agent for an XR scene pipeline.

You decide what action to take and return structured JSON.

Always respond with valid JSON only. No markdown. No explanation.

Schema:
{
  "action": "add_character" | "convert_scene",
  "character": {
    "type": "<description>",
    "asset": "<logical asset name>",
    "position": [number, number, number]
  }
}

Rules:
- Always include an "action"
- If adding a character, include "character"
- Use simple values
- Default asset = "character"
- Available asset names: "character", "witch", "bruja"
"""

MODEL = "gemini-2.5-flash"


def generate_scene_json(prompt: str) -> dict:
    """Send prompt to Gemini, return parsed JSON."""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
        },
    )
    return json.loads(response.text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python agents/gemini_agent.py "your prompt here"', file=sys.stderr)
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    result = generate_scene_json(prompt)
    print(json.dumps(result, indent=2))
```

Key points:
- Uses `google-genai` (new SDK), not `google-generativeai` (deprecated)
- Model: `gemini-2.5-flash` (the older `gemini-2.0-flash` is retired for new users)
- `response_mime_type: "application/json"` forces Gemini to return valid JSON
- `python-dotenv` loads the `.env` file automatically
- Outputs to stdout so you can pipe it anywhere

## Step 5: Wire into the pipeline

```
Command line prompt
  -> python agents/gemini_agent.py "prompt"
  -> scene JSON (stdout)
  -> /generators (JSON -> RealityKit Swift OR A-Frame HTML)
  -> output
```

- For **WebXR**: pipe JSON into a generator that injects entities into A-Frame scenes in `webXR/`
- For **RealityKit**: pipe JSON into a generator that maps asset names to `.usdz` files for Swift code in `VercelDeepmindHack/`

## Step 6: Asset mapping

Gemini returns logical names only. The generator layer handles platform-specific resolution:

| Logical Name | RealityKit (.usdz) | WebXR (.glb) | Available? |
|---|---|---|---|
| `"character"` | `character.usdz` | `character.glb` | TBD |
| `"witch"` | `witch.usdz` | `witch.glb` | TBD |
| `"bruja"` | `bruja.usdz` | `bruja.glb` | `assets/models/bruja/` has files |

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
