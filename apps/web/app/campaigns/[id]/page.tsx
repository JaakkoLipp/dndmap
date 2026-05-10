"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Map, Plus, Ticket } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { AppHeader } from "../../../components/layout/AppHeader";
import { api, ApiError, queryKeys, type Invite } from "../../../lib/api";
import {
  ROLE_LABEL,
  canCreateInvites,
  canEditMaps,
  type Role
} from "../../../lib/roles";

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [mapName, setMapName] = useState("");
  const [latestInvite, setLatestInvite] = useState<Invite | null>(null);

  const campaignQuery = useQuery({
    queryKey: queryKeys.campaign(id),
    queryFn: () => api.campaigns.get(id)
  });
  const meQuery = useQuery({
    queryKey: queryKeys.campaignMe(id),
    queryFn: () => api.campaigns.me(id),
    retry: false
  });
  const mapsQuery = useQuery({
    queryKey: queryKeys.campaignMaps(id),
    queryFn: () => api.maps.list(id)
  });
  const createMap = useMutation({
    mutationFn: (name: string) =>
      api.maps.create(id, {
        name,
        width: 1600,
        height: 1000,
        grid_size: 70,
        background_color: "#1f2937"
      }),
    onSuccess: async () => {
      setMapName("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.campaignMaps(id) });
    }
  });
  const createInvite = useMutation({
    mutationFn: () => api.invites.create(id, { role: "player" }),
    onSuccess: (invite) => setLatestInvite(invite)
  });

  const role: Role | undefined = meQuery.data?.role;
  const canEdit = canEditMaps(role);
  const canInvite = canCreateInvites(role);

  const submitMap = (event: FormEvent) => {
    event.preventDefault();
    if (!canEdit) return;
    const trimmed = mapName.trim();
    if (trimmed) {
      createMap.mutate(trimmed);
    }
  };

  const inviteUrl =
    latestInvite && typeof window !== "undefined"
      ? `${window.location.origin}/invite/${latestInvite.code}`
      : null;

  const authError =
    campaignQuery.error instanceof ApiError && campaignQuery.error.status === 401;

  return (
    <main className="app-shell">
      <AppHeader
        leading={
          <Link className="subtle-button" href="/campaigns">
            <ArrowLeft size={18} />
            <span>Campaigns</span>
          </Link>
        }
        role={role}
      />

      <section className="content-band">
        {authError ? (
          <div className="empty-state">
            <p>Your session is required for this campaign.</p>
            <Link className="primary-link-button" href="/login">
              Sign in
            </Link>
          </div>
        ) : null}

        <div className="section-title-row">
          <div>
            <h1>{campaignQuery.data?.name ?? "Campaign"}</h1>
            <p>
              {campaignQuery.data?.description ?? "Maps, invites, and DM tools."}
              {role ? ` · You are a ${ROLE_LABEL[role]}` : null}
            </p>
          </div>
          {canInvite ? (
            <button
              className="tool-button"
              disabled={createInvite.isPending}
              onClick={() => createInvite.mutate()}
              type="button"
            >
              {createInvite.isPending ? <Loader2 size={18} /> : <Ticket size={18} />}
              <span>Create invite</span>
            </button>
          ) : null}
        </div>

        {createInvite.error ? (
          <div className="notice error-notice">
            {createInvite.error instanceof Error
              ? createInvite.error.message
              : "Invite could not be created"}
          </div>
        ) : null}

        {inviteUrl ? (
          <div className="notice">
            <span>Invite link</span>
            <code>{inviteUrl}</code>
          </div>
        ) : null}

        {canEdit ? (
          <form className="inline-form" onSubmit={submitMap}>
            <input
              aria-label="Map name"
              onChange={(event) => setMapName(event.target.value)}
              placeholder="New map name"
              value={mapName}
            />
            <button
              className="primary-button"
              disabled={createMap.isPending}
              type="submit"
            >
              {createMap.isPending ? <Loader2 size={18} /> : <Plus size={18} />}
              <span>Create map</span>
            </button>
          </form>
        ) : role ? (
          <p className="muted-copy">
            Map creation is restricted to DMs and owners.
          </p>
        ) : null}

        {mapsQuery.isLoading ? <div className="empty-state">Loading maps…</div> : null}

        {mapsQuery.data ? (
          <div className="resource-grid">
            {mapsQuery.data.length === 0 ? (
              <div className="empty-state">No maps yet</div>
            ) : (
              mapsQuery.data.map((campaignMap) => (
                <Link
                  className="resource-card"
                  href={`/campaigns/${id}/maps/${campaignMap.id}`}
                  key={campaignMap.id}
                >
                  <Map size={20} />
                  <strong>{campaignMap.name}</strong>
                  <span>
                    {campaignMap.width} × {campaignMap.height}
                  </span>
                </Link>
              ))
            )}
          </div>
        ) : null}
      </section>
    </main>
  );
}
