//
//  ImmersiveView.swift
//  VercelDeepmindHack
//
//  Created by Romy Ilano on 3/21/26.
//

import SwiftUI
import RealityKit
import RealityKitContent

struct ImmersiveView: View {
    @Environment(AppModel.self) var appModel
    @State private var sceneIndex: SceneIndex?
    @State private var activeSceneID: String = ""
    @State private var sceneEntities: [Entity] = []
    @State private var rootEntity = Entity()

    var body: some View {
        RealityView { content in
            // Add the initial RealityKit content (skybox, ground, etc.)
            if let immersiveContentEntity = try? await Entity(named: "Immersive", in: realityKitContentBundle) {
                content.add(immersiveContentEntity)
            }

            content.add(rootEntity)

            // Load scene index and default scene
            if let index = SceneIndex.loadFromBundle() {
                sceneIndex = index
                let defaultID = index.defaultScene ?? index.scenes.first?.id ?? ""
                activeSceneID = defaultID

                if let entry = index.scenes.first(where: { $0.id == defaultID }) {
                    await loadScene(entry)
                }
            } else {
                // Fallback: load single scene.json
                if let entities = try? await SceneLoader.loadFromBundle() {
                    for entity in entities {
                        rootEntity.addChild(entity)
                    }
                    sceneEntities = entities
                }
            }
        }
        .ornament(attachmentAnchor: .scene(.topTrailing)) {
            if let index = sceneIndex, !index.scenes.isEmpty {
                SceneMenuView(
                    scenes: index.scenes,
                    activeSceneID: $activeSceneID
                ) { entry in
                    Task {
                        await loadScene(entry)
                    }
                }
            }
        }
    }

    @MainActor
    private func loadScene(_ entry: SceneIndexEntry) async {
        // Remove existing scene entities
        for entity in sceneEntities {
            entity.removeFromParent()
        }
        sceneEntities.removeAll()

        // Load the new scene file (strip .json extension for filename)
        let filename = entry.file.replacingOccurrences(of: ".json", with: "")
        if let entities = try? await SceneLoader.loadFromBundle(filename: filename) {
            for entity in entities {
                rootEntity.addChild(entity)
            }
            sceneEntities = entities
            activeSceneID = entry.id
        }
    }
}

#Preview(immersionStyle: .full) {
    ImmersiveView()
        .environment(AppModel())
}
