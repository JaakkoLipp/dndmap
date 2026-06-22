import { beforeEach, describe, expect, it } from "vitest";
import type { CampaignMapSnapshot } from "./api";
import {
  loadStoredSnapshot,
  normalizeSnapshot,
  readCampaignFile,
  saveStoredSnapshot,
  serializeCampaign
} from "./storage";

const sampleSnapshot: CampaignMapSnapshot = {
  title: "Test Realm",
  image: null,
  objects: [
    {
      id: "marker-1",
      type: "marker",
      name: "Town",
      category: "settlement",
      color: "#f6c177",
      dmVisible: true,
      playerVisible: true,
      notes: "",
      x: 100,
      y: 120,
      radius: 14,
      handout: { text: "Welcome", image: null }
    }
  ],
  fogEnabled: false,
  viewport: { x: 0, y: 0, scale: 1 }
};

describe("normalizeSnapshot", () => {
  it("rejects values that are not snapshot-shaped", () => {
    expect(normalizeSnapshot(null)).toBeNull();
    expect(normalizeSnapshot({ title: "x" })).toBeNull();
  });

  it("coerces missing fields and drops invalid objects", () => {
    const snapshot = normalizeSnapshot({
      objects: [
        { type: "marker", x: 1, y: 2 },
        { type: "area", points: [{ x: 0, y: 0 }] }, // too few points -> dropped
        { type: "mystery" } // unknown type -> dropped
      ]
    });

    expect(snapshot).not.toBeNull();
    expect(snapshot?.title).toBe("D&D Campaign");
    expect(snapshot?.objects).toHaveLength(1);
    expect(snapshot?.objects[0].type).toBe("marker");
    expect(snapshot?.objects[0].dmVisible).toBe(true);
  });

  it("keeps a valid area and clamps fill opacity", () => {
    const snapshot = normalizeSnapshot({
      objects: [
        {
          type: "area",
          points: [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 }
          ],
          fillOpacity: 5,
          isReveal: true
        }
      ]
    });

    const area = snapshot?.objects[0];
    expect(area?.type).toBe("area");
    if (area?.type === "area") {
      expect(area.fillOpacity).toBe(1);
      expect(area.isReveal).toBe(true);
    }
  });

  it("normalizes the fog flag", () => {
    expect(normalizeSnapshot({ objects: [] })?.fogEnabled).toBe(false);
    expect(
      normalizeSnapshot({ objects: [], fogEnabled: true })?.fogEnabled
    ).toBe(true);
  });
});

describe("campaign file round-trip", () => {
  it("serializes and parses back to an equivalent snapshot", async () => {
    const json = serializeCampaign(sampleSnapshot);
    const file = { text: async () => json } as unknown as File;

    const parsed = await readCampaignFile(file);
    expect(parsed).toEqual(sampleSnapshot);
  });

  it("also accepts a bare snapshot without the file wrapper", async () => {
    const file = {
      text: async () => JSON.stringify(sampleSnapshot)
    } as unknown as File;

    const parsed = await readCampaignFile(file);
    expect(parsed.title).toBe("Test Realm");
  });

  it("throws on an invalid campaign file", async () => {
    const file = { text: async () => "{}" } as unknown as File;
    await expect(readCampaignFile(file)).rejects.toThrow();
  });
});

describe("local storage persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("saves and restores a snapshot", () => {
    expect(loadStoredSnapshot()).toBeNull();

    const result = saveStoredSnapshot(sampleSnapshot);
    expect(result.ok).toBe(true);

    const restored = loadStoredSnapshot();
    expect(restored?.title).toBe("Test Realm");
    expect(restored?.objects[0].playerVisible).toBe(true);
  });
});
