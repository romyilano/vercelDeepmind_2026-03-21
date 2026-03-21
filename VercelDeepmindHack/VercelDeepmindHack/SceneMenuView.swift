//
//  SceneMenuView.swift
//  VercelDeepmindHack
//
//  Floating ornament-style panel for switching between scenes.
//

import SwiftUI

struct SceneMenuView: View {
    let scenes: [SceneIndexEntry]
    @Binding var activeSceneID: String
    var onSelect: (SceneIndexEntry) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Scenes")
                .font(.headline)
                .foregroundStyle(.primary)

            ForEach(scenes) { scene in
                Button {
                    onSelect(scene)
                } label: {
                    HStack {
                        Text(scene.label)
                            .fontWeight(scene.id == activeSceneID ? .bold : .regular)
                        Spacer()
                        if scene.id == activeSceneID {
                            Image(systemName: "checkmark")
                                .font(.caption)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .frame(minWidth: 200)
        .glassBackgroundEffect()
    }
}
