"use client";

import type { PresenceEntry } from "../../lib/realtime";

type PresenceIndicatorProps = {
  state: "idle" | "connecting" | "open" | "closed";
  presence: PresenceEntry[];
};

const STATE_LABEL: Record<PresenceIndicatorProps["state"], string> = {
  idle: "Idle",
  connecting: "Connecting…",
  open: "Live",
  closed: "Offline"
};

const STATE_COLOR: Record<PresenceIndicatorProps["state"], string> = {
  idle: "#6b7280",
  connecting: "#f59e0b",
  open: "#10b981",
  closed: "#ef4444"
};

function initials(name: string | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function PresenceIndicator({ state, presence }: PresenceIndicatorProps) {
  return (
    <div
      role="status"
      aria-label={`Realtime ${STATE_LABEL[state]}, ${presence.length} viewer${
        presence.length === 1 ? "" : "s"
      }`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.25rem 0.75rem",
        borderRadius: "999px",
        background: "rgba(15, 23, 42, 0.85)",
        color: "#f8fafc",
        fontSize: "0.8125rem",
        lineHeight: 1.2,
        border: `1px solid ${STATE_COLOR[state]}`
      }}
    >
      <span
        aria-hidden
        style={{
          width: "0.5rem",
          height: "0.5rem",
          borderRadius: "50%",
          background: STATE_COLOR[state]
        }}
      />
      <span>{STATE_LABEL[state]}</span>
      {presence.length > 0 ? (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.25rem",
            paddingLeft: "0.5rem",
            borderLeft: "1px solid rgba(248, 250, 252, 0.2)"
          }}
        >
          {presence.slice(0, 4).map((entry) => (
            <span
              key={entry.client_id}
              title={entry.actor?.display_name ?? "Anonymous"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "1.5rem",
                height: "1.5rem",
                borderRadius: "50%",
                background: "rgba(248, 250, 252, 0.15)",
                fontSize: "0.6875rem",
                fontWeight: 600
              }}
            >
              {initials(entry.actor?.display_name)}
            </span>
          ))}
          {presence.length > 4 ? <span>+{presence.length - 4}</span> : null}
        </span>
      ) : null}
    </div>
  );
}
