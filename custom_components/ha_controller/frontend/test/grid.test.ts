import {describe, expect, it} from "vitest";
import {canDelete, gridBounds, placeholders} from "../src/model/grid";
import type {Block, Cell, Layout} from "../src/types";
import {validLayouts} from "./fixtures";

const block = (id: string, x: number, y: number): Block => ({
  id, x, y, name: id, background: "#000000", font_size: "m", type: "custom", items: [],
});
const layoutOf = (blocks: Block[]): Layout => ({
  version: 1, start: blocks[0]?.id ?? null, settings: {sleep_timeout: 20}, blocks,
});
const cellsOf = (layout: Layout): Cell[] => layout.blocks.map(({x, y}) => ({x, y}));

describe("fixtures", () => {
  it("are loaded", () => {
    expect(Object.keys(validLayouts).length).toBeGreaterThan(0);
  });
});

describe("placeholders", () => {
  it("offers the origin for an empty layout", () => {
    expect(placeholders(validLayouts.empty)).toEqual([{x: 0, y: 0}]);
  });
  it("finds the 8 plus cells of the reference screenshot", () => {
    expect(placeholders(validLayouts.reference)).toEqual([
      {x: 0, y: -2}, {x: -1, y: -1}, {x: 1, y: -1}, {x: -2, y: 0},
      {x: 1, y: 0}, {x: -2, y: 1}, {x: 0, y: 1}, {x: -1, y: 2}]);
  });
  it("offers nothing at 32 blocks", () => {
    const row = Array.from({length: 32}, (_, i) => block(`b${i}`, i, 0));
    expect(placeholders(layoutOf(row))).toEqual([]);
  });
  it("stays within the coordinate limit", () => {
    expect(placeholders(layoutOf([block("b1", 32, 0)]))).not.toContainEqual({x: 33, y: 0});
  });
});

describe("canDelete", () => {
  it("refuses the start block", () => {
    expect(canDelete(validLayouts.reference, "b1")).toEqual({ok: false, reason: "start"});
  });
  it("refuses a block that disconnects another", () => {
    expect(canDelete(validLayouts.reference, "b3")).toEqual({ok: false, reason: "disconnects"});
  });
  it("allows a leaf block", () => {
    expect(canDelete(validLayouts.reference, "b2")).toEqual({ok: true});
  });
  it("allows deleting the only block", () => {
    expect(canDelete(validLayouts.single, "b1")).toEqual({ok: true});
  });
});

describe("gridBounds", () => {
  it("bounds a single cell", () => {
    expect(gridBounds(cellsOf(validLayouts.single))).toEqual({minX: 3, maxX: 3, minY: -2, maxY: -2});
  });
});
