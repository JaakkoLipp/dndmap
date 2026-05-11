export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const API_PREFIX = "/api/v1";

function getApiBase() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
}

function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBase()}${API_PREFIX}${normalizedPath}`;
}

async function readError(response: Response) {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => String(item.msg ?? item)).join("; ");
    }
  } catch {
    // Fall through to status text.
  }

  return response.statusText || "Request failed";
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type User = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;
};

export type Campaign = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  role: "owner" | "dm" | "player" | "viewer" | null;
};

export type CampaignMap = {
  id: string;
  campaign_id: string;
  name: string;
  width: number;
  height: number;
  grid_size: number;
  background_color: string;
  image_object_key: string | null;
  image_url: string | null;
  image_name: string | null;
  image_content_type: string | null;
  created_at: string;
  updated_at: string;
};

export type LayerAudience = "dm" | "players" | "all";
export type LayerKind = "background" | "terrain" | "objects" | "fog" | "notes";
export type MapObjectKind =
  | "marker"
  | "label"
  | "polyline"
  | "freehand"
  | "polygon"
  | "handout";

export type MapLayer = {
  id: string;
  map_id: string;
  name: string;
  kind: LayerKind;
  visible: boolean;
  audience: LayerAudience;
  opacity: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type ApiPoint = {
  x: number;
  y: number;
};

export type AnnotationGeometry =
  | { type: "marker"; x: number; y: number; radius: number }
  | { type: "label"; x: number; y: number; text: string }
  | { type: "polyline"; points: ApiPoint[] }
  | { type: "freehand"; points: ApiPoint[] }
  | { type: "polygon"; points: ApiPoint[] }
  | { type: "handout"; x: number; y: number; width: number; height: number };

export type AnnotationStyle = {
  color?: string;
  fillColor?: string;
  strokeColor?: string;
  borderColor?: string;
  strokeWidth?: number;
  fontSize?: number;
  fontFamily?: string;
  opacity?: number;
};

export type MapAnnotation = {
  id: string;
  map_id: string;
  layer_id: string;
  name: string;
  kind: MapObjectKind;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  visible: boolean;
  audience: LayerAudience;
  geometry: AnnotationGeometry | null;
  style: Record<string, unknown> | null;
  properties: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Invite = {
  id: string;
  campaign_id: string;
  code: string;
  role: "owner" | "dm" | "player" | "viewer";
  max_uses: number | null;
  use_count: number;
  expires_at: string | null;
  created_at: string;
};

export type CampaignMember = {
  campaign_id: string;
  user_id: string;
  role: "owner" | "dm" | "player" | "viewer";
  joined_at: string;
};

export type CampaignMemberDetail = CampaignMember & {
  display_name: string;
  avatar_url: string | null;
};

export type MapRevision = {
  id: string;
  map_id: string;
  actor_user_id: string | null;
  actor_display_name: string | null;
  event_type: string;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
};

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

export type MapObjectCategory =
  | "settlement"
  | "dungeon"
  | "danger"
  | "quest"
  | "faction"
  | "route"
  | "rumor";

type BaseMapObject = {
  id: string;
  name: string;
  color: string;
  category: MapObjectCategory;
  dmVisible: boolean;
  playerVisible: boolean;
  notes: string;
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
  type: "polyline" | "freehand";
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

export const queryKeys = {
  authMe: ["auth", "me"] as const,
  campaigns: ["campaigns"] as const,
  campaign: (id: string) => ["campaigns", id] as const,
  campaignMe: (id: string) => ["campaigns", id, "me"] as const,
  campaignMembers: (id: string) => ["campaigns", id, "members"] as const,
  campaignMaps: (id: string) => ["campaigns", id, "maps"] as const,
  map: (id: string) => ["maps", id] as const,
  mapLayers: (id: string) => ["maps", id, "layers"] as const,
  mapObjects: (id: string, filters?: Record<string, unknown>) =>
    ["maps", id, "objects", filters ?? {}] as const,
  mapRevisions: (id: string) => ["maps", id, "revisions"] as const
};

function qs(params: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  auth: {
    loginUrl: (
      provider: "discord" | "google" | "github",
      options: { next?: string } = {}
    ) => {
      const query = options.next ? `?next=${encodeURIComponent(options.next)}` : "";
      return apiUrl(`/auth/${provider}/login${query}`);
    },
    me: () => apiFetch<User>("/auth/me"),
    logout: () => apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" }),
    localLogin: (username: string) =>
      apiFetch<User>("/auth/local/login", {
        method: "POST",
        body: JSON.stringify({ username })
      })
  },
  campaigns: {
    list: () => apiFetch<Campaign[]>("/campaigns"),
    create: (payload: { name: string; description?: string | null }) =>
      apiFetch<Campaign>("/campaigns", {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    get: (id: string) => apiFetch<Campaign>(`/campaigns/${id}`),
    me: (id: string) => apiFetch<CampaignMember>(`/campaigns/${id}/me`),
    update: (id: string, payload: { name?: string; description?: string | null }) =>
      apiFetch<Campaign>(`/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      }),
    delete: (id: string) =>
      apiFetch<void>(`/campaigns/${id}`, { method: "DELETE" })
  },
  maps: {
    list: (campaignId: string) =>
      apiFetch<CampaignMap[]>(`/campaigns/${campaignId}/maps`),
    create: (
      campaignId: string,
      payload: {
        name: string;
        width: number;
        height: number;
        grid_size?: number;
        background_color?: string;
      }
    ) =>
      apiFetch<CampaignMap>(`/campaigns/${campaignId}/maps`, {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    get: (id: string) => apiFetch<CampaignMap>(`/maps/${id}`),
    update: (
      id: string,
      payload: Partial<Pick<CampaignMap, "name" | "width" | "height" | "grid_size" | "background_color">>
    ) =>
      apiFetch<CampaignMap>(`/maps/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      }),
    uploadImage: (id: string, file: File) => {
      const formData = new FormData();
      formData.set("file", file);
      return apiFetch<CampaignMap>(`/maps/${id}/image`, {
        method: "POST",
        body: formData
      });
    }
  },
  layers: {
    list: (mapId: string, filters: { visible?: boolean; audience?: LayerAudience } = {}) =>
      apiFetch<MapLayer[]>(`/maps/${mapId}/layers${qs(filters)}`),
    create: (
      mapId: string,
      payload: {
        name: string;
        kind?: LayerKind;
        visible?: boolean;
        audience?: LayerAudience;
        opacity?: number;
        sort_order?: number;
      }
    ) =>
      apiFetch<MapLayer>(`/maps/${mapId}/layers`, {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    update: (id: string, payload: Partial<MapLayer>) =>
      apiFetch<MapLayer>(`/layers/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      }),
    delete: (id: string) => apiFetch<void>(`/layers/${id}`, { method: "DELETE" })
  },
  objects: {
    list: (
      mapId: string,
      filters: { layer_id?: string; visible?: boolean; audience?: LayerAudience } = {}
    ) => apiFetch<MapAnnotation[]>(`/maps/${mapId}/objects${qs(filters)}`),
    create: (
      mapId: string,
      payload: {
        layer_id: string;
        name: string;
        kind: MapObjectKind;
        visible?: boolean;
        audience?: LayerAudience;
        geometry: AnnotationGeometry;
        style?: AnnotationStyle;
        properties?: Record<string, unknown>;
      }
    ) =>
      apiFetch<MapAnnotation>(`/maps/${mapId}/objects`, {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    update: (
      id: string,
      payload: Partial<{
        layer_id: string;
        name: string;
        kind: MapObjectKind;
        visible: boolean;
        audience: LayerAudience;
        geometry: AnnotationGeometry;
        style: AnnotationStyle;
        properties: Record<string, unknown>;
      }>
    ) =>
      apiFetch<MapAnnotation>(`/objects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      }),
    delete: (id: string) => apiFetch<void>(`/objects/${id}`, { method: "DELETE" })
  },
  revisions: {
    list: (mapId: string, limit = 50) =>
      apiFetch<MapRevision[]>(`/maps/${mapId}/revisions?limit=${limit}`)
  },
  members: {
    list: (campaignId: string) =>
      apiFetch<CampaignMemberDetail[]>(`/campaigns/${campaignId}/members`),
    updateRole: (
      campaignId: string,
      userId: string,
      role: CampaignMember["role"]
    ) =>
      apiFetch<CampaignMemberDetail>(
        `/campaigns/${campaignId}/members/${userId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ role })
        }
      ),
    remove: (campaignId: string, userId: string) =>
      apiFetch<void>(`/campaigns/${campaignId}/members/${userId}`, {
        method: "DELETE"
      })
  },
  invites: {
    create: (
      campaignId: string,
      payload: {
        role?: "owner" | "dm" | "player" | "viewer";
        max_uses?: number | null;
        expires_in_hours?: number | null;
      }
    ) =>
      apiFetch<Invite>(`/campaigns/${campaignId}/invites`, {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    accept: (code: string) =>
      apiFetch<CampaignMember>(`/invites/${code}/accept`, { method: "POST" })
  }
};
