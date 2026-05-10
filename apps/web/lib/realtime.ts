// Realtime event envelope shared with the backend.
// See apps/api/app/realtime/events.py for the canonical source.

export type RealtimeActor = {
  user_id?: string;
  display_name?: string;
  role?: "owner" | "dm" | "player" | "viewer";
  client_id?: string;
};

export type RealtimeEnvelope = {
  id: string;
  type: RealtimeEventType | string;
  map_id: string;
  actor: RealtimeActor | null;
  payload: Record<string, unknown>;
  sent_at: string;
};

export type RealtimeEventType =
  | "map.connected"
  | "presence.snapshot"
  | "presence.joined"
  | "presence.left"
  | "map.updated"
  | "map.image_updated"
  | "map.deleted"
  | "layer.created"
  | "layer.updated"
  | "layer.deleted"
  | "object.created"
  | "object.updated"
  | "object.deleted";

export type PresenceEntry = {
  client_id: string;
  actor: RealtimeActor | null;
  joined_at: string;
};

export function buildWebSocketUrl(campaignId: string, mapId: string): string {
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

  if (base) {
    const url = new URL(base);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `/api/v1/ws/campaigns/${campaignId}/maps/${mapId}`;
    return url.toString();
  }

  if (typeof window === "undefined") {
    return `/api/v1/ws/campaigns/${campaignId}/maps/${mapId}`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/ws/campaigns/${campaignId}/maps/${mapId}`;
}
