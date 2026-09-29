import XCTest
@testable import Orthodox_Calendar

/// The forced-update gate is the one place where a wrong comparison either
/// bricks a working app behind an update screen or lets an incompatible client
/// keep running. String comparison would order "1.10.0" below "1.9.0".
@MainActor
final class AppUpdateGateTests: XCTestCase {

    func testDottedNumericCompare() {
        XCTAssertTrue(AppUpdateGate.isOlder("1.3.0", than: "1.4.0"))
        XCTAssertFalse(AppUpdateGate.isOlder("1.4.0", than: "1.4.0"))
        XCTAssertFalse(AppUpdateGate.isOlder("1.5.0", than: "1.4.0"))
        // The lexicographic trap: 1.10 is newer than 1.9, not older.
        XCTAssertFalse(AppUpdateGate.isOlder("1.10.0", than: "1.9.0"))
        XCTAssertTrue(AppUpdateGate.isOlder("1.9.0", than: "1.10.0"))
    }

    func testMissingComponentsCountAsZero() {
        XCTAssertFalse(AppUpdateGate.isOlder("1.4", than: "1.4.0"))
        XCTAssertFalse(AppUpdateGate.isOlder("1.4.0.0", than: "1.4.0"))
        XCTAssertTrue(AppUpdateGate.isOlder("1.4.0", than: "1.4.1"))
        XCTAssertTrue(AppUpdateGate.isOlder("1", than: "1.2.0"))
    }

    func testGarbageIsNotOlderThanARealMinimum() {
        // A version we cannot parse must not lock the user out of the app. An
        // empty CFBundleShortVersionString used to read as all-zeroes and gate
        // a working app behind the update screen; "1.4.beta" used to compare
        // lexically against a numeric minimum.
        XCTAssertFalse(AppUpdateGate.isOlder("beta", than: "1.4.0"))
        XCTAssertFalse(AppUpdateGate.isOlder("1.4.beta", than: "1.4.0"))
        XCTAssertFalse(AppUpdateGate.isOlder("", than: "1.4.0"))
        // A malformed minimum from the server disables the gate rather than
        // gating everyone.
        XCTAssertFalse(AppUpdateGate.isOlder("1.3.0", than: "1.4.0-rc1"))
        XCTAssertFalse(AppUpdateGate.isOlder("1.3.0", than: ""))
    }
}
