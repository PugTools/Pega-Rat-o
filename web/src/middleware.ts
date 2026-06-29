import { NextRequest, NextResponse } from "next/server";

const ADMIN_ROLES = new Set(["system_admin", "source_admin"]);
const MOCK_DEV_TOKEN = "mock-token-ongp";

export async function middleware(request: NextRequest) {
  const token = getBearerToken(request);
  if (!token) {
    return loginRedirect(request);
  }

  if (token === MOCK_DEV_TOKEN && process.env.NODE_ENV !== "production") {
    return NextResponse.next();
  }

  const payload = await verifyHs256Jwt(token);
  if (!payload) {
    return loginRedirect(request);
  }

  const roles = Array.isArray(payload.roles)
    ? payload.roles.map((role) => String(role))
    : [];
  const authorized = roles.some((role) => ADMIN_ROLES.has(role));
  if (!authorized) {
    return NextResponse.json(
      { detail: "Insufficient role for admin route." },
      { status: 403 },
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};

function getBearerToken(request: NextRequest): string | null {
  const authorization = request.headers.get("authorization");
  if (authorization?.toLowerCase().startsWith("bearer ")) {
    return authorization.slice(7).trim() || null;
  }

  for (const cookieName of ["ongp_token", "access_token", "token"]) {
    const cookieValue = request.cookies.get(cookieName)?.value;
    if (cookieValue) {
      return cookieValue;
    }
  }

  return null;
}

async function verifyHs256Jwt(token: string): Promise<Record<string, unknown> | null> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  const [encodedHeader, encodedPayload, encodedSignature] = parts;
  const header = decodeJsonSegment(encodedHeader);
  const payload = decodeJsonSegment(encodedPayload);
  if (!header || !payload || header.alg !== "HS256") {
    return null;
  }

  const secret =
    process.env.JWT_SECRET_KEY ||
    (process.env.NODE_ENV === "production" ? "" : "ongp-local-dev-secret-change-me");
  if (!secret || (process.env.NODE_ENV === "production" && secret === "ongp-local-dev-secret-change-me")) {
    return null;
  }
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const verified = await crypto.subtle.verify(
    "HMAC",
    key,
    base64UrlToBytes(encodedSignature),
    new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`),
  );
  if (!verified) {
    return null;
  }

  const exp = Number(payload.exp ?? 0);
  if (!Number.isFinite(exp) || exp <= Math.floor(Date.now() / 1000)) {
    return null;
  }

  return payload;
}

function decodeJsonSegment(segment: string): Record<string, unknown> | null {
  try {
    return JSON.parse(new TextDecoder().decode(base64UrlToBytes(segment))) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function base64UrlToBytes(value: string): Uint8Array {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function loginRedirect(request: NextRequest) {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}
