import { NextResponse, type NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/campaigns", "/invite"];

/**
 * Whether the backend has auth turned on.
 *
 * Read from ``NEXT_PUBLIC_AUTH_ENABLED`` so the value is inlined at
 * build time and works in the Edge runtime (regular ``process.env``
 * values aren't reliably available there). The plain
 * ``AUTH_ENABLED`` env var is kept as a fallback for Node-runtime
 * deployments and for ``next dev`` where ``.env`` is loaded into
 * ``process.env`` directly. Treat any value other than the literal
 * string ``"true"`` as disabled — and remember this gate is a UX
 * hint only: the real authorization is enforced by the API.
 */
function isAuthEnabled(): boolean {
  const value =
    process.env.NEXT_PUBLIC_AUTH_ENABLED ?? process.env.AUTH_ENABLED;
  return value === "true";
}

export function middleware(request: NextRequest) {
  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    request.nextUrl.pathname.startsWith(prefix)
  );

  if (!isAuthEnabled() || !isProtected) {
    return NextResponse.next();
  }

  if (request.cookies.has("access_token")) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/campaigns/:path*", "/invite/:path*"]
};
