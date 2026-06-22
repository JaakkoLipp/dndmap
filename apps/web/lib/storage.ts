import type {
  CampaignMapSnapshot,
  HandoutContent,
  MapImageState,
  MapObject,
  MapObjectCategory,
  Point
} from "./api";

const STORAGE_KEY = "dndmap.campaign.v1";
const CAMPAIGN_FILE_VERSION = 1;

const CATEGORIES: MapObjectCategory[] = [
  "settlement",
  "dungeon",
  "danger",
  "quest",
  "faction",
  "route",
  "rumor"
];

type CampaignFile = {
  format: "dndmap.campaign";
  version: number;
  savedAt: string;
  snapshot: CampaignMapSnapshot;
};

export type PersistResult = {
  ok: boolean;
  error?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toFiniteNumber(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function toStringValue(value: unknown, fallback: string) {
  return typeof value === "string" ? value : fallback;
}

function toBoolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function toCategory(value: unknown): MapObjectCategory {
  return CATEGORIES.includes(value as MapObjectCategory)
    ? (value as MapObjectCategory)
    : "rumor";
}

function makeFallbackId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function normalizePoints(value: unknown): Point[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((point) => ({
      x: toFiniteNumber(point.x, 0),
      y: toFiniteNumber(point.y, 0)
    }));
}

function normalizeImage(value: unknown): MapImageState | null {
  if (!isRecord(value)) {
    return null;
  }

  const src = toStringValue(value.src, "");

  if (!src) {
    return null;
  }

  return {
    name: toStringValue(value.name, "Map image"),
    src,
    width: Math.max(1, toFiniteNumber(value.width, 1600)),
    height: Math.max(1, toFiniteNumber(value.height, 1000))
  };
}

function normalizeHandout(value: unknown): HandoutContent | null {
  if (!isRecord(value)) {
    return null;
  }

  const text = toStringValue(value.text, "");
  const image = normalizeImage(value.image);

  if (!text && !image) {
    return null;
  }

  return { text, image };
}

function normalizeObject(value: unknown): MapObject | null {
  if (!isRecord(value)) {
    return null;
  }

  const type = value.type;
  const base = {
    id: toStringValue(value.id, makeFallbackId("object")),
    name: toStringValue(value.name, "Map note"),
    color: toStringValue(value.color, "#e0e7ff"),
    category: toCategory(value.category),
    dmVisible: toBoolean(value.dmVisible, true),
    playerVisible: toBoolean(value.playerVisible, false),
    notes: toStringValue(value.notes, ""),
    handout: normalizeHandout(value.handout)
  };

  if (type === "marker") {
    return {
      ...base,
      type: "marker",
      x: toFiniteNumber(value.x, 0),
      y: toFiniteNumber(value.y, 0),
      radius: Math.max(4, toFiniteNumber(value.radius, 14))
    };
  }

  if (type === "label") {
    return {
      ...base,
      type: "label",
      x: toFiniteNumber(value.x, 0),
      y: toFiniteNumber(value.y, 0),
      text: toStringValue(value.text, base.name),
      fontSize: Math.max(8, toFiniteNumber(value.fontSize, 28))
    };
  }

  if (type === "polyline" || type === "freehand") {
    const points = normalizePoints(value.points);

    if (points.length < 2) {
      return null;
    }

    return {
      ...base,
      type,
      points,
      strokeWidth: Math.max(1, toFiniteNumber(value.strokeWidth, 5))
    };
  }

  if (type === "area") {
    const points = normalizePoints(value.points);

    if (points.length < 3) {
      return null;
    }

    return {
      ...base,
      type: "area",
      points,
      strokeWidth: Math.max(1, toFiniteNumber(value.strokeWidth, 3)),
      fillOpacity: Math.min(
        1,
        Math.max(0, toFiniteNumber(value.fillOpacity, 0.22))
      ),
      isReveal: toBoolean(value.isReveal, false)
    };
  }

  return null;
}

export function normalizeSnapshot(value: unknown): CampaignMapSnapshot | null {
  if (!isRecord(value)) {
    return null;
  }

  if (!Array.isArray(value.objects)) {
    return null;
  }

  const viewport = isRecord(value.viewport) ? value.viewport : {};

  return {
    title: toStringValue(value.title, "D&D Campaign"),
    image: normalizeImage(value.image),
    objects: value.objects
      .map((object) => normalizeObject(object))
      .filter((object): object is MapObject => object !== null),
    fogEnabled: toBoolean(value.fogEnabled, false),
    viewport: {
      x: toFiniteNumber(viewport.x, 0),
      y: toFiniteNumber(viewport.y, 0),
      scale: toFiniteNumber(viewport.scale, 1)
    }
  };
}

export function loadStoredSnapshot(): CampaignMapSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      return null;
    }

    return normalizeSnapshot(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function saveStoredSnapshot(snapshot: CampaignMapSnapshot): PersistResult {
  if (typeof window === "undefined") {
    return { ok: false };
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    return { ok: true };
  } catch (error) {
    const isQuota =
      error instanceof DOMException &&
      (error.name === "QuotaExceededError" ||
        error.name === "NS_ERROR_DOM_QUOTA_REACHED");

    return {
      ok: false,
      error: isQuota
        ? "Autosave skipped: map image is too large for local storage"
        : "Autosave failed"
    };
  }
}

export function clearStoredSnapshot() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage errors; clearing is best-effort.
  }
}

export function serializeCampaign(snapshot: CampaignMapSnapshot): string {
  const file: CampaignFile = {
    format: "dndmap.campaign",
    version: CAMPAIGN_FILE_VERSION,
    savedAt: new Date().toISOString(),
    snapshot
  };

  return JSON.stringify(file, null, 2);
}

export function downloadCampaignFile(
  snapshot: CampaignMapSnapshot,
  filename: string
) {
  const blob = new Blob([serializeCampaign(snapshot)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function readCampaignFile(
  file: File
): Promise<CampaignMapSnapshot> {
  const text = await file.text();
  const parsed = JSON.parse(text) as unknown;

  // Accept either a wrapped campaign file or a bare snapshot.
  const candidate =
    isRecord(parsed) && "snapshot" in parsed ? parsed.snapshot : parsed;
  const snapshot = normalizeSnapshot(candidate);

  if (!snapshot) {
    throw new Error("This file is not a valid campaign map");
  }

  return snapshot;
}
