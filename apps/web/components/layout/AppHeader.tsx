"use client";

import { ChevronDown, Compass, LogIn, LogOut } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

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

function ProfileMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  if (!user) return null;

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        className="subtle-button"
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.5rem",
          paddingLeft: "0.25rem"
        }}
        type="button"
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
        <ChevronDown size={14} />
      </button>

      {open ? (
        <div
          role="menu"
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 0.25rem)",
            minWidth: 220,
            background: "rgba(15, 23, 42, 0.95)",
            border: "1px solid rgba(148, 163, 184, 0.25)",
            borderRadius: "0.5rem",
            padding: "0.5rem",
            boxShadow: "0 12px 32px rgba(0,0,0,0.4)",
            zIndex: 100,
            color: "#f8fafc"
          }}
        >
          <div style={{ padding: "0.375rem 0.5rem 0.5rem" }}>
            <div style={{ fontWeight: 600 }}>{user.display_name}</div>
            <div style={{ fontSize: "0.75rem", opacity: 0.7 }}>Signed in</div>
          </div>
          <div
            style={{
              height: 1,
              background: "rgba(148, 163, 184, 0.2)",
              margin: "0.25rem 0"
            }}
          />
          <button
            className="subtle-button"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            role="menuitem"
            style={{
              width: "100%",
              justifyContent: "flex-start",
              gap: "0.5rem"
            }}
            type="button"
          >
            <LogOut size={14} />
            <span>Sign out</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function AppHeader({ leading, trailing, role }: AppHeaderProps) {
  const { user, isLoading } = useAuth();

  return (
    <header className="app-header">
      {leading ?? (
        <Link className="app-brand" href="/campaigns">
          <Compass size={24} />
          <span>Campaign Map Forge</span>
        </Link>
      )}

      <nav
        className="app-nav"
        style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
      >
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
          <ProfileMenu />
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
