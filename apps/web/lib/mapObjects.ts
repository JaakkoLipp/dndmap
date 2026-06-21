import type {
  AreaObject,
  LabelObject,
  MapObject,
  MapObjectCategory,
  MarkerObject,
  PathObject,
  Point
} from "./api";

export const CATEGORY_ORDER: MapObjectCategory[] = [
  "settlement",
  "dungeon",
  "danger",
  "quest",
  "faction",
  "route",
  "rumor"
];

export const CATEGORY_META: Record<
  MapObjectCategory,
  { label: string; shortLabel: string; color: string }
> = {
  settlement: { label: "Settlement", shortLabel: "S", color: "#f6c177" },
  dungeon: { label: "Dungeon", shortLabel: "D", color: "#a78bfa" },
  danger: { label: "Danger", shortLabel: "!", color: "#fb7185" },
  quest: { label: "Quest", shortLabel: "Q", color: "#67e8f9" },
  faction: { label: "Faction", shortLabel: "F", color: "#c084fc" },
  route: { label: "Route", shortLabel: "R", color: "#5eead4" },
  rumor: { label: "Rumor", shortLabel: "?", color: "#e0e7ff" }
};

export const OBJECT_COLORS = CATEGORY_ORDER.map(
  (category) => CATEGORY_META[category].color
);

export type DraftPathInput = {
  type: "line" | "freehand";
  points: Point[];
};

export function getCategoryMeta(category: MapObjectCategory) {
  return CATEGORY_META[category] ?? CATEGORY_META.rumor;
}

export function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function getObjectDisplayName(object: MapObject) {
  if (object.type === "label") {
    return object.text || object.name;
  }

  return object.name;
}

export function hasHandout(object: MapObject) {
  return Boolean(object.handout && (object.handout.text || object.handout.image));
}

export function moveObject(object: MapObject, dx: number, dy: number): MapObject {
  if (object.type === "marker" || object.type === "label") {
    return {
      ...object,
      x: object.x + dx,
      y: object.y + dy
    };
  }

  return {
    ...object,
    points: object.points.map((point) => ({
      x: point.x + dx,
      y: point.y + dy
    }))
  };
}

export function exportBaseName(title: string) {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "map"
  );
}

function countOfType(objects: MapObject[], type: MapObject["type"]) {
  return objects.filter((object) => object.type === type).length;
}

export function createMarker(
  objects: MapObject[],
  point: Point,
  category: MapObjectCategory
): MarkerObject {
  const meta = getCategoryMeta(category);
  const markerNumber =
    objects.filter(
      (object) => object.type === "marker" && object.category === category
    ).length + 1;

  return {
    id: createId("marker"),
    type: "marker",
    name: `${meta.label} ${markerNumber}`,
    category,
    x: point.x,
    y: point.y,
    radius: 14,
    color: meta.color,
    dmVisible: true,
    playerVisible: false,
    notes: ""
  };
}

export function createLabel(
  objects: MapObject[],
  point: Point,
  category: MapObjectCategory
): LabelObject {
  // Labels never represent a route; fall back to a rumor note instead.
  const resolved = category === "route" ? "rumor" : category;
  const meta = getCategoryMeta(resolved);
  const labelNumber = countOfType(objects, "label") + 1;

  return {
    id: createId("label"),
    type: "label",
    name: `${meta.label} note ${labelNumber}`,
    category: resolved,
    text: `${meta.label} note ${labelNumber}`,
    x: point.x,
    y: point.y,
    fontSize: 28,
    color: meta.color,
    dmVisible: true,
    playerVisible: false,
    notes: ""
  };
}

export function createPathFromDraft(
  objects: MapObject[],
  draft: DraftPathInput
): PathObject | null {
  const kind: PathObject["type"] =
    draft.type === "line" ? "polyline" : "freehand";
  const usefulPoints =
    draft.type === "line"
      ? draft.points.slice(0, 2)
      : draft.points.filter((point, index, points) => {
          if (index === 0) {
            return true;
          }

          const previous = points[index - 1];
          return Math.hypot(point.x - previous.x, point.y - previous.y) > 3;
        });

  if (usefulPoints.length < 2) {
    return null;
  }

  const pathNumber = countOfType(objects, kind) + 1;

  return {
    id: createId(kind),
    type: kind,
    name: draft.type === "line" ? `Route ${pathNumber}` : `Trail ${pathNumber}`,
    category: "route",
    points: usefulPoints,
    strokeWidth: draft.type === "line" ? 5 : 4,
    color: CATEGORY_META.route.color,
    dmVisible: true,
    playerVisible: false,
    notes: ""
  };
}

export function createArea(
  objects: MapObject[],
  points: Point[],
  category: MapObjectCategory
): AreaObject | null {
  if (points.length < 3) {
    return null;
  }

  const meta = getCategoryMeta(category);
  const areaNumber = countOfType(objects, "area") + 1;

  return {
    id: createId("area"),
    type: "area",
    name: `Region ${areaNumber}`,
    category,
    points,
    strokeWidth: 3,
    fillOpacity: 0.22,
    color: meta.color,
    dmVisible: true,
    playerVisible: false,
    notes: ""
  };
}
