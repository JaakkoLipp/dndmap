"use client";

import { Compass, LogIn } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { useAuth } from "../providers/AuthProvider";
import { ROLE_BADGE_COLOR, ROLE_LABEL, type Role } from "../../lib/roles";

type AppHeaderProps = {
  leading?: ReactNode;
  trailing?: ReactNode;
  role?: Role;
};

function initials(name: string | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function AppHeader({ leading, trailing, role }: AppHeaderProps) {
  const { user, isLoading, logout } = useAuth();

  return (
    <header className="app-header">
      {leading ?? (
        <Link className="app-brand" href="/campaigns">
          <Compass size={24} />
          <span>Campaign Map Forge</span>
        </Link>
      )}

      <nav className="app-nav" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {trailing}

        {role ? (
          <span
            aria-label={`Role: ${ROLE_LABEL[role]}`}
            style={{
              padding: "0.125rem 0.5rem",
              borderRadius: "999px",
              background: ROLE_BADGE_COLOR[role],
              color: "white",
              fontSize: "0.75rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
              textTransform: "uppercase"
            }}
          >
            {ROLE_LABEL[role]}
          </span>
        ) : null}

        {isLoading ? <span className="muted-copy">…</span> : null}

        {user ? (
          <>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem"
              }}
              title={user.display_name}
            >
              {user.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  alt=""
                  height={28}
                  src={user.avatar_url}
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    objectFit: "cover"
                  }}
                  width={28}
                />
              ) : (
                <span
                  aria-hidden
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "rgba(148, 163, 184, 0.25)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "0.75rem",
                    fontWeight: 600
                  }}
                >
                  {initials(user.display_name)}
                </span>
              )}
              <span>{user.display_name}</span>
            </span>
            <button
              className="subtle-button"
              onClick={() => void logout()}
              type="button"
            >
              Logout
            </button>
          </>
        ) : !isLoading ? (
          <Link className="subtle-button" href="/login">
            <LogIn size={16} />
            <span>Login</span>
          </Link>
        ) : null}
      </nav>
    </header>
  );
}
