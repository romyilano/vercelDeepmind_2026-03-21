#!/bin/bash
# Generate a scene with ALL models in assets/models/ — no prompt needed.
#
# Scans assets/models/ for model directories, builds a scene.json with
# every model spaced out along the X axis, then generates WebXR output.
#
# Usage:
#   ./agents/generate_all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"
MODELS_DIR="$PROJECT_ROOT/assets/models"
XCODE_RESOURCES="$PROJECT_ROOT/VercelDeepmindHack/VercelDeepmindHack"

mkdir -p "$OUTPUT_DIR"

# Scan assets/models/ for model directories (skip hidden files)
MODELS=()
for dir in "$MODELS_DIR"/*/; do
    name="$(basename "$dir")"
    [[ "$name" == .* ]] && continue
    MODELS+=("$name")
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "No models found in $MODELS_DIR"
    exit 1
fi

echo "Found ${#MODELS[@]} models: ${MODELS[*]}"

# Build scene.json with all models spaced along X axis
X_OFFSET=0
SPACING=3
CHARACTERS=""

for name in "${MODELS[@]}"; do
    if [ -n "$CHARACTERS" ]; then
        CHARACTERS+=","
    fi
    CHARACTERS+=$(cat <<CHAR

    {
      "type": "$name",
      "asset": "$name",
      "position": [$X_OFFSET.0, 0.5, -3.0]
    }
CHAR
)
    X_OFFSET=$((X_OFFSET + SPACING))
done

SCENE_JSON=$(cat <<JSON
{
  "characters": [$CHARACTERS
  ]
}
JSON
)

echo "$SCENE_JSON" > "$OUTPUT_DIR/scene.json"
echo "Generated output/scene.json with ${#MODELS[@]} models"

# Activate venv
source "$PROJECT_ROOT/.venv/bin/activate"

# Register as an indexed scene
SCENE_ID=$(python "$SCRIPT_DIR/scene_manager.py" add --prompt "All models" < "$OUTPUT_DIR/scene.json")
echo "Registered as $SCENE_ID"

# Copy to Xcode project
if [ -d "$XCODE_RESOURCES" ]; then
    cp "$OUTPUT_DIR/scene.json" "$XCODE_RESOURCES/scene.json"
    mkdir -p "$XCODE_RESOURCES/scenes"
    cp "$OUTPUT_DIR/scenes/"*.json "$XCODE_RESOURCES/scenes/" 2>/dev/null || true
    echo "Copied to $XCODE_RESOURCES/"
fi

# Generate WebXR
python "$PROJECT_ROOT/generators/resolve_assets.py" webxr < "$OUTPUT_DIR/scene.json" > "$OUTPUT_DIR/scene_resolved.json"
echo "Resolved assets for webxr -> output/scene_resolved.json"

python "$PROJECT_ROOT/generators/generate_aframe.py" < "$OUTPUT_DIR/scene_resolved.json"
echo "Generated WebXR scene -> webXR/index.html"

echo ""
echo "Done! Open webXR/index.html to view all ${#MODELS[@]} models."
echo "Scene JSON:"
cat "$OUTPUT_DIR/scene.json"
