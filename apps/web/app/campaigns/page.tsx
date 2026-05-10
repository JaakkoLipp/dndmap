"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { AppHeader } from "../../components/layout/AppHeader";
import { api, ApiError, queryKeys } from "../../lib/api";

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

  const authError =
    campaignsQuery.error instanceof ApiError && campaignsQuery.error.status === 401;

  return (
    <main className="app-shell">
      <AppHeader />

      <section className="content-band">
        <div className="section-title-row">
          <div>
            <h1>Your campaigns</h1>
            <p>Choose a campaign, create a new table, or jump back into a map.</p>
          </div>
        </div>

        <form className="inline-form" onSubmit={submit}>
          <input
            aria-label="Campaign name"
            onChange={(event) => setName(event.target.value)}
            placeholder="New campaign name"
            value={name}
          />
          <button className="primary-button" disabled={createCampaign.isPending} type="submit">
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

        {campaignsQuery.data ? (
          <div className="resource-grid">
            {campaignsQuery.data.length === 0 ? (
              <div className="empty-state">
                <p>No campaigns yet — create one above.</p>
                <p className="muted-copy">
                  Got an invite link? Open it to join an existing campaign.
                </p>
              </div>
            ) : (
              campaignsQuery.data.map((campaign) => (
                <Link
                  className="resource-card"
                  href={`/campaigns/${campaign.id}`}
                  key={campaign.id}
                >
                  <strong>{campaign.name}</strong>
                  <span>{campaign.description || "Campaign workspace"}</span>
                </Link>
              ))
            )}
          </div>
        ) : null}
      </section>
    </main>
  );
}
