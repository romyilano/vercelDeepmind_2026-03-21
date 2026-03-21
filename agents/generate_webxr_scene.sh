#!/bin/bash
# Generate an A-Frame WebXR scene from a prompt.
#
# Usage:
#   ./agents/generate_webxr_scene.sh "Place a punk girl at position 0,1,-3"
#
# Output:
#   webXR/index.html   — A-Frame scene with 360° panorama + lighting
#   webXR/*.glb        — 3D model assets
#   webXR/*.png        — 360° panorama background

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"

mkdir -p "$OUTPUT_DIR"

if [ -z "$1" ]; then
    echo "Usage: ./agents/generate_webxr_scene.sh \"your prompt here\""
    exit 1
fi

echo "Generating WebXR scene from prompt: $1"

# Activate venv and run agent
source "$PROJECT_ROOT/.venv/bin/activate"

# Step 1: Generate raw scene JSON
python "$SCRIPT_DIR/gemini_agent.py" "$1" > "$OUTPUT_DIR/scene.json"
echo "Generated output/scene.json"

# Step 2: Register scene in the scene index
SCENE_ID=$(python "$SCRIPT_DIR/scene_manager.py" add --prompt "$1" < "$OUTPUT_DIR/scene.json")
echo "Registered as $SCENE_ID"

# Step 3: Resolve asset names for WebXR platform
python "$PROJECT_ROOT/generators/resolve_assets.py" webxr < "$OUTPUT_DIR/scene.json" > "$OUTPUT_DIR/scene_resolved.json"
echo "Resolved assets for webxr → output/scene_resolved.json"

# Step 4: Generate A-Frame HTML and copy .glb assets + scenes
python "$PROJECT_ROOT/generators/generate_aframe.py" < "$OUTPUT_DIR/scene_resolved.json"

echo ""
echo "Done! Open webXR/index.html in a browser to view the scene."
echo "Scene JSON:"
cat "$OUTPUT_DIR/scene_resolved.json"
