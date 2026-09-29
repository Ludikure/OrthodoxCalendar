import XCTest
@testable import Orthodox_Calendar

/// A bundled year gives way to an archive copy only when the archive is newer
/// than the bundle, and a revision bump never leaves a stale copy in charge.
final class BundledDataTests: XCTestCase {

    func testBundleWinsWithoutANewerCopy() {
        XCTAssertEqual(BundledData.source(bundleRevision: 9, cachedRevision: nil), .bundle)
        XCTAssertEqual(BundledData.source(bundleRevision: 9, cachedRevision: 9), .bundle)
        // A copy downloaded before this app's newer bundle shipped.
        XCTAssertEqual(BundledData.source(bundleRevision: 10, cachedRevision: 9), .bundle)
        XCTAssertEqual(BundledData.source(bundleRevision: 10, cachedRevision: 10), .bundle)
    }

    func testNewerCopyWins() {
        XCTAssertEqual(BundledData.source(bundleRevision: 9, cachedRevision: 10), .cache)
    }

    func testDownloadOnlyWhenTheServerIsNewer() {
        // Offline or no config: never.
        XCTAssertFalse(BundledData.shouldDownload(bundleRevision: 9, serverRevision: nil, cachedRevision: nil))
        // Same or older archive than the bundle: never.
        XCTAssertFalse(BundledData.shouldDownload(bundleRevision: 9, serverRevision: 9, cachedRevision: nil))
        XCTAssertFalse(BundledData.shouldDownload(bundleRevision: 10, serverRevision: 9, cachedRevision: nil))
        // Newer archive: once.
        XCTAssertTrue(BundledData.shouldDownload(bundleRevision: 9, serverRevision: 10, cachedRevision: nil))
        XCTAssertFalse(BundledData.shouldDownload(bundleRevision: 9, serverRevision: 10, cachedRevision: 10))
        // Bumped again past the copy on disk: fetched again.
        XCTAssertTrue(BundledData.shouldDownload(bundleRevision: 9, serverRevision: 11, cachedRevision: 10))
    }

    func testCacheNameCarriesTheRevision() {
        let name = BundledData.cacheName("calendar_ru_2026", revision: 10)
        XCTAssertEqual(name, "calendar_ru_2026.r10")
        XCTAssertEqual(BundledData.revision(ofCacheName: name + ".json", key: "calendar_ru_2026"), 10)
        // Another locale's or year's copy, and a plain downloaded year, are not it.
        XCTAssertNil(BundledData.revision(ofCacheName: "calendar_ru_2026.json", key: "calendar_ru_2026"))
        XCTAssertNil(BundledData.revision(ofCacheName: "calendar_ru_2027.r10.json", key: "calendar_ru_2026"))
        XCTAssertNil(BundledData.revision(ofCacheName: "calendar_en_nc_2026.r10.json", key: "calendar_en_2026"))
    }

    func testBundleRevisionIsSet() {
        XCTAssertGreaterThanOrEqual(BundledData.revision, 9)
    }
}
