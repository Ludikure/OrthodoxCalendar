/**
 * Orthodox Calendar API — Cloudflare Worker
 *
 * Serves calendar data from R2 bucket.
 *
 * Endpoints:
 *   GET /api/{locale}/{year}          → full year calendar JSON
 *   GET /api/{locale}/{year}/{month}  → single month (filtered from year)
 *   GET /api/years                    → list available years
 *   GET /api/health                   → health check
 *
 * Headers:
 *   Cache-Control: immutable (calendar data doesn't change once generated)
 *   CORS: allowed for all origins
 */

interface Env {
	CALENDAR_DATA: R2Bucket;
}

const VALID_LOCALES = new Set(["sr", "ru", "en"]);
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

async function handleListYears(env: Env): Promise<Response> {
	const list = await env.CALENDAR_DATA.list({ prefix: "calendar_sr_" });
	const years = list.objects
		.map((obj) => {
			const match = obj.key.match(/calendar_sr_(\d{4})\.json/);
			return match ? parseInt(match[1]) : null;
		})
		.filter((y): y is number => y !== null)
		.sort();

	return jsonResponse({ years });
}

async function handleGetYear(env: Env, locale: string, year: number): Promise<Response> {
	if (!VALID_LOCALES.has(locale)) {
		return errorResponse(`Invalid locale: ${locale}. Valid: sr, ru, en`, 400);
	}

	if (year < 2020 || year > 2050) {
		return errorResponse(`Year out of range: ${year}`, 400);
	}

	const key = `calendar_${locale}_${year}.json`;
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
