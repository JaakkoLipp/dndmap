export type Point = {
  x: number;
  y: number;
};

export type MapImageState = {
  name: string;
  src: string;
  width: number;
  height: number;
};

type BaseMapObject = {
  id: string;
  name: string;
  color: string;
  visible: boolean;
};

export type MarkerObject = BaseMapObject & {
  type: "marker";
  x: number;
  y: number;
  radius: number;
};

export type LabelObject = BaseMapObject & {
  type: "label";
  x: number;
  y: number;
  text: string;
  fontSize: number;
};

export type PathObject = BaseMapObject & {
  type: "line" | "freehand";
  points: Point[];
  strokeWidth: number;
};

export type MapObject = MarkerObject | LabelObject | PathObject;

export type CampaignMapSnapshot = {
  title: string;
  image: MapImageState | null;
  objects: MapObject[];
  viewport: {
    x: number;
    y: number;
    scale: number;
  };
};

export type SaveCampaignResult = {
  ok: boolean;
  savedAt?: string;
  snapshot?: CampaignMapSnapshot;
};

export async function saveCampaignDraft(
  snapshot: CampaignMapSnapshot
): Promise<SaveCampaignResult> {
  // Local images stay browser-only until the upload/persistence route exists.
  const payload: CampaignMapSnapshot = {
    ...snapshot,
    image: snapshot.image
      ? {
          ...snapshot.image,
          src: "local-browser-image"
        }
      : null
  };

  const response = await fetch("/api/campaigns", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error("Campaign draft could not be saved.");
  }

  return response.json() as Promise<SaveCampaignResult>;
}
