"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, History } from "lucide-react";
import { useEffect, useState } from "react";

import { api, queryKeys, type MapRevision } from "../../lib/api";
import type { RealtimeEnvelope } from "../../lib/realtime";

type RevisionsPanelProps = {
  mapId: string;
  /** Last realtime envelope received from useMapRealtime. Used to refresh. */
  lastEvent: RealtimeEnvelope | null;
};

const EVENT_LABEL: Record<string, string> = {
  "object.created": "Created",
  "object.updated": "Updated",
  "object.deleted": "Deleted",
  "layer.created": "Layer created",
  "layer.updated": "Layer updated",
  "layer.deleted": "Layer deleted",
  "map.updated": "Map updated",
  "map.image_updated": "Image updated"
};

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

export function RevisionsPanel({ mapId, lastEvent }: RevisionsPanelProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const revisionsQuery = useQuery({
    queryKey: queryKeys.mapRevisions(mapId),
    queryFn: () => api.revisions.list(mapId, 50),
    enabled: open
  });

  // Any object/layer/map mutation event invalidates the cached revisions.
  useEffect(() => {
    if (!lastEvent) return;
    if (!open) return;
    if (
      lastEvent.type.startsWith("object.") ||
      lastEvent.type.startsWith("layer.") ||
      lastEvent.type === "map.updated" ||
      lastEvent.type === "map.image_updated"
    ) {
      queryClient.invalidateQueries({ queryKey: queryKeys.mapRevisions(mapId) });
    }
  }, [lastEvent, mapId, open, queryClient]);

  return (
    <div
      style={{
        position: "fixed",
        right: 0,
        top: "50%",
        transform: "translateY(-50%)",
        zIndex: 40,
        display: "flex",
        alignItems: "stretch"
      }}
    >
      <button
        aria-expanded={open}
        aria-label={open ? "Close revision history" : "Open revision history"}
        className="subtle-button"
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "rgba(15, 23, 42, 0.9)",
          color: "#f8fafc",
          padding: "0.75rem 0.5rem",
          borderRadius: "0.5rem 0 0 0.5rem",
          border: "1px solid rgba(148, 163, 184, 0.3)",
          borderRight: "none"
        }}
        type="button"
      >
        {open ? (
          <ChevronRight size={16} />
        ) : (
          <History size={16} />
        )}
      </button>

      {open ? (
        <div
          aria-label="Revision history"
          role="region"
          style={{
            width: 320,
            maxHeight: "70vh",
            overflowY: "auto",
            background: "rgba(15, 23, 42, 0.95)",
            color: "#f8fafc",
            border: "1px solid rgba(148, 163, 184, 0.3)",
            borderRight: "none",
            padding: "0.75rem",
            boxShadow: "-12px 0 24px rgba(0,0,0,0.3)"
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.5rem"
            }}
          >
            <History size={16} />
            <strong style={{ fontSize: "0.9375rem" }}>Recent activity</strong>
          </div>

          {revisionsQuery.isLoading ? (
            <p className="muted-copy" style={{ fontSize: "0.8125rem" }}>
              Loading…
            </p>
          ) : null}

          {revisionsQuery.data && revisionsQuery.data.length === 0 ? (
            <p className="muted-copy" style={{ fontSize: "0.8125rem" }}>
              No revisions recorded yet. Mutations made while signed in
              with a database backend will appear here.
            </p>
          ) : null}

          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {(revisionsQuery.data ?? []).map((revision) => (
              <RevisionItem key={revision.id} revision={revision} />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function RevisionItem({ revision }: { revision: MapRevision }) {
  const label = EVENT_LABEL[revision.event_type] ?? revision.event_type;
  return (
    <li
      style={{
        padding: "0.5rem 0",
        borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
        fontSize: "0.8125rem"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
        <strong style={{ fontSize: "0.75rem", opacity: 0.85 }}>{label}</strong>
        <time
          dateTime={revision.created_at}
          style={{ fontSize: "0.6875rem", opacity: 0.6 }}
          title={new Date(revision.created_at).toLocaleString()}
        >
          {relativeTime(revision.created_at)}
        </time>
      </div>
      <div style={{ marginTop: "0.125rem" }}>
        {revision.summary || (
          <span style={{ opacity: 0.7 }}>(no summary)</span>
        )}
      </div>
      {revision.actor_display_name ? (
        <div style={{ fontSize: "0.6875rem", opacity: 0.6, marginTop: "0.125rem" }}>
          by {revision.actor_display_name}
        </div>
      ) : null}
    </li>
  );
}
