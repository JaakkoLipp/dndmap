"use client";

import {
  Download,
  Eye,
  EyeOff,
  ImagePlus,
  Layers3,
  MapPin,
  Maximize2,
  MousePointer2,
  Move,
  PenLine,
  Plus,
  Save,
  Trash2,
  Type,
  Waypoints,
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
import {
  CampaignMapSnapshot,
  MapImageState,
  MapObject,
  PathObject,
  Point,
  saveCampaignDraft
} from "../lib/campaignApi";

type Tool = "select" | "pan" | "marker" | "label" | "line" | "freehand";

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
  visible: boolean;
  radius: number;
  text: string;
  fontSize: number;
  strokeWidth: number;
}>;

const DEFAULT_WORLD = {
  width: 1600,
  height: 1000
};

const OBJECT_COLORS = ["#d79b39", "#74a86b", "#c95f55", "#6aa9b8", "#d7d0bb"];

const TOOLS: Array<{ id: Tool; label: string; icon: LucideIcon }> = [
  { id: "select", label: "Select", icon: MousePointer2 },
  { id: "pan", label: "Pan", icon: Move },
  { id: "marker", label: "Marker", icon: MapPin },
  { id: "label", label: "Label", icon: Type },
  { id: "line", label: "Line", icon: Waypoints },
  { id: "freehand", label: "Path", icon: PenLine }
];

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getObjectDisplayName(object: MapObject) {
  if (object.type === "label") {
    return object.text || object.name;
  }

  return object.name;
}

function moveObject(object: MapObject, dx: number, dy: number): MapObject {
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

function getObjectIcon(type: MapObject["type"]) {
  if (type === "marker") {
    return <MapPin size={16} />;
  }

  if (type === "label") {
    return <Type size={16} />;
  }

  if (type === "line") {
    return <Waypoints size={16} />;
  }

  return <PenLine size={16} />;
}

function makeSnapshot(
  title: string,
  image: MapImageState | null,
  objects: MapObject[],
  view: ViewState
): CampaignMapSnapshot {
  return {
    title,
    image,
    objects,
    viewport: view
  };
}

async function loadImageElement(src: string) {
  const image = new Image();
  image.src = src;

  if ("decode" in image) {
    await image.decode();
  } else {
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve();
      image.onerror = () => reject(new Error("Image could not be decoded."));
    });
  }

  return image;
}

