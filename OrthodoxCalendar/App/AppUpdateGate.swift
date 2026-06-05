import Foundation

/// Server-controlled minimum-version gate.
///
/// On launch the app fetches `/api/config`; if the installed version is below the
/// server's `minVersion`, the app shows a blocking update screen. The minimum is
/// controlled server-side (R2 `config.json`), so an update can be forced later by
/// changing one value — no new app release required.
///
/// Fail-open by design: any network/parse failure leaves `mustUpdate == false`,
/// so offline users of this offline-first app are never blocked.
@MainActor @Observable
final class AppUpdateGate {
    var mustUpdate = false
    var appStoreURL: URL?

    private let configURL = URL(string:
        "https://orthodox-calendar-api.ludikure.workers.dev/api/config")!

    struct Config: Decodable {
        let minVersion: String
        let appStoreUrl: String?
    }

    var installedVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
    }

    func check() async {
        guard let (data, response) = try? await URLSession.shared.data(from: configURL),
              let http = response as? HTTPURLResponse, http.statusCode == 200,
              let config = try? JSONDecoder().decode(Config.self, from: data)
        else {
            return  // fail-open: never block on a failed/edge-cached miss
        }
        if let s = config.appStoreUrl, let url = URL(string: s) {
            appStoreURL = url
        }
        if Self.isOlder(installedVersion, than: config.minVersion) {
            mustUpdate = true
        }
    }

    /// True if `version` is strictly older than `minimum` (dotted numeric compare,
    /// e.g. "1.3.0" < "1.4.0"). Non-numeric or missing components count as 0.
    static func isOlder(_ version: String, than minimum: String) -> Bool {
        let a = version.split(separator: ".").map { Int($0) ?? 0 }
        let b = minimum.split(separator: ".").map { Int($0) ?? 0 }
        for i in 0..<max(a.count, b.count) {
            let x = i < a.count ? a[i] : 0
            let y = i < b.count ? b[i] : 0
            if x != y { return x < y }
        }
        return false
    }
}
