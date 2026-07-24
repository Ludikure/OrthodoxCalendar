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
 *   GET /api/{locale}/{year}/{month}  → single month (filtered from year)
 *   GET /api/years                    → list legacy years
 *   GET /api/config                   → app config (forced-update gate, dataRevision)
 *   GET /api/health                   → health check
 *
 * Headers:
 *   Cache-Control: immutable (calendar data doesn't change once generated)
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
const CACHE_HEADERS = {
	"Cache-Control": "public, max-age=86400, s-maxage=604800, immutable",
	"Content-Type": "application/json; charset=utf-8",
};

function corsHeaders(origin: string | null): Record<string, string> {
	return {
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "GET, OPTIONS",
		"Access-Control-Allow-Headers": "Content-Type",
	};
}

function jsonResponse(data: unknown, status = 200): Response {
	return new Response(JSON.stringify(data), {
		status,
		headers: { ...CACHE_HEADERS, ...corsHeaders(null) },
	});
}

function errorResponse(message: string, status: number): Response {
	return new Response(JSON.stringify({ error: message }), {
		status,
		headers: {
			"Content-Type": "application/json",
			...corsHeaders(null),
		},
	});
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		const path = url.pathname;

		// CORS preflight
		if (request.method === "OPTIONS") {
			return new Response(null, { status: 204, headers: corsHeaders(null) });
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
			return await handleGetTexts(env, v2TextsMatch[1]);
		}

		// /api/v2/{locale}/{year}
		const v2YearMatch = path.match(/^\/api\/v2\/(\w+)\/(\d{4})$/);
		if (v2YearMatch) {
			const [, locale, yearStr] = v2YearMatch;
			return await handleGetYear(env, locale, parseInt(yearStr), V2_PREFIX);
		}

		// /api/{locale}/{year}
		const yearMatch = path.match(/^\/api\/(\w+)\/(\d{4})$/);
		if (yearMatch) {
			const [, locale, yearStr] = yearMatch;
			return await handleGetYear(env, locale, parseInt(yearStr));
		}

		// /api/{locale}/{year}/{month}
		const monthMatch = path.match(/^\/api\/(\w+)\/(\d{4})\/(\d{1,2})$/);
		if (monthMatch) {
			const [, locale, yearStr, monthStr] = monthMatch;
			return await handleGetMonth(env, locale, parseInt(yearStr), parseInt(monthStr));
		}

		return errorResponse("Not found", 404);
	},
};

// App config (forced-update gate). Stored as config.json in R2 so the minimum
// required version can be changed without redeploying the worker or the app.
// Short cache so version bumps take effect quickly. Fail-open if absent.
async function handleConfig(env: Env): Promise<Response> {
	const headers = {
		"Cache-Control": "public, max-age=120",
		"Content-Type": "application/json; charset=utf-8",
		...corsHeaders(null),
	};
	const object = await env.CALENDAR_DATA.get("config.json");
	if (!object) {
		return new Response(JSON.stringify({ minVersion: "0.0.0" }), { status: 200, headers });
	}
	return new Response(await object.text(), { status: 200, headers });
}

async function handleListYears(env: Env, prefix = ""): Promise<Response> {
	// R2 list() pages at 1000 objects; one locale spans at most 76 keys, so a
	// single page suffices for both the legacy and v2 prefixes.
	const list = await env.CALENDAR_DATA.list({ prefix: `${prefix}calendar_sr_` });
	const years = list.objects
		.map((obj) => {
			const match = obj.key.match(/calendar_sr_(\d{4})\.json/);
			return match ? parseInt(match[1]) : null;
		})
		.filter((y): y is number => y !== null)
		.sort();

	return jsonResponse({ years });
}

async function handleGetTexts(env: Env, locale: string): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}. Valid: sr, ru, en, en_nc`, 400);
	}
	const object = await env.CALENDAR_DATA.get(`${V2_PREFIX}texts_${locale}.json`);
	if (!object) {
		return errorResponse(`No texts pool for ${locale}`, 404);
	}
	return new Response(await object.text(), {
		status: 200,
		headers: { ...CACHE_HEADERS, ...corsHeaders(null) },
	});
}

async function handleGetYear(env: Env, locale: string, year: number, prefix = ""): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}. Valid: sr, ru, en, en_nc`, 400);
	}

	const [minYear, maxYear] = prefix === V2_PREFIX ? [V2_MIN_YEAR, V2_MAX_YEAR] : [2020, 2050];
	if (year < minYear || year > maxYear) {
		return errorResponse(`Year out of range: ${year}`, 400);
	}

	const key = `${prefix}calendar_${locale}_${year}.json`;
	const object = await env.CALENDAR_DATA.get(key);

	if (!object) {
		return errorResponse(`No data for ${locale} ${year}`, 404);
	}

	const body = await object.text();
	return new Response(body, {
		status: 200,
		headers: { ...CACHE_HEADERS, ...corsHeaders(null) },
	});
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
