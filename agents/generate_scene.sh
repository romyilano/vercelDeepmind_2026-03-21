#!/bin/bash
# Generate a scene.json from a prompt and copy it into the Xcode project bundle.
#
# Usage:
#   ./agents/generate_scene.sh "Place a surfer witch at position 0,1,-3"
#   ./agents/generate_scene.sh --verbose "Place three characters"
#   ./agents/generate_scene.sh --backgroundcreate "Ocean scene with surfer"
#   ./agents/generate_scene.sh --dry-run --verbose "Test prompt"
#   ./agents/generate_scene.sh --clean "Fresh scene with punk girl"

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"
XCODE_RESOURCES="$PROJECT_ROOT/VercelDeepmindHack/VercelDeepmindHack"

mkdir -p "$OUTPUT_DIR"

# Separate flags from the prompt (last non-flag argument)
AGENT_FLAGS=()
PROMPT=""
for arg in "$@"; do
    case "$arg" in
        --verbose|--dry-run|--clean|--backgroundcreate)
            AGENT_FLAGS+=("$arg")
            ;;
        --max-loops=*)
            AGENT_FLAGS+=("$arg")
            ;;
        --max-loops)
            AGENT_FLAGS+=("$arg")
            ;;
        *)
            PROMPT="$arg"
            ;;
    esac
done

if [ -z "$PROMPT" ]; then
    echo "Usage: ./agents/generate_scene.sh [--verbose] [--dry-run] [--clean] [--backgroundcreate] \"your prompt here\""
    exit 1
fi

echo "Generating scene from prompt: $PROMPT"

# Activate venv and run agent
source "$PROJECT_ROOT/.venv/bin/activate"
python "$SCRIPT_DIR/gemini_agent.py" "${AGENT_FLAGS[@]}" "$PROMPT" > "$OUTPUT_DIR/scene_agent_output.json"

# The agent writes output/scene.json directly; also capture stdout
# Copy into Xcode project bundle so the app can load it
if [ -f "$OUTPUT_DIR/scene.json" ]; then
    cp "$OUTPUT_DIR/scene.json" "$XCODE_RESOURCES/scene.json"
    echo "Copied to $XCODE_RESOURCES/scene.json"

    # Register scene in the scene index
    SCENE_ID=$(python "$SCRIPT_DIR/scene_manager.py" add --prompt "$PROMPT" < "$OUTPUT_DIR/scene.json")
    echo "Registered as $SCENE_ID"

    # Copy all scenes + index to Xcode bundle
    mkdir -p "$XCODE_RESOURCES/scenes"
    cp "$OUTPUT_DIR/scenes/"*.json "$XCODE_RESOURCES/scenes/" 2>/dev/null || true
    echo "Copied scenes to $XCODE_RESOURCES/scenes/"
fi

# Also generate WebXR (A-Frame) output
if [ -f "$OUTPUT_DIR/scene.json" ]; then
    python "$PROJECT_ROOT/generators/resolve_assets.py" webxr < "$OUTPUT_DIR/scene.json" > "$OUTPUT_DIR/scene_resolved.json"
    echo "Resolved assets for webxr → output/scene_resolved.json"

    python "$PROJECT_ROOT/generators/generate_aframe.py" < "$OUTPUT_DIR/scene_resolved.json"
    echo "Generated WebXR scene → webXR/index.html"
fi

echo "Contents:"
cat "$OUTPUT_DIR/scene_agent_output.json"
