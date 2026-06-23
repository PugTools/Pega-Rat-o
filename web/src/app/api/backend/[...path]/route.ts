const rawInternalApiBaseUrl =
  process.env.INTERNAL_API_BASE_URL ??
  absoluteUrlOrUndefined(process.env.NEXT_PUBLIC_API_BASE_URL) ??
  "http://127.0.0.1:8000/api/v1";

const INTERNAL_API_BASE_URL = normalizeApiBaseUrl(rawInternalApiBaseUrl);
const DEFAULT_AUTH_HEADER = "Bearer mock-token-ongp";

type RouteContext = {
  params: Promise<{ path?: string[] }> | { path?: string[] };
};

export async function GET(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return proxyToBackend(request, context);
}

async function proxyToBackend(request: Request, context: RouteContext) {
  const params = await context.params;
  const path = (params.path ?? []).map(encodeURIComponent).join("/");
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(`${INTERNAL_API_BASE_URL}/${path}`);
  targetUrl.search = incomingUrl.search;

  const headers = forwardedHeaders(request.headers);
  if (!headers.has("authorization")) {
    headers.set("authorization", DEFAULT_AUTH_HEADER);
  }

  const response = await fetch(targetUrl.toString(), {
    method: request.method,
    headers,
    body: hasRequestBody(request.method) ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

function normalizeApiBaseUrl(value: string) {
  const trimmed = value.replace(/\/$/, "");
  if (trimmed.endsWith("/api/v1")) {
    return trimmed;
  }
  return `${trimmed}/api/v1`;
}

function absoluteUrlOrUndefined(value: string | undefined) {
  if (!value) {
    return undefined;
  }
  return value.startsWith("http://") || value.startsWith("https://")
    ? value
    : undefined;
}

function forwardedHeaders(source: Headers) {
  const blockedHeaders = new Set([
    "accept-encoding",
    "connection",
    "content-length",
    "host",
  ]);
  const headers = new Headers();
  source.forEach((value, key) => {
    if (!blockedHeaders.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  return headers;
}

function hasRequestBody(method: string) {
  return !["GET", "HEAD"].includes(method.toUpperCase());
}
