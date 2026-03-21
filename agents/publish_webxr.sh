#!/bin/bash
# Publish the latest WebXR scene to the main landing page.
#
# Takes whatever is in webXR/ and links it from index.html
# so visitors can jump straight into the AR world.
#
# Usage:
#   ./agents/publish_webxr.sh
#
# What it does:
#   1. Verifies webXR/index.html exists
#   2. Injects/updates the "Enter the XR World" link in index.html
#   3. Lists the assets that will be served

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBXR_DIR="$PROJECT_ROOT/webXR"
LANDING_PAGE="$PROJECT_ROOT/index.html"

# Check that webXR content exists
if [ ! -f "$WEBXR_DIR/index.html" ]; then
    echo "Error: webXR/index.html not found. Run generate_all.sh or generate_scene.sh first."
    exit 1
fi

# Count models
GLB_COUNT=$(find "$WEBXR_DIR" -name "*.glb" 2>/dev/null | wc -l | tr -d ' ')
echo "Found $GLB_COUNT .glb models in webXR/"

# Check if the landing page already has the XR world link
if grep -q 'id="xr-world"' "$LANDING_PAGE"; then
    echo "Landing page already has the XR World section."
else
    echo "Injecting XR World section into index.html..."

    # Insert the XR world section before the FEATURES section
    sed -i '' '/<!-- FEATURES -->/i\
\
  <!-- XR WORLD — live AR scene -->\
  <section class="section xr-launch-section" id="xr-world">\
    <div class="container xr-launch-container">\
      <h2 class="section-title">Experience the AR World</h2>\
      <p class="xr-launch-sub">Step into our latest AI-generated augmented reality scene — built with Gemini + A-Frame. Navigate with WASD, look around with your mouse.</p>\
      <a href="webXR/index.html" class="btn btn-xr-launch">Enter the XR World</a>\
      <p class="xr-launch-hint">Works in any browser. For full VR, use a headset.</p>\
    </div>\
  </section>\
' "$LANDING_PAGE"

    echo "Injected XR World section."
fi

# Also add the XR World link to the nav if not already there
if grep -q 'href="#xr-world"' "$LANDING_PAGE"; then
    echo "Nav link already present."
else
    sed -i '' 's|<a href="#demo">Demo</a>|<a href="#xr-world">XR World</a>\
        <a href="#demo">Demo</a>|' "$LANDING_PAGE"
    echo "Added XR World to navigation."
fi

echo ""
echo "Done! The landing page now links to webXR/index.html"
echo "Assets in webXR/:"
ls -1 "$WEBXR_DIR"
