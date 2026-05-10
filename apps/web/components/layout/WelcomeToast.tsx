"use client";

import { CheckCircle2, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "../providers/AuthProvider";

/**
 * Shows a brief "Welcome back, $name" toast after a successful OAuth login.
 * The backend appends ``?welcome=1`` to the post-callback redirect; this
 * component reads the flag, shows the toast for a few seconds, and rewrites
 * the URL so a refresh doesn't replay the toast.
 */
export function WelcomeToast() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, isLoading } = useAuth();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (params.get("welcome") !== "1") return;
    if (!user) return;

    setVisible(true);
    const dismissTimer = setTimeout(() => setVisible(false), 4000);

    const url = new URL(window.location.href);
    url.searchParams.delete("welcome");
    router.replace(url.pathname + (url.search ? `?${url.searchParams}` : ""));

    return () => clearTimeout(dismissTimer);
  }, [isLoading, params, router, user]);

  if (!visible || !user) return null;

  return (
    <div
      aria-live="polite"
      role="status"
      style={{
        position: "fixed",
        bottom: "1.5rem",
        left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(16, 185, 129, 0.95)",
        color: "white",
        padding: "0.625rem 0.875rem",
        borderRadius: "0.5rem",
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        boxShadow: "0 12px 32px rgba(0,0,0,0.3)",
        zIndex: 200,
        fontSize: "0.875rem"
      }}
    >
      <CheckCircle2 size={18} />
      <span>
        Welcome back, <strong>{user.display_name}</strong>
      </span>
      <button
        aria-label="Dismiss"
        onClick={() => setVisible(false)}
        style={{
          background: "transparent",
          border: "none",
          color: "white",
          cursor: "pointer",
          padding: 0,
          marginLeft: "0.25rem",
          display: "inline-flex"
        }}
        type="button"
      >
        <X size={16} />
      </button>
    </div>
  );
}
