/**
 * Next.js config.
 *
 * The ``rewrites()`` block proxies ``/api/*`` to the API container so that
 * direct access to the web container (e.g. ``http://<host>:3000``) keeps
 * working when callers reach for the API. When traffic is routed through
 * the bundled nginx (``http://<host>:8080``), nginx terminates ``/api/``
 * itself and these rewrites never fire. Either way the browser stays on
 * a single origin, which is what the OAuth login flow needs (a 302 from
 * the API to ``/login`` must resolve against the web origin).
 *
 * ``INTERNAL_API_BASE_URL`` is the in-network address of the API
 * service (e.g. ``http://api:8000`` in Docker Compose). When not set we
 * fall back to ``http://localhost:8000`` for ``next dev`` outside Docker.
 */
const API_TARGET = (
  process.env.INTERNAL_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_TARGET}/api/:path*` }
    ];
  }
};

export default nextConfig;
