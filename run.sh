#!/bin/bash
# VercelHackDeepMind - Hackathon Entry Point
# 
# This script is the main entry point to run the Gemini Scene Agent Pipeline.
# It takes a natural language prompt, uses Gemini to select and place 3D assets,
# and outputs the scene to both Apple Vision Pro (RealityKit) and WebXR (A-Frame).

set -e

# Change to the directory of this script
cd "$(dirname "$0")"

echo "=========================================================="
echo "    🔮 VercelHackDeepMind: Gemini XR Scene Pipeline 🔮    "
echo "=========================================================="

# 1. Check for Python environment
if [ ! -d ".venv" ]; then
    echo "📦 Setting up Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "✅ Environment setup complete."
else
    source .venv/bin/activate
fi

# 2. Check for API key
if [ ! -f ".env" ] || ! grep -q "GEMINI_API_KEY" ".env"; then
    echo "⚠️  Missing GEMINI_API_KEY in .env file."
    read -p "Enter your Gemini API Key (or press enter to skip if set in env): " api_key
    if [ ! -z "$api_key" ]; then
        echo "GEMINI_API_KEY=$api_key" >> .env
        echo "✅ Saved to .env"
    fi
fi

# 3. Handle arguments
if [ $# -eq 0 ]; then
    echo ""
    echo "Usage: ./run.sh \"<your scene description>\" [flags]"
    echo "Example: ./run.sh \"Place a witch and a punk girl in the scene\""
    echo ""
    echo "Optional flags (place before prompt):"
    echo "  --verbose          Show detailed agent thinking process"
    echo "  --backgroundcreate Include a 360 environment background"
    echo "  --clean            Start fresh (ignore existing scene.json)"
    echo "  --append           Add to existing scene instead of replacing"
    echo "=========================================================="
    exit 1
fi

echo ""
echo "🚀 Starting the Gemini Agent Pipeline..."
echo ""

# 4. Execute the core pipeline (which handles both Xcode and WebXR targets)
bash ./agents/generate_scene.sh "$@"

echo ""
echo "=========================================================="
echo "✨ Pipeline Complete! ✨"
echo "=========================================================="
echo "🍎 Vision Pro / RealityKit:"
echo "   The scene.json has been copied to your Xcode bundle."
echo "   Open VercelDeepmindHack.xcodeproj and run the app."
echo ""
echo "🌐 WebXR / A-Frame:"
echo "   The scene has been generated along with required assets."
echo "   Open webXR/index.html in any modern web browser to view."
echo "=========================================================="
