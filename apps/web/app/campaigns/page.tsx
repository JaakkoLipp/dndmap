"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import { AppHeader } from "../../components/layout/AppHeader";
import { api, ApiError, queryKeys, type Campaign } from "../../lib/api";
import { ROLE_BADGE_COLOR, ROLE_LABEL, type Role } from "../../lib/roles";

const ROLE_GROUP_ORDER: Role[] = ["owner", "dm", "player", "viewer"];
const GROUP_HEADING: Record<Role, string> = {
  owner: "Campaigns you own",
  dm: "Campaigns you DM",
  player: "Campaigns you play in",
  viewer: "Campaigns you watch"
};

function groupByRole(campaigns: Campaign[]): Array<{ role: Role; items: Campaign[] }> {
  const buckets = new Map<Role, Campaign[]>();
  for (const campaign of campaigns) {
    const role = (campaign.role ?? "viewer") as Role;
    if (!buckets.has(role)) buckets.set(role, []);
    buckets.get(role)!.push(campaign);
  }
  return ROLE_GROUP_ORDER.filter((role) => buckets.has(role)).map((role) => ({
    role,
    items: buckets.get(role)!
  }));
}

function RolePill({ role }: { role: Role }) {
  return (
    <span
      aria-label={`Role: ${ROLE_LABEL[role]}`}
      style={{
        padding: "0.125rem 0.5rem",
        borderRadius: "999px",
        background: ROLE_BADGE_COLOR[role],
        color: "white",
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase"
      }}
    >
      {ROLE_LABEL[role]}
    </span>
  );
}

export default function CampaignsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const campaignsQuery = useQuery({
    queryKey: queryKeys.campaigns,
    queryFn: api.campaigns.list
  });
  const createCampaign = useMutation({
    mutationFn: api.campaigns.create,
    onSuccess: async () => {
      setName("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.campaigns });
    }
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed) {
      createCampaign.mutate({ name: trimmed });
    }
  };

  const groups = useMemo(
    () => groupByRole(campaignsQuery.data ?? []),
    [campaignsQuery.data]
  );

  const authError =
    campaignsQuery.error instanceof ApiError && campaignsQuery.error.status === 401;

  return (
    <main className="app-shell">
      <AppHeader />

      <section className="content-band">
        <div className="section-title-row">
          <div>
            <h1>Your campaigns</h1>
            <p>
              You can be a DM in one campaign and a player in another — each
              row shows the role you hold there.
            </p>
          </div>
        </div>

        <form className="inline-form" onSubmit={submit}>
          <input
            aria-label="Campaign name"
            onChange={(event) => setName(event.target.value)}
            placeholder="New campaign name"
            value={name}
          />
          <button
            className="primary-button"
            disabled={createCampaign.isPending}
            type="submit"
          >
            {createCampaign.isPending ? <Loader2 size={18} /> : <Plus size={18} />}
            <span>Create</span>
          </button>
        </form>

        {authError ? (
          <div className="empty-state">
            <p>Your session is required for campaign access.</p>
            <Link className="primary-link-button" href="/login">
              Sign in
            </Link>
          </div>
        ) : null}

        {campaignsQuery.isLoading ? (
          <div className="empty-state">Loading campaigns…</div>
        ) : null}

        {campaignsQuery.data && campaignsQuery.data.length === 0 ? (
          <div className="empty-state">
            <p>No campaigns yet — create one above.</p>
            <p className="muted-copy">
              Got an invite link? Open it to join an existing campaign.
            </p>
          </div>
        ) : null}

        {groups.map(({ role, items }) => (
          <div key={role} style={{ marginTop: "1.5rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "0.5rem"
              }}
            >
              <h2 style={{ fontSize: "1rem", margin: 0 }}>
                {GROUP_HEADING[role]}
              </h2>
              <span className="muted-copy" style={{ fontSize: "0.8125rem" }}>
                {items.length}
              </span>
            </div>
            <div className="resource-grid">
              {items.map((campaign) => (
                <Link
                  className="resource-card"
                  href={`/campaigns/${campaign.id}`}
                  key={campaign.id}
                  style={{ position: "relative" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: "0.5rem",
                      right: "0.5rem"
                    }}
                  >
                    <RolePill role={role} />
                  </div>
                  <strong style={{ paddingRight: "4rem" }}>
                    {campaign.name}
                  </strong>
                  <span>{campaign.description || "Campaign workspace"}</span>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
