# Multiple Scenes Plan

> **Purpose:** Allow multiple scenes to be generated and stored, with a menu to switch between them. The first scene created is the default. Scene names are auto-generated (not entered by the user).

---

## Concept

Each time the user runs the pipeline, a new scene is created and added to a scene index. Both platforms (visionOS + WebXR) show a menu in the top-right corner to switch between scenes.

```
generate_scene.sh "Place a witch on the beach"
  → output/scenes/scene_001.json  (auto-named)
  → output/scenes/scene_002.json  (next run)
  → output/scenes/index.json      (scene list)
```

The first scene in the index is always the default (loaded on startup).

---

## Architecture

### Scene storage

```
output/
└── scenes/
    ├── index.json          # List of all scenes
    ├── scene_001.json      # First scene (default)
    ├── scene_002.json      # Second scene
    └── scene_003.json      # ...
```

### index.json format

```json
{
  "default": "scene_001",
  "scenes": [
    {
      "id": "scene_001",
      "label": "Witch on the beach",
      "file": "scene_001.json",
      "created": "2026-03-21T16:30:00Z"
    },
    {
      "id": "scene_002",
      "label": "Punk girl in surf house",
      "file": "scene_002.json",
      "created": "2026-03-21T16:35:00Z"
    }
  ]
}
```

- **`id`** — auto-generated sequential name (`scene_001`, `scene_002`, ...)
- **`label`** — derived from the prompt (first ~40 chars, or Gemini can summarize)
- **`default`** — always the first scene created
- No user input needed for naming

### Individual scene files

Same format as today:
```json
{
  "characters": [...],
  "background": { ... }
}
```

---

## Phase 1: Scene Manager (Python)

Create `agents/scene_manager.py` — handles scene creation, listing, and indexing.

**What to do:**

1. When a new scene is generated, `scene_manager.py`:
   - Reads `output/scenes/index.json` (or creates it)
   - Determines next ID: `scene_001`, `scene_002`, etc.
   - Auto-generates label from the prompt (truncate to ~40 chars)
   - Saves the scene JSON as `output/scenes/scene_XXX.json`
   - Updates `index.json` with the new entry
   - First scene becomes the default

2. CLI:
   ```bash
   # Called by generate_scene.sh after agent runs
   python agents/scene_manager.py add --prompt "Place a witch" < output/scene.json

   # List all scenes
   python agents/scene_manager.py list

   # Set default scene
   python agents/scene_manager.py set-default scene_002
   ```

3. The existing `output/scene.json` continues to work as the "latest" scene for backward compat

**Done when:**
- [ ] Running the pipeline twice creates `scene_001.json` and `scene_002.json`
- [ ] `index.json` lists both scenes
- [ ] First scene is marked as default
- [ ] `scene_manager.py list` prints all scenes
- [ ] No user input needed for naming

---

## Phase 2: WebXR Scene Menu (A-Frame)

Add a scene switcher menu to `webXR/index.html` — top-right overlay.

**What to do:**

1. Update `generators/generate_aframe.py` to:
   - Copy all scene JSON files into `webXR/scenes/`
   - Copy `index.json` into `webXR/scenes/`
   - Generate a menu overlay in the HTML

2. The menu is **HTML/CSS overlay on top of A-Frame** (not an A-Frame entity):
   ```html
   <div id="scene-menu" style="position:fixed; top:16px; right:16px; z-index:999;">
     <button id="menu-toggle">Scenes</button>
     <div id="scene-list" style="display:none;">
       <a href="#" class="scene-item active" data-scene="scene_001">Witch on the beach</a>
       <a href="#" class="scene-item" data-scene="scene_002">Punk girl in surf house</a>
     </div>
   </div>
   ```

3. JavaScript scene switching:
   - On click, fetch `scenes/scene_XXX.json`
   - Remove existing `<a-gltf-model>` entities
   - Parse new scene JSON, create new `<a-gltf-model>` entities
   - Update `<a-sky>` if background differs
   - Highlight the active scene in the menu

4. Styling:
   - Semi-transparent dark background
   - White text
   - Active scene highlighted
   - Collapses to just "Scenes" button when closed

**Done when:**
- [ ] Menu appears top-right over the A-Frame scene
- [ ] Clicking a scene name switches the 3D models without page reload
- [ ] Active scene is highlighted
- [ ] Menu is collapsible
- [ ] Works on mobile and desktop browsers

---

## Phase 3: visionOS Scene Menu (SwiftUI)

Add a scene switcher to `ImmersiveView.swift` — floating SwiftUI panel.

**What to do:**