function drawGridBackground(
  context: CanvasRenderingContext2D,
  width: number,
  height: number
) {
  context.fillStyle = "#1b211b";
  context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(215, 208, 187, 0.13)";
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

function drawExportObject(context: CanvasRenderingContext2D, object: MapObject) {
  if (!object.visible) {
    return;
  }

  context.save();
  context.lineCap = "round";
  context.lineJoin = "round";

  if (object.type === "marker") {
    context.fillStyle = object.color;
    context.strokeStyle = "#fff5dc";
    context.lineWidth = 4;
    context.beginPath();
    context.arc(object.x, object.y, object.radius, 0, Math.PI * 2);
    context.fill();
    context.stroke();

    context.font = "700 18px Arial, sans-serif";
    context.lineWidth = 5;
    context.strokeStyle = "rgba(19, 18, 14, 0.82)";
    context.fillStyle = "#fff5dc";
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

  if (object.type === "line" || object.type === "freehand") {
    const [firstPoint, ...rest] = object.points;

    if (firstPoint) {
      context.strokeStyle = object.color;
      context.lineWidth = object.strokeWidth;
      context.beginPath();
      context.moveTo(firstPoint.x, firstPoint.y);
      rest.forEach((point) => context.lineTo(point.x, point.y));
      context.stroke();
    }
  }

  context.restore();
}

export function MapEditor() {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const [title, setTitle] = useState("Blackfen Campaign");
  const [image, setImage] = useState<MapImageState | null>(null);
  const [objects, setObjects] = useState<MapObject[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tool, setTool] = useState<Tool>("select");
  const [view, setView] = useState<ViewState>({ x: 0, y: 0, scale: 1 });
  const [draftPath, setDraftPath] = useState<DraftPath | null>(null);
  const [status, setStatus] = useState("Ready");

  const worldSize = useMemo(
    () => ({
      width: image?.width ?? DEFAULT_WORLD.width,
      height: image?.height ?? DEFAULT_WORLD.height
    }),
    [image]
  );

  const selectedObject = objects.find((object) => object.id === selectedId);
  const visibleObjects = objects.filter((object) => object.visible);

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

  const handleImageFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      setStatus("Choose an image file");
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
  }, []);

  const addMarker = useCallback(
    (point: Point) => {
      const markerNumber =
        objects.filter((object) => object.type === "marker").length + 1;
      const marker: MapObject = {
        id: createId("marker"),
        type: "marker",
        name: `Marker ${markerNumber}`,
        x: point.x,
        y: point.y,
        radius: 14,
        color: OBJECT_COLORS[(objects.length + 1) % OBJECT_COLORS.length],
        visible: true
      };

      setObjects((currentObjects) => [...currentObjects, marker]);
      setSelectedId(marker.id);
      setStatus(`Added ${marker.name}`);
    },
    [objects]
  );

  const addLabel = useCallback(
    (point: Point) => {
      const labelNumber =
        objects.filter((object) => object.type === "label").length + 1;
      const label: MapObject = {
        id: createId("label"),
        type: "label",
        name: `Label ${labelNumber}`,
        text: `Label ${labelNumber}`,
        x: point.x,
        y: point.y,
        fontSize: 28,
        color: OBJECT_COLORS[(objects.length + 2) % OBJECT_COLORS.length],
        visible: true
      };

      setObjects((currentObjects) => [...currentObjects, label]);
      setSelectedId(label.id);
      setStatus(`Added ${label.name}`);
    },
    [objects]
  );

  const addPathObject = useCallback(
    (path: DraftPath) => {
      const usefulPoints =
        path.type === "line"
          ? path.points.slice(0, 2)
          : path.points.filter((point, index, points) => {
              if (index === 0) {
                return true;
              }

              const previous = points[index - 1];
              return Math.hypot(point.x - previous.x, point.y - previous.y) > 3;
            });

      if (usefulPoints.length < 2) {
        return;
      }

      const pathNumber =
        objects.filter((object) => object.type === path.type).length + 1;
      const nextPath: PathObject = {
        id: createId(path.type),
        type: path.type,
        name: path.type === "line" ? `Line ${pathNumber}` : `Path ${pathNumber}`,
        points: usefulPoints,
        strokeWidth: path.type === "line" ? 5 : 4,
        color: OBJECT_COLORS[(objects.length + 3) % OBJECT_COLORS.length],
        visible: true
      };

      setObjects((currentObjects) => [...currentObjects, nextPath]);
      setSelectedId(nextPath.id);
      setStatus(`Added ${nextPath.name}`);
    },
    [objects]
  );

  const updateSelectedObject = useCallback((updates: EditableObjectUpdates) => {
    setObjects((currentObjects) =>
      currentObjects.map((object) =>
        object.id === selectedId ? ({ ...object, ...updates } as MapObject) : object
      )
    );
  }, [selectedId]);

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) {
      return;
    }

    const point = screenToWorld(event);

    if (tool === "pan") {
      dragRef.current = {
        kind: "pan",
        clientX: event.clientX,
        clientY: event.clientY
      };
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (tool === "marker") {
      addMarker(point);
      return;
    }

    if (tool === "label") {
      addLabel(point);
      return;
    }

    if (tool === "line") {
      setDraftPath({ type: "line", points: [point, point] });
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (tool === "freehand") {
      setDraftPath({ type: "freehand", points: [point] });
      event.currentTarget.setPointerCapture(event.pointerId);
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

    if (tool === "pan") {
      dragRef.current = {
        kind: "pan",
        clientX: event.clientX,
        clientY: event.clientY
      };
      svgRef.current?.setPointerCapture(event.pointerId);
      return;
    }

    setSelectedId(object.id);

    if (tool !== "select") {
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
    if (draftPath) {
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

  const exportPng = async () => {
    const bounds = viewportRef.current?.getBoundingClientRect();

    if (!bounds) {
      return;
    }

    setStatus("Rendering PNG");

    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.floor(bounds.width * pixelRatio));
    canvas.height = Math.max(1, Math.floor(bounds.height * pixelRatio));
    const context = canvas.getContext("2d");

    if (!context) {
      setStatus("PNG export is not available");
      return;
    }

    context.scale(pixelRatio, pixelRatio);
    context.fillStyle = "#11150f";
    context.fillRect(0, 0, bounds.width, bounds.height);
    context.save();
    context.translate(view.x, view.y);
    context.scale(view.scale, view.scale);

    if (image) {
      const exportImage = await loadImageElement(image.src);
      context.drawImage(exportImage, 0, 0, worldSize.width, worldSize.height);
    } else {
      drawGridBackground(context, worldSize.width, worldSize.height);
    }

    objects.forEach((object) => drawExportObject(context, object));
    context.restore();

    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "map"}-view.png`;
    link.click();
    setStatus("PNG exported");
  };

  const saveDraft = async () => {
    setStatus("Saving draft");

    try {
      const snapshot = makeSnapshot(title, image, objects, view);
      const result = await saveCampaignDraft(snapshot);
      setStatus(result.savedAt ? `Saved ${new Date(result.savedAt).toLocaleTimeString()}` : "Saved");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
    }
  };

  const deleteSelectedObject = () => {
    if (!selectedId) {
      return;
    }

    setObjects((currentObjects) =>
      currentObjects.filter((object) => object.id !== selectedId)
    );
    setSelectedId(null);
    setStatus("Object removed");
  };

  const toggleVisibility = (id: string) => {
    setObjects((currentObjects) =>
      currentObjects.map((object) =>
        object.id === id ? { ...object, visible: !object.visible } : object
      )
    );
  };

  const renderPath = (
    object: PathObject | DraftPath,
    color: string,
    strokeWidth: number,
    className?: string
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
        strokeWidth={strokeWidth}
      />
    );
  };

  return (
    <main className="editor-shell">
      <header className="topbar">
        <div className="brand-area">
          <Layers3 size={22} />
          <input
            aria-label="Campaign title"
            className="title-input"
            onChange={(event) => setTitle(event.target.value)}
            value={title}
          />
        </div>

        <div className="toolbar" aria-label="Map tools">
          <button
            className="tool-button"
            onClick={() => fileInputRef.current?.click()}
            title="Load image"
            type="button"
          >
            <ImagePlus size={18} />
            <span>Load</span>
          </button>
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
          <button
            className="tool-button"
            onClick={saveDraft}
            title="Save draft"
            type="button"
          >
            <Save size={18} />
            <span>Save</span>
          </button>
          <button
            className="primary-button"
            onClick={exportPng}
            title="Export PNG"
            type="button"
          >
            <Download size={18} />
            <span>PNG</span>
          </button>
        </div>
      </header>

      <section className="workspace">
        <aside className="sidebar" aria-label="Layers and properties">
          <div className="sidebar-section">
            <div className="section-heading">
              <Layers3 size={17} />
              <h2>Objects</h2>
              <span>{visibleObjects.length}/{objects.length}</span>
            </div>

            <div className="object-list">
              {objects.length === 0 ? (
                <div className="empty-list">No objects</div>
              ) : (
                [...objects].reverse().map((object) => (
                  <div
                    className={`object-row ${selectedId === object.id ? "selected" : ""}`}
                    key={object.id}
                  >
                    <button
                      className="object-main"
                      onClick={() => setSelectedId(object.id)}
                      type="button"
                    >
                      <span
                        className="object-color"
                        style={{ background: object.color }}
                      />
                      {getObjectIcon(object.type)}
                      <span>{getObjectDisplayName(object)}</span>
                    </button>
                    <button
                      className="icon-action"
                      onClick={() => toggleVisibility(object.id)}
                      title={object.visible ? "Hide" : "Show"}
                      type="button"
                    >
                      {object.visible ? <Eye size={16} /> : <EyeOff size={16} />}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="sidebar-section properties-section">
            <div className="section-heading">
              <Plus size={17} />
              <h2>Properties</h2>
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

                {selectedObject.type === "line" ||
                selectedObject.type === "freehand" ? (
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
              <div className="empty-list">Nothing selected</div>
            )}
          </div>
        </aside>

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
            <span>{image?.name ?? "Untitled map"}</span>
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
                <span>Map image</span>
              </div>
            )}

            <svg
              className="map-overlay"
              height={worldSize.height}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              ref={svgRef}
              viewBox={`0 0 ${worldSize.width} ${worldSize.height}`}
              width={worldSize.width}
            >
              <rect fill="transparent" height={worldSize.height} width={worldSize.width} />

              {objects.map((object) => {
                if (!object.visible) {
                  return null;
                }

                const isSelected = selectedId === object.id;

                if (object.type === "marker") {
                  return (
                    <g
                      className={`map-object ${isSelected ? "selected" : ""}`}
                      key={object.id}
                      onPointerDown={(event) => handleObjectPointerDown(event, object)}
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
                        r={Math.max(4, object.radius * 0.32)}
                      />
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
                      className={`map-object ${isSelected ? "selected" : ""}`}
                      key={object.id}
                      onPointerDown={(event) => handleObjectPointerDown(event, object)}
                    >
                      {isSelected ? (
                        <rect
                          className="label-selection"
                          height={object.fontSize + 12}
                          width={Math.max(90, object.text.length * object.fontSize * 0.55)}
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
                    className={`map-object ${isSelected ? "selected" : ""}`}
                    key={object.id}
                    onPointerDown={(event) => handleObjectPointerDown(event, object)}
                  >
                    {isSelected
                      ? renderPath(object, "rgba(255, 245, 220, 0.9)", object.strokeWidth + 8, "selection-path")
                      : null}
                    {renderPath(object, object.color, object.strokeWidth)}
                  </g>
                );
              })}

              {draftPath
                ? renderPath(
                    draftPath,
                    "#fff5dc",
                    draftPath.type === "line" ? 4 : 3,
                    "draft-path"
                  )
                : null}
            </svg>
          </div>
        </div>
      </section>
    </main>
  );
}
