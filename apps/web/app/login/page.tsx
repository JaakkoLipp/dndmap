"use client";

import { Github, LogIn, MessageCircle, Search } from "lucide-react";
import Link from "next/link";

import { api } from "../../lib/api";
import { useAuth } from "../../components/providers/AuthProvider";

const PROVIDERS = [
  { id: "discord", label: "Continue with Discord", icon: MessageCircle },
  { id: "google", label: "Continue with Google", icon: Search },
  { id: "github", label: "Continue with GitHub", icon: Github }
] as const;

export default function LoginPage() {
  const { user, isLoading } = useAuth();

  return (
    <main className="app-shell centered-shell">
      <section className="auth-panel">
        <div className="brand-lockup">
          <LogIn size={28} />
          <div>
            <h1>Campaign Map Forge</h1>
            <p>Sign in to manage private campaign maps and invites.</p>
          </div>
        </div>

        <div className="auth-actions">
          {PROVIDERS.map(({ id, label, icon: Icon }) => (
            <a className="wide-action" href={api.auth.loginUrl(id)} key={id}>
              <Icon size={18} />
              <span>{label}</span>
            </a>
          ))}
        </div>

        {isLoading ? <p className="muted-copy">Checking session…</p> : null}
        {user ? (
          <p className="muted-copy">
            Signed in as {user.display_name}.{" "}
            <Link href="/campaigns">Open campaigns</Link>
          </p>
        ) : null}
      </section>
    </main>
  );
}
