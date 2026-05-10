"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { queryKeys } from "../lib/api";
import {
  buildWebSocketUrl,
  type PresenceEntry,
  type RealtimeEnvelope
} from "../lib/realtime";

type ConnectionState = "idle" | "connecting" | "open" | "closed";

export type UseMapRealtimeOptions = {
  campaignId: string;
  mapId: string;
  enabled?: boolean;
};

export type UseMapRealtimeResult = {
  state: ConnectionState;
  presence: PresenceEntry[];
  /** Last event received, for components that want raw access. */
  lastEvent: RealtimeEnvelope | null;
};

const RECONNECT_DELAYS_MS = [500, 1000, 2000, 4000, 8000];

export function useMapRealtime({
  campaignId,
  mapId,
  enabled = true
}: UseMapRealtimeOptions): UseMapRealtimeResult {
  const queryClient = useQueryClient();
  const [state, setState] = useState<ConnectionState>("idle");
  const [presence, setPresence] = useState<PresenceEntry[]>([]);
  const [lastEvent, setLastEvent] = useState<RealtimeEnvelope | null>(null);

  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    cancelledRef.current = false;

    function connect() {
      if (cancelledRef.current) return;
      setState("connecting");
      const ws = new WebSocket(buildWebSocketUrl(campaignId, mapId));
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        setState("open");
      };

      ws.onmessage = (event) => {
        let envelope: RealtimeEnvelope;
        try {
          envelope = JSON.parse(event.data);
        } catch {
          return;
        }
        setLastEvent(envelope);
        handleEvent(envelope);
      };

      ws.onerror = () => {
        // The close handler will run after error too; centralise reconnect there.
      };

      ws.onclose = () => {
        wsRef.current = null;
        setState("closed");
        setPresence([]);
        if (cancelledRef.current) return;
        const delay =
          RECONNECT_DELAYS_MS[
            Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS_MS.length - 1)
          ];
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      };
    }

    function handleEvent(envelope: RealtimeEnvelope) {
      switch (envelope.type) {
        case "presence.snapshot": {
          const actors = (envelope.payload?.actors ?? []) as PresenceEntry[];
          setPresence(actors);
          break;
        }
        case "presence.joined": {
          const clientId = envelope.actor?.client_id;
          if (!clientId) return;
          setPresence((prev) =>
            prev.some((p) => p.client_id === clientId)
              ? prev
              : [
                  ...prev,
                  {
                    client_id: clientId,
                    actor: envelope.actor,
                    joined_at: envelope.sent_at
                  }
                ]
          );
          break;
        }
        case "presence.left": {
          const clientId = envelope.actor?.client_id;
          if (!clientId) return;
          setPresence((prev) => prev.filter((p) => p.client_id !== clientId));
          break;
        }
        case "map.updated":
        case "map.image_updated":
          queryClient.invalidateQueries({ queryKey: queryKeys.map(mapId) });
          break;
        case "map.deleted":
          queryClient.invalidateQueries({ queryKey: queryKeys.map(mapId) });
          queryClient.invalidateQueries({
            queryKey: queryKeys.campaignMaps(campaignId)
          });
          break;
        case "layer.created":
        case "layer.updated":
        case "layer.deleted":
          queryClient.invalidateQueries({ queryKey: queryKeys.mapLayers(mapId) });
          break;
        case "object.created":
        case "object.updated":
        case "object.deleted":
          queryClient.invalidateQueries({ queryKey: queryKeys.mapObjects(mapId) });
          break;
      }
    }

    connect();

    return () => {
      cancelledRef.current = true;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = null;
    };
  }, [campaignId, mapId, enabled, queryClient]);

  return { state, presence, lastEvent };
}
