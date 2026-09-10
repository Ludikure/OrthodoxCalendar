/**
 * Orthodox Calendar API — Cloudflare Worker
 *
 * Serves calendar data from R2 bucket.
 *
 * Endpoints:
 *   GET /api/v2/{locale}/{year}       → deduplicated year JSON (2024-2099; text
 *                                       refs resolve against bundled texts pools)
 *   GET /api/v2/years                 → years available in the v2 archive
 *   GET /api/v2/texts/{locale}        → full texts pool for a locale
 *   GET /api/{locale}/{year}          → legacy fat year JSON (pre-1.4.0 clients)
 *   GET /api/{locale}/{year}/{month}  → single month, from the legacy fat object
 *                                       only; the v2 archive has no month endpoint
 *                                       because clients cache whole years
 *   GET /api/years                    → list legacy years
 *   GET /api/config                   → app config (forced-update gate, dataRevision)
 *   GET /api/health                   → health check
 *
 * Headers:
 *   Cache-Control: short max-age + stale-while-revalidate, validated by ETag.
 *     Data IS regenerated in place (see dataRevision), so it is not immutable.
 *   CORS: allowed for all origins
 */

interface Env {
	CALENDAR_DATA: R2Bucket;
}

const VALID_LOCALES = new Set(["sr", "ru", "en", "en_nc"]);

// v2 deduplicated archive spans 2024-2099 (Julian+13 date math holds to 2099).
const V2_PREFIX = "v2/";
const V2_MIN_YEAR = 2024;
const V2_MAX_YEAR = 2099;
// Year files and pools are regenerated in place, so they are emphatically not
// `immutable`, and a week of s-maxage meant the CDN kept serving superseded data
// for a week after a fix — exactly when it should be gone. Revalidation is cheap
// against an ETag, and stale-while-revalidate keeps it off the critical path.
const CACHE_HEADERS = {
	"Cache-Control": "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400",
	"Content-Type": "application/json; charset=utf-8",
};

/** Serves an R2 object with its ETag, answering a matching If-None-Match with 304. */
function objectResponse(request: Request, object: R2ObjectBody): Response {
	const etag = object.httpEtag;
	const headers = { ...CACHE_HEADERS, ...corsHeaders(), ETag: etag };
	if (request.headers.get("If-None-Match") === etag) {
		return new Response(null, { status: 304, headers });
	}
	return new Response(object.body, { status: 200, headers });
}

function corsHeaders(): Record<string, string> {
	return {
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "GET, OPTIONS",
		"Access-Control-Allow-Headers": "Content-Type",
	};
}

function jsonResponse(data: unknown, status = 200): Response {
	return new Response(JSON.stringify(data), {
		status,
		headers: { ...CACHE_HEADERS, ...corsHeaders() },
	});
}

function errorResponse(message: string, status: number): Response {
	return new Response(JSON.stringify({ error: message }), {
		status,
		headers: {
			"Content-Type": "application/json",
			...corsHeaders(),
		},
	});
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		// One bad object is enough to throw inside a handler (handleGetMonth parses
		// JSON, R2 can fail): an unhandled rejection returns Cloudflare's HTML 500
		// without CORS or JSON, and the app maps any non-200 to "offline", so the
		// user is told to check their connection. Answer 5xx as JSON instead.
		try {
			return await route(request, env);
		} catch (e) {
			const message = e instanceof Error ? e.message : String(e);
			console.error("unhandled error", request.url, message);
			return errorResponse(`Internal error: ${message}`.slice(0, 300), 500);
		}
	},
};

async function route(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		const path = url.pathname;

		// CORS preflight
		if (request.method === "OPTIONS") {
			return new Response(null, { status: 204, headers: corsHeaders() });
		}

		if (request.method !== "GET") {
			return errorResponse("Method not allowed", 405);
		}

		// Routes
		if (path === "/api/health") {
			return jsonResponse({ status: "ok", timestamp: new Date().toISOString() });
		}

		if (path === "/api/years") {
			return await handleListYears(env);
		}

		if (path === "/api/config") {
			return await handleConfig(env);
		}

		// v2 archive: deduplicated year files under the v2/ key prefix.
		// Text refs resolve against the texts_<locale> pools the apps bundle
		// (also served at /api/v2/texts/{locale}). Legacy fat objects for
		// pre-1.4.0 clients stay at the unprefixed keys.
		if (path === "/api/v2/years") {
			return await handleListYears(env, V2_PREFIX);
		}

		const v2TextsMatch = path.match(/^\/api\/v2\/texts\/(\w+)$/);
		if (v2TextsMatch) {
			return await handleGetTexts(request, env, v2TextsMatch[1]);
		}

		// /api/v2/{locale}/{year}
		const v2YearMatch = path.match(/^\/api\/v2\/(\w+)\/(\d{4})$/);
		if (v2YearMatch) {
			const [, locale, yearStr] = v2YearMatch;
			return await handleGetYear(request, env, locale, parseInt(yearStr), V2_PREFIX);
		}

		// /api/{locale}/{year}
		const yearMatch = path.match(/^\/api\/(\w+)\/(\d{4})$/);
		if (yearMatch) {
			const [, locale, yearStr] = yearMatch;
			return await handleGetYear(request, env, locale, parseInt(yearStr));
		}

		// /api/{locale}/{year}/{month}
		const monthMatch = path.match(/^\/api\/(\w+)\/(\d{4})\/(\d{1,2})$/);
		if (monthMatch) {
			const [, locale, yearStr, monthStr] = monthMatch;
			return await handleGetMonth(env, locale, parseInt(yearStr), parseInt(monthStr));
		}

		return errorResponse("Not found", 404);
}

