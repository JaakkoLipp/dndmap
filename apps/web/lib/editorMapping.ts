import type {
  AnnotationGeometry,
  AnnotationStyle,
  LayerAudience,
  MapAnnotation,
  MapObject,
  MapObjectCategory
} from "./api";

const CATEGORIES: MapObjectCategory[] = [
  "settlement",
  "dungeon",
  "danger",
  "quest",
  "faction",
  "route",
  "rumor"
];

const FALLBACK_COLORS: Record<MapObjectCategory, string> = {
  settlement: "#f6c177",
  dungeon: "#a78bfa",
  danger: "#fb7185",
  quest: "#67e8f9",
  faction: "#c084fc",
  route: "#5eead4",
  rumor: "#e0e7ff"
};

function isCategory(value: unknown): value is MapObjectCategory {
  return typeof value === "string" && CATEGORIES.includes(value as MapObjectCategory);
}

function styleValue<T>(style: Record<string, unknown> | null, key: string, fallback: T): T {
  const value = style?.[key];
  return value === undefined || value === null ? fallback : (value as T);
}

function numberStyle(style: Record<string, unknown> | null, key: string, fallback: number) {
  const value = style?.[key];
  return typeof value === "number" ? value : fallback;
}

function stringProperty(properties: Record<string, unknown>, key: string, fallback = "") {
  const value = properties[key];
  return typeof value === "string" ? value : fallback;
}

function audienceFromObject(object: MapObject): LayerAudience {
  return object.playerVisible ? "players" : "dm";
}

export function annotationToEditorObject(annotation: MapAnnotation): MapObject | null {
  if (!annotation.geometry) {
    return null;
  }

  const category = isCategory(annotation.properties.category)
    ? annotation.properties.category
    : annotation.kind === "polyline" || annotation.kind === "freehand"
      ? "route"
      : "settlement";
  const notes = stringProperty(annotation.properties, "notes");
  const color = styleValue(
    annotation.style,
    annotation.kind === "polyline" || annotation.kind === "freehand"
      ? "stroke_color"
      : "color",
    FALLBACK_COLORS[category]
  );
  const sharedVisibility = {
    dmVisible: annotation.visible,
    playerVisible: annotation.visible && annotation.audience === "players"
  };

  if (annotation.geometry.type === "marker") {
    return {
      id: annotation.id,
      type: "marker",
      name: annotation.name,
      category,
      color,
      notes,
      radius: annotation.geometry.radius,
      x: annotation.geometry.x,
      y: annotation.geometry.y,
      ...sharedVisibility
    };
  }

  if (annotation.geometry.type === "label") {
    return {
      id: annotation.id,
      type: "label",
      name: annotation.name,
      category,
      color,
      notes,
      fontSize: numberStyle(annotation.style, "font_size", 28),
      text: annotation.geometry.text || annotation.name,
      x: annotation.geometry.x,
      y: annotation.geometry.y,
      ...sharedVisibility
    };
  }

  if (
    annotation.geometry.type === "polyline" ||
    annotation.geometry.type === "freehand"
  ) {
    return {
      id: annotation.id,
      type: annotation.geometry.type,
      name: annotation.name,
      category,
      color,
      notes,
      points: annotation.geometry.points,
      strokeWidth: numberStyle(annotation.style, "stroke_width", 5),
      ...sharedVisibility
    };
  }

  return null;
}

export function editorObjectToPayload(object: MapObject): {
  name: string;
  kind: MapObject["type"];
  visible: boolean;
  audience: LayerAudience;
  geometry: AnnotationGeometry;
  style: AnnotationStyle;
  properties: Record<string, unknown>;
} {
  const base = {
    name: object.name,
    kind: object.type,
    visible: object.dmVisible,
    audience: audienceFromObject(object),
    properties: {
      category: object.category,
      notes: object.notes
    }
  };

  if (object.type === "marker") {
    return {
      ...base,
      geometry: {
        type: "marker",
        x: object.x,
        y: object.y,
        radius: object.radius
      },
      style: { color: object.color }
    };
  }

  if (object.type === "label") {
    return {
      ...base,
      geometry: {
        type: "label",
        x: object.x,
        y: object.y,
        text: object.text
      },
      style: {
        color: object.color,
        fontSize: object.fontSize
      }
    };
  }

  return {
    ...base,
    geometry: {
      type: object.type,
      points: object.points
    },
    style: {
      strokeColor: object.color,
      strokeWidth: object.strokeWidth
    }
  };
}
