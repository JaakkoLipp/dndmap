"use client";

import { AlertTriangle, ChevronDown, Github, MessageCircle, Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { useAuth } from "../../components/providers/AuthProvider";
import { api } from "../../lib/api";

type ProviderId = "discord" | "google" | "github";

const OTHER_PROVIDERS: { id: ProviderId; label: string; Icon: typeof Github }[] = [
  { id: "google", label: "Continue with Google", Icon: Search },
  { id: "github", label: "Continue with GitHub", Icon: Github }
];

const ERROR_COPY: Record<string, string> = {
  invalid_state: "Your sign-in link expired. Please try again.",
  missing_state_or_code: "The sign-in link was incomplete. Please try again.",
  provider_not_configured:
    "OAuth credentials for this provider are not configured on the server. Ask your admin to set OAUTH_DISCORD_CLIENT_ID / OAUTH_DISCORD_CLIENT_SECRET (or the matching variables for Google / GitHub).",
  session_secret_missing:
    "SESSION_SECRET is not configured on the server. Sign-in cannot proceed until it is set.",
  unknown_provider: "Unknown sign-in provider.",
  no_access_token: "The provider did not return an access token.",
  provider_error: "The provider rejected the sign-in. Please try again.",
  jwt_not_configured: "Server is missing a JWT secret. Contact your admin."
};

function describeError(error: string | null): string | null {
  if (!error) return null;
  if (error.startsWith("provider:")) {
    return `The provider returned an error: ${error.slice("provider:".length)}.`;
  }
  return ERROR_COPY[error] ?? `Sign-in failed (${error}).`;
}

function LoginInner() {
  const params = useSearchParams();
  const { user, isLoading } = useAuth();
  const [showOther, setShowOther] = useState(false);

  const next = params.get("next") ?? undefined;
  const error = describeError(params.get("error"));
  const providerLabel = params.get("provider");

  return (
    <main className="app-shell centered-shell">
      <section className="auth-panel" style={{ maxWidth: 420 }}>
        <div className="brand-lockup">
          <MessageCircle size={28} />
          <div>
            <h1>Campaign Map Forge</h1>
            <p>Sign in to manage private campaign maps and invites.</p>
          </div>
        </div>

        {error ? (
          <div
            className="notice error-notice"
            role="alert"
            style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}
          >
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <strong>Sign-in failed{providerLabel ? ` (${providerLabel})` : ""}.</strong>
              <p style={{ margin: "0.25rem 0 0" }}>{error}</p>
            </div>
          </div>
        ) : null}

        <div className="auth-actions" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <a
            className="wide-action"
            href={api.auth.loginUrl("discord", { next })}
            style={{
              background: "#5865f2",
              color: "white",
              border: "1px solid #4752c4",
              fontWeight: 600
            }}
          >
            <MessageCircle size={18} />
            <span>Continue with Discord</span>
          </a>

          <button
            aria-expanded={showOther}
            className="subtle-button"
            onClick={() => setShowOther((v) => !v)}
            style={{
              alignSelf: "flex-start",
              fontSize: "0.8125rem",
              gap: "0.25rem"
            }}
            type="button"
          >
            <ChevronDown
              size={14}
              style={{
                transition: "transform 150ms",
                transform: showOther ? "rotate(180deg)" : "none"
              }}
            />
            <span>{showOther ? "Hide other options" : "More sign-in options"}</span>
          </button>

          {showOther
            ? OTHER_PROVIDERS.map(({ id, label, Icon }) => (
                <a
                  className="wide-action"
                  href={api.auth.loginUrl(id, { next })}
                  key={id}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </a>
              ))
            : null}
        </div>

        {next ? (
          <p className="muted-copy">
            You&apos;ll be sent to <code>{next}</code> after signing in.
          </p>
        ) : null}

        {isLoading ? <p className="muted-copy">Checking session…</p> : null}
        {user ? (
          <p className="muted-copy">
            Signed in as {user.display_name}.{" "}
            <Link href={next ?? "/campaigns"}>Continue</Link>
          </p>
        ) : null}
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="app-shell centered-shell">Loading…</main>}>
      <LoginInner />
    </Suspense>
  );
}
