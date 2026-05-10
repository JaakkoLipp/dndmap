import { NextResponse, type NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/campaigns", "/invite"];

export function middleware(request: NextRequest) {
  const authEnabled = process.env.AUTH_ENABLED === "true";
  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    request.nextUrl.pathname.startsWith(prefix)
  );

  if (!authEnabled || !isProtected) {
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
