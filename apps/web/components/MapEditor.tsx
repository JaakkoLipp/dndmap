"use client";

import {
  CloudFog,
  Download,
  Eye,
  EyeOff,
  FilePlus2,
  FileText,
  FolderOpen,
  Hexagon,
  ImagePlus,
  Layers3,
  MapPin,
  Maximize2,
  MonitorPlay,
  MousePointer2,
  Move,
  Paperclip,
  PenLine,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Type,
  Users,
  Waypoints,
  X,
  ZoomIn,
  ZoomOut,
  type LucideIcon
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import type {
  PointerEvent as ReactPointerEvent,
  WheelEvent as ReactWheelEvent
} from "react";
import type {
  AreaObject,
  CampaignMapSnapshot,
  HandoutContent,
  MapImageState,
  MapObject,
  MapObjectCategory,
  PathObject,
  Point
} from "../lib/api";
import { downloadCanvasAsPdf } from "../lib/pdfExport";
import {
  CATEGORY_ORDER,
  OBJECT_COLORS,
  createArea,
  createLabel,
  createMarker,
  createPathFromDraft,
  exportBaseName,
  getCategoryMeta,
  getObjectDisplayName,
  hasHandout,
  moveObject
} from "../lib/mapObjects";
import {
  clearStoredSnapshot,
  downloadCampaignFile,
  loadStoredSnapshot,
  readCampaignFile,
  saveStoredSnapshot
} from "../lib/storage";

type Tool =
  | "select"
  | "pan"
  | "marker"
  | "label"
  | "line"
  | "freehand"
  | "area"
  | "reveal";

type ExportAudience = "dm" | "player";

type ViewState = {
  x: number;
  y: number;
  scale: number;
};

type DraftPath = {
  type: "line" | "freehand";
  points: Point[];
};

type DragState =
  | {
      kind: "pan";
      clientX: number;
      clientY: number;
    }
  | {
      kind: "object";
      id: string;
      start: Point;
      original: MapObject;
    };

type EditableObjectUpdates = Partial<{
  name: string;
  color: string;
  category: MapObjectCategory;
  dmVisible: boolean;
  playerVisible: boolean;
  notes: string;
  radius: number;
  text: string;
  fontSize: number;
  strokeWidth: number;
  fillOpacity: number;
  isReveal: boolean;
  handout: HandoutContent | null;
}>;

type MapEditorProps = {
  initialTitle?: string;
  initialImage?: MapImageState | null;
  initialObjects?: MapObject[];
  onSave?: (snapshot: CampaignMapSnapshot) => Promise<void>;
  onUploadImage?: (file: File) => Promise<void>;
  saveLabel?: string;
};

const DEFAULT_WORLD = {
  width: 1600,
  height: 1000
};

const EMPTY_MAP_OBJECTS: MapObject[] = [];

const TOOLS: Array<{ id: Tool; label: string; icon: LucideIcon }> = [
  { id: "select", label: "Select", icon: MousePointer2 },
  { id: "pan", label: "Pan", icon: Move },
  { id: "marker", label: "Location", icon: MapPin },
  { id: "label", label: "Map Text", icon: Type },
  { id: "line", label: "Route", icon: Waypoints },
  { id: "freehand", label: "Trail", icon: PenLine },
  { id: "area", label: "Area", icon: Hexagon },
  { id: "reveal", label: "Reveal", icon: Sparkles }
];

const AREA_CLOSE_DISTANCE = 14;

const AREA_TOOLS: Tool[] = ["area", "reveal"];

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getObjectIcon(type: MapObject["type"]) {
  if (type === "marker") {
    return <MapPin size={16} />;
  }

  if (type === "label") {
    return <Type size={16} />;
  }

  if (type === "polyline") {
    return <Waypoints size={16} />;
  }

  if (type === "area") {
    return <Hexagon size={16} />;
  }

  return <PenLine size={16} />;
}

function makeSnapshot(
  title: string,
  image: MapImageState | null,
  objects: MapObject[],
  view: ViewState,
  fogEnabled: boolean
): CampaignMapSnapshot {
  return {
    title,
    image,
    objects,
    fogEnabled,
    viewport: view
  };
}

function getRevealAreas(objects: MapObject[]) {
  return objects.filter(
    (object): object is AreaObject =>
      object.type === "area" && Boolean(object.isReveal)
  );
}

function drawFog(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  reveals: AreaObject[],
  opacity: number
) {
  // Render fog on its own layer and punch reveal holes so the underlying map
  // and notes are not erased.
  const fog = document.createElement("canvas");
  fog.width = Math.max(1, Math.floor(width));
  fog.height = Math.max(1, Math.floor(height));
  const fogContext = fog.getContext("2d");

  if (!fogContext) {
    return;
  }

  fogContext.fillStyle = "#04060f";
  fogContext.globalAlpha = opacity;
  fogContext.fillRect(0, 0, fog.width, fog.height);
  fogContext.globalAlpha = 1;
  fogContext.globalCompositeOperation = "destination-out";

  reveals.forEach((area) => {
    const [first, ...rest] = area.points;

    if (!first) {
      return;
    }

    fogContext.beginPath();
    fogContext.moveTo(first.x, first.y);
    rest.forEach((point) => fogContext.lineTo(point.x, point.y));
    fogContext.closePath();
    fogContext.fill();
  });

  context.drawImage(fog, 0, 0, width, height);
}

async function loadImageElement(src: string) {
  const image = new Image();
  const loaded = new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("Image could not be decoded."));
  });
  image.src = src;

  try {
    await image.decode();
  } catch {
    await loaded;
  }

  return image;
}

function drawGridBackground(
  context: CanvasRenderingContext2D,
  width: number,
  height: number
) {
  context.fillStyle = "#10172f";
  context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(167, 139, 250, 0.14)";
  context.lineWidth = 1;

  for (let x = 0; x <= width; x += 80) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }

  for (let y = 0; y <= height; y += 80) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }
}

