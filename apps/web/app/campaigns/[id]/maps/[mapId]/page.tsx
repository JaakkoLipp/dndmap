"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";

const HostedMapEditor = dynamic(
  () => import("./HostedMapEditor").then((mod) => mod.HostedMapEditor),
  {
    ssr: false,
    loading: () => <div className="empty-state">Loading map editor…</div>
  }
);

export default function CampaignMapPage() {
  const { id, mapId } = useParams<{ id: string; mapId: string }>();

  return (
    <>
      <Link className="floating-back-link" href={`/campaigns/${id}`}>
        Back to campaign
      </Link>
      <HostedMapEditor campaignId={id} mapId={mapId} />
    </>
  );
}
