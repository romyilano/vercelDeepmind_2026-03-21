//
//  SceneIndex.swift
//  VercelDeepmindHack
//
//  Loads and decodes the scene index (index.json) from the app bundle.
//

import Foundation

struct SceneIndexEntry: Codable, Identifiable {
    let id: String
    let label: String
    let file: String
}

struct SceneIndex: Codable {
    let defaultScene: String?
    let scenes: [SceneIndexEntry]

    enum CodingKeys: String, CodingKey {
        case defaultScene = "default"
        case scenes
    }

    /// Load the scene index from the app bundle.
    static func loadFromBundle() -> SceneIndex? {
        guard let url = Bundle.main.url(forResource: "index", withExtension: "json", subdirectory: "scenes") else {
            // Try without subdirectory (flat bundle)
            guard let url = Bundle.main.url(forResource: "index", withExtension: "json") else {
                print("SceneIndex: index.json not found in bundle")
                return nil
            }
            return decode(from: url)
        }
        return decode(from: url)
    }

    private static func decode(from url: URL) -> SceneIndex? {
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(SceneIndex.self, from: data)
        } catch {
            print("SceneIndex: failed to decode index.json: \(error)")
            return nil
        }
    }
}