// App config (forced-update gate). Stored as config.json in R2 so the minimum
// required version can be changed without redeploying the worker or the app.
// Short cache so version bumps take effect quickly. Fail-open if absent.
async function handleConfig(env: Env): Promise<Response> {
	const headers = {
		"Cache-Control": "public, max-age=120",
		"Content-Type": "application/json; charset=utf-8",
		...corsHeaders(),
	};
	const object = await env.CALENDAR_DATA.get("config.json");
	if (!object) {
		return new Response(JSON.stringify({ minVersion: "0.0.0" }), { status: 200, headers });
	}
	return new Response(await object.text(), { status: 200, headers });
}

async function handleListYears(env: Env, prefix = ""): Promise<Response> {
	// R2 list() pages at 1000 objects; four locales span at most 304 keys, so a
	// single page suffices for both the legacy and v2 prefixes. Deriving the list
	// from sr alone meant one missing sr object hid that year from every locale.
	const list = await env.CALENDAR_DATA.list({ prefix: `${prefix}calendar_` });
	const years = [
		...new Set(
			list.objects
				.map((obj) => obj.key.match(/calendar_[a-z_]+_(\d{4})\.json$/))
				.filter((m): m is RegExpMatchArray => m !== null)
				.map((m) => parseInt(m[1]))
		),
	].sort((a, b) => a - b);

	return jsonResponse({ years });
}

async function handleGetTexts(request: Request, env: Env, locale: string): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}. Valid: sr, ru, en, en_nc`, 400);
	}
	// en and en_nc show the same bios and scripture text and share one pool.
	const pool = locale === 'en_nc' ? 'en' : locale;
	const object = await env.CALENDAR_DATA.get(`${V2_PREFIX}texts_${pool}.json`);
	if (!object) {
		return errorResponse(`No texts pool for ${locale}`, 404);
	}
	return objectResponse(request, object);
}

async function handleGetYear(request: Request, env: Env, locale: string, year: number, prefix = ""): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}. Valid: sr, ru, en, en_nc`, 400);
	}

	// Legacy fat objects only ever covered the bundled window; the v2 archive is
	// the one that spans 2024-2099.
	const [minYear, maxYear] = prefix === V2_PREFIX ? [V2_MIN_YEAR, V2_MAX_YEAR] : [2024, 2030];
	if (year < minYear || year > maxYear) {
		return errorResponse(`Year out of range: ${year}`, 400);
	}

	const key = `${prefix}calendar_${locale}_${year}.json`;
	const object = await env.CALENDAR_DATA.get(key);

	if (!object) {
		return errorResponse(`No data for ${locale} ${year}`, 404);
	}

	return objectResponse(request, object);
}

async function handleGetMonth(
	env: Env,
	locale: string,
	year: number,
	month: number
): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}`, 400);
	}

	if (month < 1 || month > 12) {
		return errorResponse(`Invalid month: ${month}`, 400);
	}

	const key = `calendar_${locale}_${year}.json`;
	const object = await env.CALENDAR_DATA.get(key);

	if (!object) {
		return errorResponse(`No data for ${locale} ${year}`, 404);
	}

	const data = await object.json<{ year: number; locale: string; days: Record<string, unknown> }>();
	const monthPrefix = month.toString().padStart(2, "0") + "-";

	const filteredDays: Record<string, unknown> = {};
	for (const [dayKey, dayData] of Object.entries(data.days)) {
		if (dayKey.startsWith(monthPrefix)) {
			filteredDays[dayKey] = dayData;
		}
	}

	return jsonResponse({
		year: data.year,
		locale: data.locale,
		month,
		days: filteredDays,
	});
}
