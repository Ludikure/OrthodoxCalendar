import UIKit

enum Haptics {
    static func light() {
        Task { @MainActor in
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        }
    }

    static func medium() {
        Task { @MainActor in
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        }
    }

    static func selection() {
        Task { @MainActor in
            UISelectionFeedbackGenerator().selectionChanged()
        }
    }
}
