import {describe, expect, it} from "vitest";
import {
  PALETTE, addBlock, addItem, deleteBlock, moveItem, nextId, removeItem, setSleepTimeout, setStart,
  updateBlock, updateItem,
} from "../src/model/edit";
import type {Layout} from "../src/types";
import {validLayouts} from "./fixtures";

const ref = validLayouts.reference;
const itemIds = (l: Layout, blockId: string): string[] =>
  (l.blocks.find((b) => b.id === blockId)?.items ?? []).map((i) => i.id);

describe("edit operations", () => {
  it("has an 8 colour palette", () => expect(PALETTE).toHaveLength(8));

  it("nextId continues the highest suffix", () => {
    expect(nextId(ref, "i")).toBe("i6");
    expect(nextId(ref, "b")).toBe("b5");
    expect(nextId(validLayouts.empty, "b")).toBe("b1");
  });

  it("addBlock", () => {
    const r = addBlock(ref, {x: 1, y: 0});
    expect(r.id).toBe("b5");
    expect(r.layout.blocks.at(-1)).toMatchObject({
      x: 1, y: 0, name: "Block 5", background: "#E08A2E", font_size: "m", type: "custom", items: [],
    });
    expect(r.layout.start).toBe("b1");
    expect(addBlock(validLayouts.empty, {x: 0, y: 0}).layout).toMatchObject({
      start: "b1", blocks: [{id: "b1", background: "#C94F3D"}],
    });
  });

  it("deleteBlock", () => {
    expect(deleteBlock(validLayouts.single, "b1")).toEqual({
      version: 1, start: null, settings: {sleep_timeout: 0}, blocks: [],
    });
    expect(deleteBlock(ref, "b4").blocks.map((b) => b.id)).toEqual(["b1", "b2", "b3"]);
    expect(() => deleteBlock(ref, "b3")).toThrow();
    expect(() => deleteBlock(ref, "b1")).toThrow();
  });

  it("setStart, updateBlock, setSleepTimeout", () => {
    expect(setStart(ref, "b2").start).toBe("b2");
    expect(updateBlock(ref, "b2", {name: "X"}).blocks[1].name).toBe("X");
    expect(setSleepTimeout(ref, 45).settings).toEqual({sleep_timeout: 45});
  });

  it("addItem defaults", () => {
    const text = addItem(ref, "b3", "text");
    expect(text.id).toBe("i6");
    expect(text.layout.blocks[2].items?.at(-1)).toEqual({id: "i6", kind: "text", text: "Text", font_size: null});
    expect(addItem(ref, "b3", "emoji").layout.blocks[2].items?.at(-1))
      .toEqual({id: "i6", kind: "emoji", emoji: "💡", font_size: null});
    expect(addItem(ref, "b3", "entity").layout.blocks[2].items?.at(-1))
      .toEqual({id: "i6", kind: "entity", entity_id: "", attribute: null, font_size: null});
    expect(addItem(ref, "b3", "battery").layout.blocks[2].items?.at(-1))
      .toEqual({id: "i6", kind: "battery", font_size: null});
  });

  it("updateItem and removeItem", () => {
    expect(updateItem(ref, "b3", "i1", {text: "Hi"}).blocks[2].items?.[0]).toMatchObject({id: "i1", text: "Hi"});
    expect(itemIds(removeItem(ref, "b3", "i2"), "b3")).toEqual(["i1", "i3", "i4", "i5"]);
  });

  it("moveItem", () => {
    expect(itemIds(moveItem(ref, "b3", "i1", 1), "b3")).toEqual(["i2", "i1", "i3", "i4", "i5"]);
    expect(itemIds(moveItem(ref, "b3", "i1", -1), "b3")).toEqual(["i1", "i2", "i3", "i4", "i5"]);
    expect(itemIds(moveItem(ref, "b3", "i5", 1), "b3")).toEqual(["i1", "i2", "i3", "i4", "i5"]);
    expect(itemIds(moveItem(ref, "b3", "i3", -1), "b3")).toEqual(["i1", "i3", "i2", "i4", "i5"]);
  });

  it("never mutates its input", () => {
    const copy = structuredClone(ref);
    addBlock(copy, {x: 1, y: 0});
    deleteBlock(copy, "b4");
    setStart(copy, "b2");
    updateBlock(copy, "b2", {name: "X"});
    setSleepTimeout(copy, 45);
    addItem(copy, "b3", "text");
    updateItem(copy, "b3", "i1", {text: "Hi"});
    removeItem(copy, "b3", "i2");
    moveItem(copy, "b3", "i1", 1);
    expect(copy).toEqual(ref);
  });
});
