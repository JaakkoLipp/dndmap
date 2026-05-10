"use client";

import { useMutation } from "@tanstack/react-query";
import { TicketCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "../../../lib/api";

export default function InvitePage() {
  const { code } = useParams<{ code: string }>();
  const acceptInvite = useMutation({
    mutationFn: () => api.invites.accept(code)
  });

  return (
    <main className="app-shell centered-shell">
      <section className="auth-panel">
        <div className="brand-lockup">
          <TicketCheck size={28} />
          <div>
            <h1>Campaign Invite</h1>
            <p>Accept the invite to add this campaign to your table list.</p>
          </div>
        </div>

        {acceptInvite.isSuccess ? (
          <div className="notice">
            <span>Invite accepted</span>
            <Link href={`/campaigns/${acceptInvite.data.campaign_id}`}>
              Open campaign
            </Link>
          </div>
        ) : (
          <button
            className="wide-action"
            disabled={acceptInvite.isPending}
            onClick={() => acceptInvite.mutate()}
            type="button"
          >
            <TicketCheck size={18} />
            <span>{acceptInvite.isPending ? "Accepting…" : "Accept invite"}</span>
          </button>
        )}

        {acceptInvite.error ? (
          <p className="muted-copy">
            {acceptInvite.error instanceof Error
              ? acceptInvite.error.message
              : "Invite could not be accepted"}
          </p>
        ) : null}
      </section>
    </main>
  );
}
