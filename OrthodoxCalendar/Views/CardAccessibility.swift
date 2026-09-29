import Foundation

/// Accessibility label builder for the expandable day-detail cards.
///
/// The cards set an explicit accessibility label, which replaces the combined
/// content of their children — without folding the text in here, an opened
/// biography or scripture passage was never announced by VoiceOver.
///
/// Callers pass the text only while the card is expanded. A collapsed card's
/// label stays short: a full biography is thousands of characters, so reading
/// it unprompted buries the subject the listener is trying to recognise and
/// contradicts the hint that offers to expand it.
enum CardAccessibility {
    /// `"type: subject"`, plus `text` when the card is open.
    static func summary(localizedType: String, subject: String, text: String?) -> String {
        guard let text, !text.isEmpty else { return "\(localizedType): \(subject)" }
        return "\(localizedType): \(subject). \(text)"
    }
}