1. Create `SceneIndex.swift` — loads and decodes `index.json` from the bundle:
   ```swift
   struct SceneIndexEntry: Codable {
       let id: String
       let label: String
       let file: String
   }

   struct SceneIndex: Codable {
       let defaultScene: String  // "default" key
       let scenes: [SceneIndexEntry]

       enum CodingKeys: String, CodingKey {
           case defaultScene = "default"
           case scenes
       }
   }
   ```

2. Create `SceneMenuView.swift` — floating ornament-style panel:
   ```swift
   struct SceneMenuView: View {
       let scenes: [SceneIndexEntry]
       @Binding var activeSceneID: String
       var onSelect: (SceneIndexEntry) -> Void

       var body: some View {
           VStack(alignment: .leading, spacing: 8) {
               Text("Scenes").font(.headline)
               ForEach(scenes, id: \.id) { scene in
                   Button(scene.label) {
                       onSelect(scene)
                   }
                   .fontWeight(scene.id == activeSceneID ? .bold : .regular)
               }
           }
           .padding()
           .glassBackgroundEffect()
       }
   }
   ```

3. Update `ImmersiveView.swift`:
   - Load `index.json` on appear
   - Show `SceneMenuView` as an `.ornament` attachment (top-right)
   - On scene select: clear existing entities, call `SceneLoader.loadFromBundle(filename:)` with the new scene file
   - Track active scene ID in `@State`

4. Update `SceneLoader.swift`:
   - `loadFromBundle(filename:)` already takes a filename parameter — just pass the scene file name without extension

5. Update `generate_scene.sh`:
   - Copy all scene files from `output/scenes/` into Xcode bundle
   - Copy `index.json` into Xcode bundle

**Done when:**
- [ ] Floating panel appears in the immersive view
- [ ] Shows list of scene names
- [ ] Tapping a scene name swaps the 3D models
- [ ] Active scene is visually highlighted
- [ ] Default scene loads on startup

---

## Phase 4: Pipeline Integration

Update the shell scripts to use the scene manager.

**What to do:**

1. Update `agents/generate_scene.sh`:
   ```bash
   # After agent writes output/scene.json:
   python agents/scene_manager.py add --prompt "$PROMPT" < output/scene.json

   # Copy all scenes + index to Xcode bundle
   cp output/scenes/*.json "$XCODE_RESOURCES/scenes/"
   ```

2. Update `agents/generate_all.sh`:
   - Register the "all models" scene as a single scene entry

3. Update `agents/generate_webxr_scene.sh`:
   - After generating, copy `output/scenes/` into `webXR/scenes/`

4. Backward compat:
   - `output/scene.json` still written (symlink or copy of latest scene)
   - Old scripts that read `scene.json` directly keep working

**Done when:**
- [ ] Each `generate_scene.sh` run adds a new scene to the index
- [ ] `generate_all.sh` creates one indexed scene
- [ ] All scenes are copied to both Xcode bundle and webXR/
- [ ] Old `output/scene.json` still works

---

## Phase 5: Polish

1. Scene deletion:
   ```bash
   python agents/scene_manager.py delete scene_002
   ```

2. Scene limit: keep max 20 scenes, auto-delete oldest (configurable)

3. Menu styling matches platform:
   - WebXR: semi-transparent dark overlay
   - visionOS: glass material ornament

4. Keyboard shortcut in WebXR: press `M` to toggle menu

**Done when:**
- [ ] Can delete scenes
- [ ] Scene limit works
- [ ] Menu looks polished on both platforms
- [ ] Keyboard shortcut works in WebXR

---

## Quick Reference

### Auto-naming rules

| Source | Label |
|---|---|
| User prompt | First ~40 chars of the prompt |
| `generate_all.sh` | "All models" |
| No prompt | "Scene {N}" |

### File locations

| File | Purpose |
|---|---|
| `output/scenes/index.json` | Scene list + default |
| `output/scenes/scene_NNN.json` | Individual scene data |
| `webXR/scenes/` | Copied for browser access |
| `VercelDeepmindHack/.../scenes/` | Copied into Xcode bundle |
| `agents/scene_manager.py` | Scene CRUD operations |

### New files to create

| File | Phase |
|---|---|
| `agents/scene_manager.py` | 1 |
| `SceneIndex.swift` | 3 |
| `SceneMenuView.swift` | 3 |

### Files to modify

| File | Phase | Change |
|---|---|---|
| `generators/generate_aframe.py` | 2 | Add menu overlay + JS scene switching |
| `ImmersiveView.swift` | 3 | Add ornament, scene switching logic |
| `agents/generate_scene.sh` | 4 | Call scene_manager.py, copy scenes/ |
| `agents/generate_all.sh` | 4 | Register as indexed scene |
| `agents/generate_webxr_scene.sh` | 4 | Copy scenes/ to webXR/ |
