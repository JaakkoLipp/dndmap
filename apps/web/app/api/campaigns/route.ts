import { NextResponse } from "next/server";

const apiBase =
  process.env.INTERNAL_API_BASE_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${apiBase}/api/v1/campaigns`);
    if (!res.ok) return NextResponse.json({ campaigns: [] });
    const campaigns = await res.json();
    return NextResponse.json({ campaigns });
  } catch {
    return NextResponse.json({ campaigns: [] });
  }
}

export async function POST(request: Request) {
  const { title, width, height, campaignId, mapId } =
    (await request.json()) as {
      title: string;
      width: number;
      height: number;
      campaignId?: string;
      mapId?: string;
    };

  const name = title?.trim() || "Untitled Campaign";

  try {
    let resolvedCampaignId = campaignId;
    let resolvedMapId = mapId;

    if (!resolvedCampaignId) {
      const cRes = await fetch(`${apiBase}/api/v1/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      if (!cRes.ok)
        return NextResponse.json({ ok: false }, { status: 502 });
      const campaign = (await cRes.json()) as { id: string };
      resolvedCampaignId = campaign.id;
    } else {
      await fetch(`${apiBase}/api/v1/campaigns/${resolvedCampaignId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
    }

    if (!resolvedMapId) {
      const mRes = await fetch(
        `${apiBase}/api/v1/campaigns/${resolvedCampaignId}/maps`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            width: width ?? 1600,
            height: height ?? 1000
          })
        }
      );
      if (!mRes.ok)
        return NextResponse.json({ ok: false }, { status: 502 });
      const map = (await mRes.json()) as { id: string };
      resolvedMapId = map.id;
    } else {
      await fetch(`${apiBase}/api/v1/maps/${resolvedMapId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, width, height })
      });
    }

    return NextResponse.json({
      ok: true,
      savedAt: new Date().toISOString(),
      campaignId: resolvedCampaignId,
      mapId: resolvedMapId
    });
  } catch {
    return NextResponse.json({ ok: false }, { status: 502 });
  }
}
