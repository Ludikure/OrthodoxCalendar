import UIKit

enum Haptics {
    nonisolated(unsafe) private static var _light: UIImpactFeedbackGenerator?
    nonisolated(unsafe) private static var _medium: UIImpactFeedbackGenerator?
    nonisolated(unsafe) private static var _selection: UISelectionFeedbackGenerator?

    @MainActor static func prepare() {
        _light = UIImpactFeedbackGenerator(style: .light)
        _medium = UIImpactFeedbackGenerator(style: .medium)
        _selection = UISelectionFeedbackGenerator()
        _light?.prepare()
        _medium?.prepare()
        _selection?.prepare()
    }

    static func light() {
        DispatchQueue.main.async {
            if _light == nil { _light = UIImpactFeedbackGenerator(style: .light) }
            _light?.impactOccurred()
        }
    }

    static func medium() {
        DispatchQueue.main.async {
            if _medium == nil { _medium = UIImpactFeedbackGenerator(style: .medium) }
            _medium?.impactOccurred()
        }
    }

    static func selection() {
        DispatchQueue.main.async {
            if _selection == nil { _selection = UISelectionFeedbackGenerator() }
            _selection?.selectionChanged()
        }
    }
}
