"use client";

import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, Github, MessageCircle, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { useAuth } from "../../components/providers/AuthProvider";
import { api, ApiError, queryKeys } from "../../lib/api";

type ProviderId = "discord" | "google" | "github";

const OTHER_PROVIDERS: { id: ProviderId; label: string; Icon: typeof Github }[] = [
  { id: "google", label: "Continue with Google", Icon: Search },
  { id: "github", label: "Continue with GitHub", Icon: Github }
];

const OAUTH_ERROR_COPY: Record<string, string> = {
  invalid_state: "Your sign-in link expired. Please try again.",
  missing_state_or_code: "The sign-in link was incomplete. Please try again.",
  provider_not_configured:
    "OAuth credentials for this provider are not configured on the server.",
  session_secret_missing:
    "SESSION_SECRET is not configured on the server. Contact your admin.",
  unknown_provider: "Unknown sign-in provider.",
  no_access_token: "The provider did not return an access token.",
  provider_error: "The provider rejected the sign-in. Please try again.",
  jwt_not_configured: "Server is missing a JWT secret. Contact your admin.",
  database_unavailable:
    "Sign-in succeeded with the provider, but the database is unreachable so we can't store your account. Contact your admin."
};

function describeOAuthError(error: string | null): string | null {
  if (!error) return null;
  if (error.startsWith("provider:")) {
    return `The provider returned an error: ${error.slice("provider:".length)}.`;
  }
  return OAUTH_ERROR_COPY[error] ?? `Sign-in failed (${error}).`;
}

function LoginInner() {
  const params = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading } = useAuth();
  const [username, setUsername] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showOther, setShowOther] = useState(false);

  const next = params.get("next") ?? undefined;
  const oauthError = describeOAuthError(params.get("error"));
  const providerLabel = params.get("provider");
  const error = localError ?? oauthError;

  async function handleLocalLogin(e: FormEvent) {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) return;
    setLocalError(null);
    setIsPending(true);
    try {
      await api.auth.localLogin(trimmed);
      await queryClient.invalidateQueries({ queryKey: queryKeys.authMe });
      const dest = next ?? "/campaigns";
      const sep = dest.includes("?") ? "&" : "?";
      router.push(`${dest}${sep}welcome=1`);
    } catch (err) {
      setLocalError(
        err instanceof ApiError ? err.detail : "Sign-in failed. Please try again."
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <main className="app-shell centered-shell">
      <section className="auth-panel" style={{ maxWidth: 420 }}>
        <div className="brand-lockup">
          <MessageCircle size={28} />
          <div>
            <h1>Campaign Map Forge</h1>
            <p>Enter a username to sign in — new usernames create an account automatically.</p>
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
              <strong>
                Sign-in failed{providerLabel && !localError ? ` (${providerLabel})` : ""}.
              </strong>
              <p style={{ margin: "0.25rem 0 0" }}>{error}</p>
            </div>
          </div>
        ) : null}

        <form className="properties-form" onSubmit={handleLocalLogin}>
          <input
            autoComplete="username"
            autoFocus
            disabled={isPending}
            maxLength={32}
            minLength={2}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Choose a username"
            required
            type="text"
            value={username}
          />
          <button
            className="wide-action"
            disabled={isPending || !username.trim()}
            style={{ border: "none" }}
            type="submit"
          >
            {isPending ? "Signing in…" : "Continue"}
          </button>
        </form>

        <div
          style={{
            alignItems: "center",
            color: "var(--muted)",
            display: "flex",
            fontSize: "0.8125rem",
            gap: "10px"
          }}
        >
          <div style={{ background: "var(--border)", flex: 1, height: 1 }} />
          <span>or continue with</span>
          <div style={{ background: "var(--border)", flex: 1, height: 1 }} />
        </div>

        <div className="auth-actions">
          <a
            className="wide-action"
            href={api.auth.loginUrl("discord", { next })}
            style={{
              background: "#5865f2",
              border: "1px solid #4752c4",
              color: "white",
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
            style={{ alignSelf: "flex-start", fontSize: "0.8125rem", gap: "0.25rem" }}
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
