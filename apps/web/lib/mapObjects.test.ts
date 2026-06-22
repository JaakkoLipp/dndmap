import { describe, expect, it } from "vitest";
import type { MapObject } from "./api";
import {
  createArea,
  createLabel,
  createMarker,
  createPathFromDraft,
  exportBaseName,
  hasHandout,
  moveObject
} from "./mapObjects";

describe("createMarker", () => {
  it("creates a DM-only marker numbered per category", () => {
    const first = createMarker([], { x: 10, y: 20 }, "settlement");

    expect(first.type).toBe("marker");
    expect(first.name).toBe("Settlement 1");
    expect(first.dmVisible).toBe(true);
    expect(first.playerVisible).toBe(false);
    expect(first.color).toBe("#f6c177");

    const second = createMarker([first], { x: 0, y: 0 }, "settlement");
    expect(second.name).toBe("Settlement 2");

    // Numbering is independent per category.
    const dungeon = createMarker([first, second], { x: 0, y: 0 }, "dungeon");
    expect(dungeon.name).toBe("Dungeon 1");
  });
});

describe("createLabel", () => {
  it("falls back to a rumor note when the category is a route", () => {
    const label = createLabel([], { x: 1, y: 2 }, "route");

    expect(label.type).toBe("label");
    expect(label.category).toBe("rumor");
    expect(label.text).toBe(label.name);
  });
});

describe("createPathFromDraft", () => {
  it("keeps only the endpoints of a line", () => {
    const path = createPathFromDraft([], {
      type: "line",
      points: [
        { x: 0, y: 0 },
        { x: 5, y: 5 },
        { x: 9, y: 9 }
      ]
    });

    expect(path?.type).toBe("polyline");
    expect(path?.points).toHaveLength(2);
  });

  it("drops near-duplicate freehand points and rejects tiny strokes", () => {
    const path = createPathFromDraft([], {
      type: "freehand",
      points: [
        { x: 0, y: 0 },
        { x: 0.5, y: 0.5 },
        { x: 40, y: 40 }
      ]
    });

    expect(path?.type).toBe("freehand");
    expect(path?.points).toHaveLength(2);

    expect(
      createPathFromDraft([], { type: "line", points: [{ x: 0, y: 0 }] })
    ).toBeNull();
  });
});

describe("createArea", () => {
  it("requires at least three points", () => {
    expect(
      createArea([], [{ x: 0, y: 0 }, { x: 1, y: 1 }], "faction")
    ).toBeNull();

    const area = createArea(
      [],
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 10, y: 10 }
      ],
      "faction"
    );

    expect(area?.type).toBe("area");
    expect(area?.fillOpacity).toBeGreaterThan(0);
    expect(area?.name).toBe("Region 1");
    expect(area?.isReveal).toBe(false);
  });

  it("creates reveal areas that are player-visible and numbered separately", () => {
    const region = createArea(
      [],
      [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 1, y: 1 }
      ],
      "faction"
    );
    const reveal = createArea(
      region ? [region] : [],
      [
        { x: 0, y: 0 },
        { x: 2, y: 0 },
        { x: 2, y: 2 }
      ],
      "faction",
      true
    );

    expect(reveal?.isReveal).toBe(true);
    expect(reveal?.playerVisible).toBe(true);
    expect(reveal?.name).toBe("Reveal 1");
  });
});

describe("moveObject", () => {
  it("translates point coordinates for markers", () => {
    const marker = createMarker([], { x: 5, y: 5 }, "danger");
    const moved = moveObject(marker, 10, -3);

    expect(moved).toMatchObject({ x: 15, y: 2 });
  });

  it("translates every vertex for paths and areas", () => {
    const area = createArea(
      [],
      [
        { x: 0, y: 0 },
        { x: 4, y: 0 },
        { x: 4, y: 4 }
      ],
      "route"
    );
    const moved = moveObject(area as MapObject, 2, 2);

    expect(moved.type).toBe("area");
    if (moved.type === "area") {
      expect(moved.points).toEqual([
        { x: 2, y: 2 },
        { x: 6, y: 2 },
        { x: 6, y: 6 }
      ]);
    }
  });
});

describe("hasHandout", () => {
  it("is true only when text or image content exists", () => {
    const marker = createMarker([], { x: 0, y: 0 }, "quest");

    expect(hasHandout(marker)).toBe(false);
    expect(hasHandout({ ...marker, handout: { text: "", image: null } })).toBe(
      false
    );
    expect(
      hasHandout({ ...marker, handout: { text: "A letter", image: null } })
    ).toBe(true);
  });
});

describe("exportBaseName", () => {
  it("slugifies a title and falls back to map", () => {
    expect(exportBaseName("The Sword Coast!")).toBe("the-sword-coast");
    expect(exportBaseName("   ")).toBe("map");
  });
});
