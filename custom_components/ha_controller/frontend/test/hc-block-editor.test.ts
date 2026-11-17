import {html} from "lit";
import {afterEach, describe, expect, it} from "vitest";
import "../src/components/hc-block-editor";
import {all, cleanup, mount, nextEvent, one} from "./dom";
import {validLayouts} from "./fixtures";
import {fakeHass} from "./hass";
import type {Layout} from "../src/types";

afterEach(cleanup);

const hass = fakeHass();
const editor = (blockId: string, layout: Layout = validLayouts.reference) =>
  mount(html`<hc-block-editor .hass=${hass} .layout=${layout} .blockId=${blockId}></hc-block-editor>`);

function type(input: HTMLInputElement, value: string): void {
  input.value = value;
  input.dispatchEvent(new Event("input", {bubbles: true}));
  input.dispatchEvent(new Event("change", {bubbles: true}));
}

describe("hc-block-editor", () => {
  it("emits the new layout when the name changes, without mutating the property", async () => {
    const el = await editor("b1");
    const changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    type(one<HTMLInputElement>(el, "input[name=name]")!, "Kitchen 2");
    expect((await changed).detail.layout.blocks[0].name).toBe("Kitchen 2");
    expect(validLayouts.reference.blocks[0].name).toBe("Kitchen");
  });

  it("offers matching entities in the entity input", async () => {
    const el = await editor("b1");
    const input = one(el, "hc-entity-input")!;
    await (input as unknown as {updateComplete: Promise<unknown>}).updateComplete;
    const values = all<HTMLOptionElement>(input, "datalist option").map((o) => o.value);
    expect(values).toEqual(["climate.bedroom", "light.kitchen", "light.living_room"]);
  });

  it("changes the entity", async () => {
    const el = await editor("b1");
    const input = one(el, "hc-entity-input")!;
    const changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    type(one<HTMLInputElement>(input, "input")!, "light.living_room");
    expect((await changed).detail.layout.blocks[0].entity_id).toBe("light.living_room");
  });

  it("changes the background from a swatch and the font size", async () => {
    const el = await editor("b1");
    expect(all(el, "button.swatch")).toHaveLength(8);
    let changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    all(el, "button.swatch")[1].click();
    expect((await changed).detail.layout.blocks[0].background).toBe("#4F86DD");
    changed = nextEvent(el, "hc-layout-change");
    all(el, "button.font-size").find((b) => b.textContent!.trim() === "XL")!.click();
    expect((await changed).detail.layout.blocks[0].font_size).toBe("xl");
  });

  it("switches to Custom keeping the entity and adding items", async () => {
    const el = await editor("b1");
    const changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    const select = one<HTMLSelectElement>(el, "select[name=type]")!;
    select.value = "custom";
    select.dispatchEvent(new Event("change", {bubbles: true}));
    const block = (await changed).detail.layout.blocks[0];
    expect(block.type).toBe("custom");
    expect(block.entity_id).toBe("light.kitchen");
    expect(block.items).toEqual([]);
  });

  it("switches back to Entity keeping the items", async () => {
    const el = await editor("b3");
    const changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    const select = one<HTMLSelectElement>(el, "select[name=type]")!;
    select.value = "entity";
    select.dispatchEvent(new Event("change", {bubbles: true}));
    const block = (await changed).detail.layout.blocks[2];
    expect(block.type).toBe("entity");
    expect(block.items).toHaveLength(5);
  });

  it("lists items of a custom block and adds an item", async () => {
    const el = await editor("b3");
    expect(all(el, "hc-item-editor")).toHaveLength(5);
    const changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    const select = one<HTMLSelectElement>(el, "select[name=add-item]")!;
    select.value = "battery";
    select.dispatchEvent(new Event("change", {bubbles: true}));
    const items = (await changed).detail.layout.blocks[2].items!;
    expect(items).toHaveLength(6);
    expect(items[5].kind).toBe("battery");
  });

  it("applies item events to the layout", async () => {
    const el = await editor("b3");
    const editors = all(el, "hc-item-editor");
    let changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    editors[0].dispatchEvent(new CustomEvent("hc-item-change", {detail: {patch: {text: "Hi"}}, bubbles: true, composed: true}));
    expect((await changed).detail.layout.blocks[2].items![0].text).toBe("Hi");
    changed = nextEvent(el, "hc-layout-change");
    editors[0].dispatchEvent(new CustomEvent("hc-item-move", {detail: {delta: 1}, bubbles: true, composed: true}));
    expect((await changed).detail.layout.blocks[2].items![1].id).toBe("i1");
    changed = nextEvent(el, "hc-layout-change");
    editors[1].dispatchEvent(new CustomEvent("hc-item-remove", {bubbles: true, composed: true}));
    expect((await changed).detail.layout.blocks[2].items).toHaveLength(4);
  });

  it("disables start and delete for the start block and explains why", async () => {
    const el = await editor("b1");
    expect(one(el, "button.start")!.hasAttribute("disabled")).toBe(true);
    expect(one(el, "button.delete")!.hasAttribute("disabled")).toBe(true);
    expect(el.shadowRoot!.textContent).toContain("Choose another start block first.");
  });

  it("explains a delete that would disconnect blocks", async () => {
    const layout: Layout = {
      ...validLayouts.reference,
      blocks: [
        {id: "b1", x: 0, y: 0, name: "A", background: "#C94F3D", font_size: "m", type: "custom", items: []},
        {id: "b2", x: 1, y: 0, name: "B", background: "#4F86DD", font_size: "m", type: "custom", items: []},
        {id: "b3", x: 2, y: 0, name: "C", background: "#5B9E4D", font_size: "m", type: "custom", items: []},
      ],
    };
    const el = await editor("b2", layout);
    expect(one(el, "button.delete")!.hasAttribute("disabled")).toBe(true);
    expect(el.shadowRoot!.textContent).toContain("Other blocks would become unreachable.");
  });

  it("sets the start block and deletes a leaf block", async () => {
    let el = await editor("b2");
    expect(one(el, "button.start")!.hasAttribute("disabled")).toBe(false);
    let changed = nextEvent<{layout: Layout}>(el, "hc-layout-change");
    one(el, "button.start")!.click();
    expect((await changed).detail.layout.start).toBe("b2");
    el = await editor("b2");
    changed = nextEvent(el, "hc-layout-change");
    one(el, "button.delete")!.click();
    expect((await changed).detail.layout.blocks.map((b) => b.id)).toEqual(["b1", "b3", "b4"]);
  });

  it("renders a preview", async () => {
    const el = await editor("b1");
    expect(one(el, "hc-preview")).not.toBeNull();
  });
});
