import { NextResponse } from "next/server";
import type { CampaignMapSnapshot } from "../../../lib/campaignApi";

export async function GET() {
  return NextResponse.json({
    campaigns: [],
    message: "Campaign persistence is stubbed for the first frontend slice."
  });
}

export async function POST(request: Request) {
  const snapshot = (await request.json()) as CampaignMapSnapshot;

  return NextResponse.json({
    ok: true,
    savedAt: new Date().toISOString(),
    snapshot
  });
}