function drawExportObject(
  context: CanvasRenderingContext2D,
  object: MapObject,
  audience: ExportAudience
) {
  const visible = audience === "player" ? object.playerVisible : object.dmVisible;

  if (!visible) {
    return;
  }

  const category = getCategoryMeta(object.category);

  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";

  if (object.type === "marker") {
    context.fillStyle = object.color;
    context.strokeStyle = "#f5f2ff";
    context.lineWidth = 4;
    context.beginPath();
    context.arc(object.x, object.y, object.radius, 0, Math.PI * 2);
    context.fill();
    context.stroke();

    context.font = "800 13px Arial, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineWidth = 3;
    context.strokeStyle = "rgba(19, 18, 14, 0.78)";
    context.fillStyle = "#f5f2ff";
    context.strokeText(category.shortLabel, object.x, object.y + 1);
    context.fillText(category.shortLabel, object.x, object.y + 1);

    context.font = "700 18px Arial, sans-serif";
    context.textAlign = "left";
    context.textBaseline = "alphabetic";
    context.lineWidth = 5;
    context.strokeStyle = "rgba(19, 18, 14, 0.82)";
    context.fillStyle = "#f5f2ff";
    context.strokeText(object.name, object.x + object.radius + 8, object.y + 6);
    context.fillText(object.name, object.x + object.radius + 8, object.y + 6);
  }

  if (object.type === "label") {
    context.font = `700 ${object.fontSize}px Arial, sans-serif`;
    context.lineWidth = 6;
    context.strokeStyle = "rgba(19, 18, 14, 0.82)";
    context.fillStyle = object.color;
    context.strokeText(object.text, object.x, object.y);
    context.fillText(object.text, object.x, object.y);
  }

  if (object.type === "polyline" || object.type === "freehand") {
    const [firstPoint, ...rest] = object.points;

    if (firstPoint) {
      context.strokeStyle = object.color;
      context.lineWidth = object.strokeWidth;
      context.setLineDash(object.category === "route" ? [18, 12] : []);
      context.beginPath();
      context.moveTo(firstPoint.x, firstPoint.y);
      rest.forEach((point) => context.lineTo(point.x, point.y));
      context.stroke();
    }
  }

  if (object.type === "area" && !object.isReveal) {
    const [firstPoint, ...rest] = object.points;

    if (firstPoint) {
      context.beginPath();
      context.moveTo(firstPoint.x, firstPoint.y);
      rest.forEach((point) => context.lineTo(point.x, point.y));
      context.closePath();
      context.globalAlpha = object.fillOpacity;
      context.fillStyle = object.color;
      context.fill();
      context.globalAlpha = 1;
      context.strokeStyle = object.color;
      context.lineWidth = object.strokeWidth;
      context.stroke();
    }
  }

  context.restore();
}

