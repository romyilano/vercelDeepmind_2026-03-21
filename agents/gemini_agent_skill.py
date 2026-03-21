#!/usr/bin/env python3
# ARCHIVED: single-shot skill version. See gemini_agent.py for the agent version.
"""Gemini agent — structured JSON generator for XR scene pipeline (skill version)."""

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
- Available asset names: "character", "witch", "bruja", "punkgirl"
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
