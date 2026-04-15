import UIKit

@MainActor
enum Haptics {
    private static let lightGen = UIImpactFeedbackGenerator(style: .light)
    private static let mediumGen = UIImpactFeedbackGenerator(style: .medium)
    private static let selectionGen = UISelectionFeedbackGenerator()

    static func prepare() {
        lightGen.prepare()
        mediumGen.prepare()
        selectionGen.prepare()
    }

    static func light() {
        lightGen.impactOccurred()
        lightGen.prepare()
    }

    static func medium() {
        mediumGen.impactOccurred()
        mediumGen.prepare()
    }

    static func selection() {
        selectionGen.selectionChanged()
        selectionGen.prepare()
    }
}