export function MapEditor({
  initialTitle = "D&D Campaign",
  initialImage = null,
  initialObjects = EMPTY_MAP_OBJECTS,
  onSave,
  onUploadImage,
  saveLabel = "Save"
}: MapEditorProps = {}) {
  const persistLocally = !onSave;
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const campaignFileInputRef = useRef<HTMLInputElement | null>(null);
  const handoutFileInputRef = useRef<HTMLInputElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);
  const hydratedRef = useRef(false);
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map());
  const pinchRef = useRef<{
    distance: number;
    view: ViewState;
    world: Point;
  } | null>(null);
  const [title, setTitle] = useState(initialTitle);
  const [image, setImage] = useState<MapImageState | null>(initialImage);
  const [objects, setObjects] = useState<MapObject[]>(initialObjects);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [activeCategory, setActiveCategory] =
    useState<MapObjectCategory>("settlement");
  const [view, setView] = useState<ViewState>({ x: 0, y: 0, scale: 1 });
  const [draftPath, setDraftPath] = useState<DraftPath | null>(null);
  const [draftArea, setDraftArea] = useState<Point[] | null>(null);
  const [areaCursor, setAreaCursor] = useState<Point | null>(null);
  const [status, setStatus] = useState("Ready");
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [presentMode, setPresentMode] = useState(false);
  const [openHandoutId, setOpenHandoutId] = useState<string | null>(null);
  const [fogEnabled, setFogEnabled] = useState(false);

  const activeTool: Tool = presentMode ? "pan" : tool;

  useEffect(() => {
    setTitle(initialTitle);
  }, [initialTitle]);

  useEffect(() => {
    setImage(initialImage);
  }, [initialImage]);

  useEffect(() => {
    setObjects(initialObjects);
    setSelectedId(null);
  }, [initialObjects]);

  // Restore the most recent local draft once on mount (browser-only mode).
  useEffect(() => {
    if (!persistLocally) {
      hydratedRef.current = true;
      return;
    }

    const stored = loadStoredSnapshot();

    if (stored) {
      setTitle(stored.title);
      setImage(stored.image);
      setObjects(stored.objects);
      setFogEnabled(Boolean(stored.fogEnabled));
      setSelectedId(null);
      setStatus("Restored local campaign");
    }

    hydratedRef.current = true;
  }, [persistLocally]);

  // Debounced autosave of the working draft to local storage.
  useEffect(() => {
    if (!persistLocally || !hydratedRef.current) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      const result = saveStoredSnapshot(
        makeSnapshot(title, image, objects, view, fogEnabled)
      );

      if (!result.ok && result.error) {
        setStatus(result.error);
      }
    }, 600);

    return () => window.clearTimeout(handle);
  }, [persistLocally, title, image, objects, view, fogEnabled]);

  useEffect(() => {
    if (!exportMenuOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      if (exportMenuRef.current?.contains(event.target as Node)) {
        return;
      }

      setExportMenuOpen(false);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setExportMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [exportMenuOpen]);

  const worldSize = useMemo(
    () => ({
      width: image?.width ?? DEFAULT_WORLD.width,
      height: image?.height ?? DEFAULT_WORLD.height
    }),
    [image]
  );

  const selectedObject = objects.find((object) => object.id === selectedId);
  const dmVisibleObjects = objects.filter((object) => object.dmVisible);
  const playerVisibleObjects = objects.filter((object) => object.playerVisible);
  const visibleObjects = presentMode ? playerVisibleObjects : dmVisibleObjects;
  const revealAreas = getRevealAreas(objects);
  const openHandoutObject = openHandoutId
    ? objects.find((object) => object.id === openHandoutId) ?? null
    : null;

  const screenToWorld = useCallback(
    (event: ReactPointerEvent) => {
      const bounds = viewportRef.current?.getBoundingClientRect();

      if (!bounds) {
        return { x: 0, y: 0 };
      }

      return {
        x: (event.clientX - bounds.left - view.x) / view.scale,
        y: (event.clientY - bounds.top - view.y) / view.scale
      };
    },
    [view]
  );

  const fitToViewport = useCallback(() => {
    const bounds = viewportRef.current?.getBoundingClientRect();

    if (!bounds) {
      return;
    }

    const padding = 64;
    const nextScale = clamp(
      Math.min(
        (bounds.width - padding) / worldSize.width,
        (bounds.height - padding) / worldSize.height
      ),
      0.08,
      5
    );

    setView({
      scale: nextScale,
      x: (bounds.width - worldSize.width * nextScale) / 2,
      y: (bounds.height - worldSize.height * nextScale) / 2
    });
  }, [worldSize.height, worldSize.width]);

  useEffect(() => {
    fitToViewport();
  }, [fitToViewport]);

  useEffect(() => {
    const viewport = viewportRef.current;

    if (!viewport) {
      return undefined;
    }

    const observer = new ResizeObserver(() => fitToViewport());
    observer.observe(viewport);

    return () => observer.disconnect();
  }, [fitToViewport]);

  const handleImageFile = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) {
      setStatus("Choose an image file");
      return;
    }

    if (onUploadImage) {
      setStatus(`Uploading ${file.name}`);
      try {
        await onUploadImage(file);
        setStatus(`Uploaded ${file.name}`);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Upload failed");
      }
      return;
    }

    const reader = new FileReader();

    reader.onload = () => {
      const src = String(reader.result);
      const probe = new Image();

      probe.onload = () => {
        setImage({
          name: file.name,
          src,
          width: probe.naturalWidth,
          height: probe.naturalHeight
        });
        setStatus(`Loaded ${file.name}`);
      };

      probe.onerror = () => setStatus("Image could not be loaded");
      probe.src = src;
    };

    reader.onerror = () => setStatus("Image could not be read");
    reader.readAsDataURL(file);
  }, [onUploadImage]);

  const addMarker = useCallback(
    (point: Point) => {
      const marker = createMarker(objects, point, activeCategory);
      setObjects((currentObjects) => [...currentObjects, marker]);
      setSelectedId(marker.id);
      setStatus(`Added ${marker.name}`);
    },
    [activeCategory, objects]
  );

  const addLabel = useCallback(
    (point: Point) => {
      const label = createLabel(objects, point, activeCategory);
      setObjects((currentObjects) => [...currentObjects, label]);
      setSelectedId(label.id);
      setStatus(`Added ${label.name}`);
    },
    [activeCategory, objects]
  );

  const addPathObject = useCallback(
    (path: DraftPath) => {
      const nextPath = createPathFromDraft(objects, path);

      if (!nextPath) {
        return;
      }

      setObjects((currentObjects) => [...currentObjects, nextPath]);
      setSelectedId(nextPath.id);
      setStatus(`Added ${nextPath.name}`);
    },
    [objects]
  );

  const finishArea = useCallback(() => {
    const isReveal = tool === "reveal";
    setDraftArea((currentDraft) => {
      if (currentDraft) {
        const area = createArea(objects, currentDraft, activeCategory, isReveal);

        if (area) {
          setObjects((currentObjects) => [...currentObjects, area]);
          setSelectedId(area.id);
          setStatus(`Added ${area.name}`);

          if (isReveal) {
            setFogEnabled(true);
          }
        }
      }

      return null;
    });
    setAreaCursor(null);
  }, [activeCategory, objects, tool]);

  const cancelArea = useCallback(() => {
    setDraftArea(null);
    setAreaCursor(null);
  }, []);

  // Drop any in-progress area when the tool changes or presentation starts.
  useEffect(() => {
    if (!AREA_TOOLS.includes(tool) || presentMode) {
      setDraftArea(null);
      setAreaCursor(null);
    }
  }, [tool, presentMode]);

  // Keyboard shortcuts for area drawing, handouts, and presentation.
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter" && draftArea) {
        event.preventDefault();
        finishArea();
        return;
      }

      if (event.key !== "Escape") {
        return;
      }

      if (openHandoutId) {
        setOpenHandoutId(null);
        return;
      }

      if (draftArea) {
        cancelArea();
        return;
      }

      if (presentMode) {
        setPresentMode(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [cancelArea, draftArea, finishArea, openHandoutId, presentMode]);

  const updateSelectedObject = useCallback((updates: EditableObjectUpdates) => {
    setObjects((currentObjects) =>
      currentObjects.map((object) => {
        if (object.id !== selectedId) {
          return object;
        }

        const nextObject = { ...object, ...updates } as MapObject;

        if (updates.category && !updates.color) {
          nextObject.color = getCategoryMeta(updates.category).color;
        }

        if (updates.dmVisible === false) {
          nextObject.playerVisible = false;
        }

        if (updates.playerVisible === true) {
          nextObject.dmVisible = true;
        }

        return nextObject;
      })
    );
  }, [selectedId]);

  const setHandoutText = (text: string) => {
    if (!selectedObject) {
      return;
    }

    const image = selectedObject.handout?.image ?? null;
    updateSelectedObject({
      handout: text || image ? { text, image } : null
    });
  };

  const attachHandoutImage = (file: File) => {
    if (!file.type.startsWith("image/")) {
      setStatus("Choose an image file for the handout");
      return;
    }

    const currentText = selectedObject?.handout?.text ?? "";
    const reader = new FileReader();

    reader.onload = () => {
      const src = String(reader.result);
      const probe = new Image();

      probe.onload = () => {
        updateSelectedObject({
          handout: {
            text: currentText,
            image: {
              name: file.name,
              src,
              width: probe.naturalWidth,
              height: probe.naturalHeight
            }
          }
        });
        setStatus(`Handout image attached (${file.name})`);
      };

      probe.onerror = () => setStatus("Handout image could not be loaded");
      probe.src = src;
    };

    reader.onerror = () => setStatus("Handout image could not be read");
    reader.readAsDataURL(file);
  };

  const clearHandout = () => {
    updateSelectedObject({ handout: null });
  };

  const startPan = (event: ReactPointerEvent, target: Element) => {
    dragRef.current = {
      kind: "pan",
      clientX: event.clientX,
      clientY: event.clientY
    };
    target.setPointerCapture(event.pointerId);
  };

  // Track touch points; a second finger starts a pinch-to-zoom/pan gesture
  // and cancels any in-progress single-pointer drawing.
  const trackPointerForGesture = (event: ReactPointerEvent) => {
    pointersRef.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY
    });

    if (pointersRef.current.size !== 2) {
      return false;
    }

    const bounds = viewportRef.current?.getBoundingClientRect();
    const points = [...pointersRef.current.values()];

    if (bounds) {
      const a = { x: points[0].x - bounds.left, y: points[0].y - bounds.top };
      const b = { x: points[1].x - bounds.left, y: points[1].y - bounds.top };
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };

      pinchRef.current = {
        distance: Math.hypot(b.x - a.x, b.y - a.y) || 1,
        view: { ...view },
        world: {
          x: (mid.x - view.x) / view.scale,
          y: (mid.y - view.y) / view.scale
        }
      };
    }

    dragRef.current = null;
    setDraftPath(null);
    setDraftArea(null);
    setAreaCursor(null);
    return true;
  };

  const releaseGesturePointer = (event: ReactPointerEvent) => {
    pointersRef.current.delete(event.pointerId);

    if (pointersRef.current.size < 2) {
      pinchRef.current = null;
    }
  };

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) {
      return;
    }

    if (trackPointerForGesture(event)) {
      return;
    }

    const point = screenToWorld(event);

    if (activeTool === "pan") {
      startPan(event, event.currentTarget);
      return;
    }

    if (activeTool === "marker") {
      addMarker(point);
      return;
    }

    if (activeTool === "label") {
      addLabel(point);
      return;
    }

    if (activeTool === "line") {
      setDraftPath({ type: "line", points: [point, point] });
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (activeTool === "freehand") {
      setDraftPath({ type: "freehand", points: [point] });
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (AREA_TOOLS.includes(activeTool)) {
      // Click near the first vertex to close, otherwise drop a new vertex.
      if (draftArea && draftArea.length >= 3) {
        const first = draftArea[0];
        const closeDistance = AREA_CLOSE_DISTANCE / view.scale;

        if (Math.hypot(point.x - first.x, point.y - first.y) <= closeDistance) {
          finishArea();
          return;
        }
      }

      setDraftArea((currentDraft) =>
        currentDraft ? [...currentDraft, point] : [point]
      );
      setAreaCursor(point);
      setStatus(
        activeTool === "reveal"
          ? "Reveal: click the first point or press Enter to finish"
          : "Area: click the first point or press Enter to finish"
      );
      return;
    }

    setSelectedId(null);
  };

  const handleObjectPointerDown = (
    event: ReactPointerEvent<SVGGElement>,
    object: MapObject
  ) => {
    if (event.button !== 0) {
      return;
    }

    event.stopPropagation();

    if (trackPointerForGesture(event)) {
      return;
    }

    if (presentMode) {
      if (hasHandout(object)) {
        setOpenHandoutId(object.id);
      } else {
        startPan(event, svgRef.current ?? event.currentTarget);
      }
      return;
    }

    if (AREA_TOOLS.includes(activeTool)) {
      // Forward to the canvas handler so vertices can be placed over objects.
      handlePointerDown(
        event as unknown as ReactPointerEvent<SVGSVGElement>
      );
      return;
    }

    if (activeTool === "pan") {
      startPan(event, svgRef.current ?? event.currentTarget);
      return;
    }

    setSelectedId(object.id);

    if (activeTool !== "select") {
      return;
    }

    dragRef.current = {
      kind: "object",
      id: object.id,
      start: screenToWorld(event),
      original: object
    };
    svgRef.current?.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (pinchRef.current) {
      if (pointersRef.current.has(event.pointerId)) {
        pointersRef.current.set(event.pointerId, {
          x: event.clientX,
          y: event.clientY
        });
      }

      const points = [...pointersRef.current.values()];
      const bounds = viewportRef.current?.getBoundingClientRect();

      if (points.length >= 2 && bounds) {
        const a = { x: points[0].x - bounds.left, y: points[0].y - bounds.top };
        const b = { x: points[1].x - bounds.left, y: points[1].y - bounds.top };
        const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        const distance = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        const start = pinchRef.current;
        const nextScale = clamp(
          start.view.scale * (distance / start.distance),
          0.08,
          8
        );

        setView({
          scale: nextScale,
          x: mid.x - start.world.x * nextScale,
          y: mid.y - start.world.y * nextScale
        });
      }

      return;
    }

    const activeDrag = dragRef.current;

    if (activeDrag?.kind === "pan") {
      const dx = event.clientX - activeDrag.clientX;
      const dy = event.clientY - activeDrag.clientY;
      activeDrag.clientX = event.clientX;
      activeDrag.clientY = event.clientY;
      setView((currentView) => ({
        ...currentView,
        x: currentView.x + dx,
        y: currentView.y + dy
      }));
      return;
    }

    if (activeDrag?.kind === "object") {
      const point = screenToWorld(event);
      const dx = point.x - activeDrag.start.x;
      const dy = point.y - activeDrag.start.y;

      setObjects((currentObjects) =>
        currentObjects.map((object) =>
          object.id === activeDrag.id
            ? moveObject(activeDrag.original, dx, dy)
            : object
        )
      );
      return;
    }

    if (AREA_TOOLS.includes(activeTool) && draftArea) {
      setAreaCursor(screenToWorld(event));
      return;
    }

    if (!draftPath) {
      return;
    }

    const point = screenToWorld(event);

    if (draftPath.type === "line") {
      setDraftPath({
        ...draftPath,
        points: [draftPath.points[0], point]
      });
      return;
    }

    const previous = draftPath.points[draftPath.points.length - 1];

    if (!previous || Math.hypot(point.x - previous.x, point.y - previous.y) > 4) {
      setDraftPath({
        ...draftPath,
        points: [...draftPath.points, point]
      });
    }
  };

  const handlePointerUp = (event: ReactPointerEvent<SVGSVGElement>) => {
    const wasPinching = pinchRef.current !== null;
    releaseGesturePointer(event);

    if (!wasPinching && draftPath) {
      addPathObject(draftPath);
      setDraftPath(null);
    }

    dragRef.current = null;

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleWheel = (event: ReactWheelEvent<HTMLDivElement>) => {
    event.preventDefault();

    const bounds = viewportRef.current?.getBoundingClientRect();

    if (!bounds) {
      return;
    }

    const viewportPoint = {
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top
    };
    const nextScale = clamp(
      view.scale * (event.deltaY > 0 ? 0.9 : 1.1),
      0.08,
      8
    );
    const worldPoint = {
      x: (viewportPoint.x - view.x) / view.scale,
      y: (viewportPoint.y - view.y) / view.scale
    };

    setView({
      scale: nextScale,
      x: viewportPoint.x - worldPoint.x * nextScale,
      y: viewportPoint.y - worldPoint.y * nextScale
    });
  };

  const zoomBy = (multiplier: number) => {
    const bounds = viewportRef.current?.getBoundingClientRect();

    if (!bounds) {
      return;
    }

    const viewportPoint = {
      x: bounds.width / 2,
      y: bounds.height / 2
    };
    const nextScale = clamp(view.scale * multiplier, 0.08, 8);
    const worldPoint = {
      x: (viewportPoint.x - view.x) / view.scale,
      y: (viewportPoint.y - view.y) / view.scale
    };

    setView({
      scale: nextScale,
      x: viewportPoint.x - worldPoint.x * nextScale,
      y: viewportPoint.y - worldPoint.y * nextScale
    });
  };

  const drawMapSurface = useCallback(
    async (context: CanvasRenderingContext2D, audience: ExportAudience) => {
      if (image) {
        const exportImage = await loadImageElement(image.src);
        context.drawImage(exportImage, 0, 0, worldSize.width, worldSize.height);
      } else {
        drawGridBackground(context, worldSize.width, worldSize.height);
      }

      objects.forEach((object) => drawExportObject(context, object, audience));

      // Player exports hide everything outside the revealed regions.
      if (audience === "player" && fogEnabled) {
        drawFog(
          context,
          worldSize.width,
          worldSize.height,
          getRevealAreas(objects),
          0.94
        );
      }
    },
    [fogEnabled, image, objects, worldSize.height, worldSize.width]
  );

  const renderViewportCanvas = useCallback(
    async (audience: ExportAudience) => {
    const bounds = viewportRef.current?.getBoundingClientRect();

    if (!bounds) {
      return null;
    }

    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.floor(bounds.width * pixelRatio));
    canvas.height = Math.max(1, Math.floor(bounds.height * pixelRatio));
    const context = canvas.getContext("2d");

    if (!context) {
      return null;
    }

    context.scale(pixelRatio, pixelRatio);
    context.fillStyle = "#080d1f";
    context.fillRect(0, 0, bounds.width, bounds.height);
    context.save();
    context.translate(view.x, view.y);
    context.scale(view.scale, view.scale);
    await drawMapSurface(context, audience);
    context.restore();
    return canvas;
    },
    [drawMapSurface, view.scale, view.x, view.y]
  );

  const renderFullMapCanvas = useCallback(
    async (audience: ExportAudience) => {
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.floor(worldSize.width));
      canvas.height = Math.max(1, Math.floor(worldSize.height));
      const context = canvas.getContext("2d");

      if (!context) {
        return null;
      }

      context.fillStyle = "#080d1f";
      context.fillRect(0, 0, canvas.width, canvas.height);
      await drawMapSurface(context, audience);
      return canvas;
    },
    [drawMapSurface, worldSize.height, worldSize.width]
  );

  const getExportBaseName = () => exportBaseName(title);

  const downloadCanvasAsPng = (canvas: HTMLCanvasElement, filename: string) => {
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = filename;
    link.click();
  };

  const exportPng = async () => {
    setStatus("Rendering PNG");
    const canvas = await renderViewportCanvas("dm");

    if (!canvas) {
      setStatus("PNG export is not available");
      return;
    }

    downloadCanvasAsPng(canvas, `${getExportBaseName()}-view.png`);
    setStatus("PNG exported");
  };

  const exportPdf = async () => {
    setStatus("Rendering PDF");
    const canvas = await renderViewportCanvas("dm");

    if (!canvas) {
      setStatus("PDF export is not available");
      return;
    }

    downloadCanvasAsPdf(
      canvas,
      `${getExportBaseName()}-view.pdf`
    );
    setStatus("PDF exported");
  };

  const exportFullMapPng = async () => {
    setStatus("Rendering full map");
    const canvas = await renderFullMapCanvas("dm");

    if (!canvas) {
      setStatus("Full-map export is not available");
      return;
    }

    downloadCanvasAsPng(canvas, `${getExportBaseName()}-full-map.png`);
    setStatus("Full map PNG exported");
  };

  const exportPlayerMapPng = async () => {
    setStatus("Rendering player map");
    const canvas = await renderFullMapCanvas("player");

    if (!canvas) {
      setStatus("Player-map export is not available");
      return;
    }

    downloadCanvasAsPng(canvas, `${getExportBaseName()}-player-map.png`);
    setStatus(
      playerVisibleObjects.length === 0
        ? "Player map exported (no shared notes yet)"
        : "Player map PNG exported"
    );
  };

  const exportPlayerMapPdf = async () => {
    setStatus("Rendering player map");
    const canvas = await renderFullMapCanvas("player");

    if (!canvas) {
      setStatus("Player-map export is not available");
      return;
    }

    downloadCanvasAsPdf(canvas, `${getExportBaseName()}-player-map.pdf`);
    setStatus("Player map PDF exported");
  };

  const saveCampaignFile = () => {
    downloadCampaignFile(
      makeSnapshot(title, image, objects, view, fogEnabled),
      `${getExportBaseName()}-campaign.json`
    );
    setStatus("Campaign file saved");
  };

  const loadCampaignFile = async (file: File) => {
    setStatus(`Loading ${file.name}`);

    try {
      const snapshot = await readCampaignFile(file);
      setTitle(snapshot.title);
      setImage(snapshot.image);
      setObjects(snapshot.objects);
      setFogEnabled(Boolean(snapshot.fogEnabled));
      setSelectedId(null);
      setStatus(`Loaded ${file.name}`);
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Campaign file is invalid"
      );
    }
  };

  const saveDraft = async () => {
    setStatus("Saving…");

    try {
      const snapshot = makeSnapshot(title, image, objects, view, fogEnabled);
      if (onSave) {
        await onSave(snapshot);
        setStatus(`Saved ${new Date().toLocaleTimeString()}`);
        return;
      }

      const result = saveStoredSnapshot(snapshot);
      setStatus(
        result.ok
          ? `Saved locally ${new Date().toLocaleTimeString()}`
          : result.error ?? "Save failed"
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
    }
  };

  const resetCampaign = () => {
    if (
      typeof window !== "undefined" &&
      !window.confirm("Clear the current map and the saved local draft?")
    ) {
      return;
    }

    clearStoredSnapshot();
    setObjects(EMPTY_MAP_OBJECTS);
    setImage(null);
    setSelectedId(null);
    setStatus("Cleared local campaign");
  };

  const deleteSelectedObject = () => {
    if (!selectedId) {
      return;
    }

    setObjects((currentObjects) =>
      currentObjects.filter((object) => object.id !== selectedId)
    );
    setSelectedId(null);
    setStatus("Map note removed");
  };

  const toggleDmVisibility = (id: string) => {
    setObjects((currentObjects) =>
      currentObjects.map((object) => {
        if (object.id !== id) {
          return object;
        }

        const dmVisible = !object.dmVisible;

        return {
          ...object,
          dmVisible,
          playerVisible: dmVisible ? object.playerVisible : false
        };
      })
    );
  };

  const togglePlayerVisibility = (id: string) => {
    setObjects((currentObjects) =>
      currentObjects.map((object) => {
        if (object.id !== id) {
          return object;
        }

        const playerVisible = !object.playerVisible;

        return {
          ...object,
          dmVisible: playerVisible ? true : object.dmVisible,
          playerVisible
        };
      })
    );
  };

  const renderPath = (
    object: PathObject | DraftPath,
    color: string,
    strokeWidth: number,
    className?: string,
    dashArray?: string
  ) => {
    const points = object.points
      .map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`)
      .join(" ");

    return (
      <polyline
        className={className}
        fill="none"
        points={points}
        stroke={color}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={dashArray}
        strokeWidth={strokeWidth}
      />
    );
  };

  return (
    <main className={`editor-shell ${presentMode ? "presenting" : ""}`}>
      <header className="topbar">
        <div className="brand-area">
          <Layers3 size={22} />
          <input
            aria-label="Campaign title"
            className="title-input"
            onChange={(event) => setTitle(event.target.value)}
            readOnly={presentMode}
            value={title}
          />
          {presentMode ? <span className="present-badge">Player view</span> : null}
        </div>

        <input
          ref={fileInputRef}
          accept="image/*"
          className="hidden-input"
          onChange={(event) => {
            const file = event.target.files?.[0];

            if (file) {
              handleImageFile(file);
            }
          }}
          type="file"
        />
        <input
          ref={campaignFileInputRef}
          accept="application/json,.json"
          className="hidden-input"
          onChange={(event) => {
            const file = event.target.files?.[0];

            if (file) {
              void loadCampaignFile(file);
            }

            event.target.value = "";
          }}
          type="file"
        />
        <input
          ref={handoutFileInputRef}
          accept="image/*"
          className="hidden-input"
          onChange={(event) => {
            const file = event.target.files?.[0];

            if (file) {
              attachHandoutImage(file);
            }

            event.target.value = "";
          }}
          type="file"
        />

        {!presentMode ? (
          <div className="toolbar" aria-label="Map tools">
            <button
              className="tool-button map-option-button"
              onClick={() => fileInputRef.current?.click()}
              title="Load image"
              type="button"
            >
              <ImagePlus size={18} />
              <span>Load</span>
            </button>

            <label className="category-select-label">
              <MapPin size={16} />
              <select
                aria-label="New map note category"
                onChange={(event) =>
                  setActiveCategory(event.target.value as MapObjectCategory)
                }
                value={activeCategory}
              >
                {CATEGORY_ORDER.map((category) => (
                  <option key={category} value={category}>
                    {getCategoryMeta(category).label}
                  </option>
                ))}
              </select>
            </label>

            <div className="segmented-tools">
              {TOOLS.map(({ id, label, icon: Icon }) => (
                <button
                  aria-pressed={tool === id}
                  className="tool-button icon-tool"
                  key={id}
                  onClick={() => setTool(id)}
                  title={label}
                  type="button"
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="toolbar right-toolbar">
          <button
            className="tool-button icon-only"
            onClick={() => zoomBy(0.85)}
            title="Zoom out"
            type="button"
          >
            <ZoomOut size={18} />
          </button>
          <span className="zoom-readout">{Math.round(view.scale * 100)}%</span>
          <button
            className="tool-button icon-only"
            onClick={() => zoomBy(1.18)}
            title="Zoom in"
            type="button"
          >
            <ZoomIn size={18} />
          </button>
          <button
            className="tool-button icon-only"
            onClick={fitToViewport}
            title="Fit image"
            type="button"
          >
            <Maximize2 size={18} />
          </button>
          {presentMode ? (
            <button
              className="tool-button map-option-button present-exit"
              onClick={() => setPresentMode(false)}
              title="Exit player view"
              type="button"
            >
              <X size={18} />
              <span>Exit</span>
            </button>
          ) : (
            <>
              <button
                aria-pressed={fogEnabled}
                className="tool-button icon-only fog-toggle"
                onClick={() => {
                  setFogEnabled((enabled) => !enabled);
                  setStatus(
                    fogEnabled ? "Fog of war off" : "Fog of war on"
                  );
                }}
                title={
                  fogEnabled
                    ? "Fog of war on (players see only revealed areas)"
                    : "Fog of war off"
                }
                type="button"
              >
                <CloudFog size={18} />
              </button>
              {persistLocally ? (
                <button
                  className="tool-button icon-only"
                  onClick={resetCampaign}
                  title="New campaign (clears the saved local draft)"
                  type="button"
                >
                  <FilePlus2 size={18} />
                </button>
              ) : null}
              <button
                className="tool-button map-option-button"
                onClick={saveDraft}
                title={persistLocally ? "Save to this browser" : "Save draft"}
                type="button"
              >
                <Save size={18} />
                <span>{saveLabel}</span>
              </button>
              <button
                className="tool-button map-option-button"
                onClick={() => {
                  setSelectedId(null);
                  setExportMenuOpen(false);
                  setPresentMode(true);
                  setStatus("Player view — only shared notes are shown");
                }}
                title="Player view for screen sharing"
                type="button"
              >
                <MonitorPlay size={18} />
                <span>Present</span>
              </button>
            </>
          )}
          <div className="export-menu" ref={exportMenuRef}>
            <button
              aria-label="Export options"
              aria-expanded={exportMenuOpen}
              aria-haspopup="menu"
              className="tool-button map-option-button"
              onClick={() => setExportMenuOpen((open) => !open)}
              title="Export options"
              type="button"
            >
              <Download size={18} />
              <span>Export</span>
            </button>
            {exportMenuOpen ? (
              <div className="export-menu-popover" role="menu">
                <span className="export-menu-group">DM current view</span>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    void exportPng();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Download size={16} />
                  <span>View PNG</span>
                </button>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    void exportPdf();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <FileText size={16} />
                  <span>View PDF</span>
                </button>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    void exportFullMapPng();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Maximize2 size={16} />
                  <span>Full map PNG</span>
                </button>

                <span className="export-menu-group">Player handout</span>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    void exportPlayerMapPng();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Users size={16} />
                  <span>Player PNG</span>
                </button>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    void exportPlayerMapPdf();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <FileText size={16} />
                  <span>Player PDF</span>
                </button>

                <span className="export-menu-group">Campaign file</span>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    saveCampaignFile();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Save size={16} />
                  <span>Save .json</span>
                </button>
                <button
                  onClick={() => {
                    setExportMenuOpen(false);
                    campaignFileInputRef.current?.click();
                  }}
                  role="menuitem"
                  type="button"
                >
                  <FolderOpen size={16} />
                  <span>Load .json</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <section className="workspace">
        {!presentMode ? (
        <aside className="sidebar" aria-label="Known locations and map notes">
          <div className="sidebar-section">
            <div className="section-heading">
              <Layers3 size={17} />
              <h2>Known Locations</h2>
              <span>
                {dmVisibleObjects.length}/{objects.length} DM
              </span>
            </div>

            <div className="object-list">
              {objects.length === 0 ? (
                <div className="empty-list">No known locations or notes</div>
              ) : (
                [...objects].reverse().map((object) => (
                  <div
                    className={`object-row ${
                      selectedId === object.id ? "selected" : ""
                    } ${!object.dmVisible ? "muted" : ""}`}
                    key={object.id}
                  >
                    <button
                      className="object-main"
                      onClick={() => setSelectedId(object.id)}
                      type="button"
                    >
                      <span
                        className="category-mark"
                        style={{ color: object.color }}
                      >
                        {getCategoryMeta(object.category).shortLabel}
                      </span>
                      {getObjectIcon(object.type)}
                      <span className="object-copy">
                        <span className="object-name-row">
                          {getObjectDisplayName(object)}
                          {hasHandout(object) ? (
                            <Paperclip className="handout-flag" size={12} />
                          ) : null}
                        </span>
                        <small>{getCategoryMeta(object.category).label}</small>
                      </span>
                    </button>
                    <button
                      className="icon-action"
                      onClick={() => toggleDmVisibility(object.id)}
                      title={
                        object.dmVisible
                          ? "Hide from DM map"
                          : "Show on DM map"
                      }
                      type="button"
                    >
                      {object.dmVisible ? <Eye size={16} /> : <EyeOff size={16} />}
                    </button>
                    <button
                      className="icon-action"
                      onClick={() => togglePlayerVisibility(object.id)}
                      title={
                        object.playerVisible
                          ? "Hide from players"
                          : "Show to players"
                      }
                      type="button"
                    >
                      <Users
                        className={object.playerVisible ? undefined : "muted-icon"}
                        size={16}
                      />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="sidebar-section properties-section">
            <div className="section-heading">
              <Plus size={17} />
              <h2>Map Note</h2>
              <span>{playerVisibleObjects.length} shared</span>
            </div>

            {selectedObject ? (
              <div className="properties-form">
                <label>
                  <span>Name</span>
                  <input
                    onChange={(event) =>
                      updateSelectedObject({ name: event.target.value })
                    }
                    value={selectedObject.name}
                  />
                </label>

                <label>
                  <span>Category</span>
                  <select
                    onChange={(event) =>
                      updateSelectedObject({
                        category: event.target.value as MapObjectCategory
                      })
                    }
                    value={selectedObject.category}
                  >
                    {CATEGORY_ORDER.map((category) => (
                      <option key={category} value={category}>
                        {getCategoryMeta(category).label}
                      </option>
                    ))}
                  </select>
                </label>

                {selectedObject.type === "label" ? (
                  <label>
                    <span>Text</span>
                    <input
                      onChange={(event) =>
                        updateSelectedObject({ text: event.target.value })
                      }
                      value={selectedObject.text}
                    />
                  </label>
                ) : null}

                <label>
                  <span>Notes</span>
                  <textarea
                    onChange={(event) =>
                      updateSelectedObject({ notes: event.target.value })
                    }
                    rows={3}
                    value={selectedObject.notes}
                  />
                </label>

                <div className="visibility-controls">
                  <button
                    aria-pressed={selectedObject.dmVisible}
                    className="visibility-toggle"
                    onClick={() =>
                      updateSelectedObject({
                        dmVisible: !selectedObject.dmVisible
                      })
                    }
                    type="button"
                  >
                    {selectedObject.dmVisible ? (
                      <Eye size={16} />
                    ) : (
                      <EyeOff size={16} />
                    )}
                    <span>DM map</span>
                  </button>
                  <button
                    aria-pressed={selectedObject.playerVisible}
                    className="visibility-toggle"
                    onClick={() =>
                      updateSelectedObject({
                        playerVisible: !selectedObject.playerVisible
                      })
                    }
                    type="button"
                  >
                    <Users size={16} />
                    <span>Players</span>
                  </button>
                </div>

                <label>
                  <span>Color</span>
                  <div className="swatches">
                    {OBJECT_COLORS.map((color) => (
                      <button
                        aria-label={`Set color ${color}`}
                        aria-pressed={selectedObject.color === color}
                        className="swatch"
                        key={color}
                        onClick={() => updateSelectedObject({ color })}
                        style={{ background: color }}
                        type="button"
                      />
                    ))}
                  </div>
                </label>

                {selectedObject.type === "marker" ? (
                  <label>
                    <span>Radius</span>
                    <input
                      max="42"
                      min="8"
                      onChange={(event) =>
                        updateSelectedObject({
                          radius: Number(event.target.value)
                        })
                      }
                      type="range"
                      value={selectedObject.radius}
                    />
                  </label>
                ) : null}

                {selectedObject.type === "label" ? (
                  <label>
                    <span>Size</span>
                    <input
                      max="72"
                      min="14"
                      onChange={(event) =>
                        updateSelectedObject({
                          fontSize: Number(event.target.value)
                        })
                      }
                      type="range"
                      value={selectedObject.fontSize}
                    />
                  </label>
                ) : null}

                {selectedObject.type === "polyline" ||
                selectedObject.type === "freehand" ||
                selectedObject.type === "area" ? (
                  <label>
                    <span>Stroke</span>
                    <input
                      max="18"
                      min="2"
                      onChange={(event) =>
                        updateSelectedObject({
                          strokeWidth: Number(event.target.value)
                        })
                      }
                      type="range"
                      value={selectedObject.strokeWidth}
                    />
                  </label>
                ) : null}

                {selectedObject.type === "area" &&
                !selectedObject.isReveal ? (
                  <label>
                    <span>Fill</span>
                    <input
                      max="80"
                      min="0"
                      onChange={(event) =>
                        updateSelectedObject({
                          fillOpacity: Number(event.target.value) / 100
                        })
                      }
                      type="range"
                      value={Math.round(selectedObject.fillOpacity * 100)}
                    />
                  </label>
                ) : null}

                {selectedObject.type === "area" ? (
                  <button
                    aria-pressed={Boolean(selectedObject.isReveal)}
                    className="visibility-toggle"
                    onClick={() => {
                      const nextReveal = !selectedObject.isReveal;
                      updateSelectedObject({ isReveal: nextReveal });

                      if (nextReveal) {
                        setFogEnabled(true);
                      }
                    }}
                    type="button"
                  >
                    <CloudFog size={16} />
                    <span>
                      {selectedObject.isReveal
                        ? "Fog reveal area"
                        : "Use as fog reveal"}
                    </span>
                  </button>
                ) : null}

                <div className="handout-section">
                  <div className="handout-heading">
                    <Paperclip size={14} />
                    <span>Player handout</span>
                  </div>
                  <p className="handout-hint">
                    Shown when you click this note in Present (player view).
                  </p>
                  <textarea
                    aria-label="Handout text"
                    onChange={(event) => setHandoutText(event.target.value)}
                    placeholder="Read-aloud text, riddle, letter…"
                    rows={2}
                    value={selectedObject.handout?.text ?? ""}
                  />
                  {selectedObject.handout?.image ? (
                    <div className="handout-image-row">
                      <img
                        alt="Handout"
                        className="handout-thumb"
                        src={selectedObject.handout.image.src}
                      />
                      <span className="handout-image-name">
                        {selectedObject.handout.image.name}
                      </span>
                    </div>
                  ) : null}
                  <div className="handout-actions">
                    <button
                      className="tool-button"
                      onClick={() => handoutFileInputRef.current?.click()}
                      type="button"
                    >
                      <ImagePlus size={15} />
                      <span>
                        {selectedObject.handout?.image ? "Replace" : "Image"}
                      </span>
                    </button>
                    {hasHandout(selectedObject) ? (
                      <button
                        className="tool-button"
                        onClick={clearHandout}
                        type="button"
                      >
                        <X size={15} />
                        <span>Clear</span>
                      </button>
                    ) : null}
                  </div>
                </div>

                <button
                  className="danger-button"
                  onClick={deleteSelectedObject}
                  type="button"
                >
                  <Trash2 size={16} />
                  <span>Delete</span>
                </button>
              </div>
            ) : (
              <div className="empty-list">Select a location or note</div>
            )}
          </div>
        </aside>
        ) : null}

        <div
          className="stage-viewport"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const file = event.dataTransfer.files?.[0];

            if (file) {
              handleImageFile(file);
            }
          }}
          onWheel={handleWheel}
          ref={viewportRef}
        >
          <div className="viewport-status">
            <span>{image?.name ?? "Untitled region map"}</span>
            <span>{status}</span>
          </div>

          <div
            className="stage-content"
            style={{
              height: worldSize.height,
              transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
              width: worldSize.width
            }}
          >
            {image ? (
              <img
                alt={image.name}
                className="map-image"
                draggable={false}
                src={image.src}
              />
            ) : (
              <div className="grid-map">
                <div className="empty-map-lockup">
                  <span>DM atlas</span>
                  <strong>Uncharted region</strong>
                  <small>Survey grid</small>
                </div>
              </div>
            )}

            <svg
              className="map-overlay"
              height={worldSize.height}
              onPointerCancel={handlePointerUp}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              ref={svgRef}
              viewBox={`0 0 ${worldSize.width} ${worldSize.height}`}
              width={worldSize.width}
            >
              <rect
                fill="transparent"
                height={worldSize.height}
                width={worldSize.width}
              />

              {visibleObjects.map((object) => {
                const isSelected = !presentMode && selectedId === object.id;
                const clickable = presentMode && hasHandout(object);
                const groupClass = `map-object ${
                  isSelected ? "selected" : ""
                } ${clickable ? "clickable" : ""}`;
                const category = getCategoryMeta(object.category);

                if (object.type === "area") {
                  // Reveal areas only cut holes in the fog; they are invisible
                  // to players and shown as a dashed outline to the DM.
                  if (object.isReveal && presentMode) {
                    return null;
                  }

                  const polygonPoints = object.points
                    .map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`)
                    .join(" ");

                  return (
                    <g
                      className={groupClass}
                      key={object.id}
                      onPointerDown={(event) =>
                        handleObjectPointerDown(event, object)
                      }
                    >
                      {isSelected ? (
                        <polygon
                          className="selection-path"
                          fill="none"
                          points={polygonPoints}
                        />
                      ) : null}
                      {object.isReveal ? (
                        <polygon
                          className="reveal-outline"
                          fill={object.color}
                          fillOpacity={0.06}
                          points={polygonPoints}
                          stroke={object.color}
                          strokeDasharray="14 10"
                          strokeLinejoin="round"
                          strokeWidth={object.strokeWidth}
                        />
                      ) : (
                        <polygon
                          fill={object.color}
                          fillOpacity={object.fillOpacity}
                          points={polygonPoints}
                          stroke={object.color}
                          strokeLinejoin="round"
                          strokeWidth={object.strokeWidth}
                        />
                      )}
                    </g>
                  );
                }

                if (object.type === "marker") {
                  return (
                    <g
                      className={groupClass}
                      key={object.id}
                      onPointerDown={(event) =>
                        handleObjectPointerDown(event, object)
                      }
                    >
                      {isSelected ? (
                        <circle
                          className="selection-ring"
                          cx={object.x}
                          cy={object.y}
                          r={object.radius + 8}
                        />
                      ) : null}
                      <circle
                        cx={object.x}
                        cy={object.y}
                        fill={object.color}
                        r={object.radius}
                      />
                      <circle
                        className="marker-core"
                        cx={object.x}
                        cy={object.y}
                        r={Math.max(7, object.radius * 0.48)}
                      />
                      <text
                        className="marker-glyph"
                        x={object.x}
                        y={object.y + 1}
                      >
                        {category.shortLabel}
                      </text>
                      <text
                        className="marker-label"
                        x={object.x + object.radius + 8}
                        y={object.y + 6}
                      >
                        {object.name}
                      </text>
                    </g>
                  );
                }

                if (object.type === "label") {
                  return (
                    <g
                      className={groupClass}
                      key={object.id}
                      onPointerDown={(event) =>
                        handleObjectPointerDown(event, object)
                      }
                    >
                      {isSelected ? (
                        <rect
                          className="label-selection"
                          height={object.fontSize + 12}
                          width={Math.max(
                            90,
                            object.text.length * object.fontSize * 0.55
                          )}
                          x={object.x - 8}
                          y={object.y - object.fontSize - 6}
                        />
                      ) : null}
                      <text
                        className="map-label"
                        fill={object.color}
                        fontSize={object.fontSize}
                        x={object.x}
                        y={object.y}
                      >
                        {object.text}
                      </text>
                    </g>
                  );
                }

                return (
                  <g
                    className={groupClass}
                    key={object.id}
                    onPointerDown={(event) =>
                      handleObjectPointerDown(event, object)
                    }
                  >
                    {isSelected
                      ? renderPath(
                          object,
                          "rgba(255, 245, 220, 0.9)",
                          object.strokeWidth + 8,
                          "selection-path"
                        )
                      : null}
                    {renderPath(
                      object,
                      object.color,
                      object.strokeWidth,
                      undefined,
                      object.category === "route" ? "18 12" : undefined
                    )}
                  </g>
                );
              })}

              {draftPath
                ? renderPath(
                    draftPath,
                    "#67e8f9",
                    draftPath.type === "line" ? 4 : 3,
                    "draft-path"
                  )
                : null}

              {!presentMode && draftArea && draftArea.length > 0 ? (
                <g className="draft-area">
                  <polyline
                    fill="rgba(103, 232, 249, 0.16)"
                    points={[...draftArea, ...(areaCursor ? [areaCursor] : [])]
                      .map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`)
                      .join(" ")}
                    stroke="#67e8f9"
                    strokeDasharray="10 8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={3}
                  />
                  {draftArea.map((point, index) => (
                    <circle
                      cx={point.x}
                      cy={point.y}
                      key={index}
                      r={index === 0 ? 7 : 4}
                      className={index === 0 ? "draft-area-start" : "draft-area-vertex"}
                    />
                  ))}
                </g>
              ) : null}

              {fogEnabled ? (
                <>
                  <defs>
                    <mask id="fog-reveal-mask">
                      <rect
                        fill="white"
                        height={worldSize.height}
                        width={worldSize.width}
                        x={0}
                        y={0}
                      />
                      {revealAreas.map((area) => (
                        <polygon
                          fill="black"
                          key={area.id}
                          points={area.points
                            .map(
                              (point) =>
                                `${point.x.toFixed(1)},${point.y.toFixed(1)}`
                            )
                            .join(" ")}
                        />
                      ))}
                    </mask>
                  </defs>
                  <rect
                    className="fog-layer"
                    fill="#04060f"
                    fillOpacity={presentMode ? 0.94 : 0.4}
                    height={worldSize.height}
                    mask="url(#fog-reveal-mask)"
                    width={worldSize.width}
                    x={0}
                    y={0}
                  />
                </>
              ) : null}
            </svg>
          </div>
        </div>
      </section>

      {openHandoutObject && hasHandout(openHandoutObject) ? (
        <div
          className="handout-overlay"
          onClick={() => setOpenHandoutId(null)}
          role="presentation"
        >
          <div
            className="handout-modal"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={`Handout: ${openHandoutObject.name}`}
          >
            <div className="handout-modal-head">
              <strong>{getObjectDisplayName(openHandoutObject)}</strong>
              <button
                aria-label="Close handout"
                className="tool-button icon-only"
                onClick={() => setOpenHandoutId(null)}
                type="button"
              >
                <X size={18} />
              </button>
            </div>
            {openHandoutObject.handout?.image ? (
              <img
                alt={openHandoutObject.handout.image.name}
                className="handout-modal-image"
                src={openHandoutObject.handout.image.src}
              />
            ) : null}
            {openHandoutObject.handout?.text ? (
              <p className="handout-modal-text">
                {openHandoutObject.handout.text}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  );
}
