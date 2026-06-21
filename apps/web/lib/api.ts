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

export type HandoutContent = {
  text: string;
  image: MapImageState | null;
};

type BaseMapObject = {
  id: string;
  name: string;
  color: string;
  category: MapObjectCategory;
  dmVisible: boolean;
  playerVisible: boolean;
  notes: string;
  handout?: HandoutContent | null;
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

export type AreaObject = BaseMapObject & {
  type: "area";
  points: Point[];
  strokeWidth: number;
  fillOpacity: number;
};

export type MapObject = MarkerObject | LabelObject | PathObject | AreaObject;

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
