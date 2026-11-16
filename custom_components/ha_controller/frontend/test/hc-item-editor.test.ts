import {html} from "lit";
import {afterEach, describe, expect, it} from "vitest";
import "../src/components/hc-item-editor";
import "../src/components/hc-emoji-picker";
import "../src/components/hc-preview";
import {all, cleanup, mount, nextEvent, one} from "./dom";
import {fakeHass} from "./hass";
import {validLayouts} from "./fixtures";
import type {Item} from "../src/types";

afterEach(cleanup);

const hass = fakeHass();
const items = validLayouts.reference.blocks[2].items as Item[];
const item = (i: number) =>
  mount(html`<hc-item-editor .hass=${hass} .item=${items[i]} .index=${i} .count=${items.length}></hc-item-editor>`);

describe("hc-item-editor", () => {
  it("emits a text patch", async () => {
    const el = await item(0);
    const input = one<HTMLInputElement>(el, "input[name=text]")!;
    const changed = nextEvent<{patch: Partial<Item>}>(el, "hc-item-change");
    input.value = "Hi";
    input.dispatchEvent(new Event("input", {bubbles: true}));
    expect((await changed).detail.patch).toEqual({text: "Hi"});
  });

  it("emits font size patches, null for inherit", async () => {
    const el = await item(1);
    const select = one<HTMLSelectElement>(el, "select[name=font-size]")!;
    expect(select.value).toBe("xl");
    const changed = nextEvent<{patch: Partial<Item>}>(el, "hc-item-change");
    select.value = "";
    select.dispatchEvent(new Event("change", {bubbles: true}));
    expect((await changed).detail.patch).toEqual({font_size: null});
  });

  it("emits move and remove, disabling impossible moves", async () => {
    const el = await item(0);
    expect(one(el, "button.up")!.hasAttribute("disabled")).toBe(true);
    expect(one(el, "button.down")!.hasAttribute("disabled")).toBe(false);
    const moved = nextEvent<{delta: number}>(el, "hc-item-move");
    one(el, "button.down")!.click();
    expect((await moved).detail.delta).toBe(1);
    const removed = nextEvent(el, "hc-item-remove");
    one(el, "button.remove")!.click();
    await removed;
  });

  it("edits an entity item with attribute", async () => {
    const el = await item(2);
    expect(one(el, "hc-entity-input")).not.toBeNull();
    const input = one<HTMLInputElement>(el, "input[name=attribute]")!;
    const changed = nextEvent<{patch: Partial<Item>}>(el, "hc-item-change");
    input.value = "unit";
    input.dispatchEvent(new Event("input", {bubbles: true}));
    expect((await changed).detail.patch).toEqual({attribute: "unit"});
  });

  it("maps the emoji picker to an emoji patch", async () => {
    const el = await item(1);
    const changed = nextEvent<{patch: Partial<Item>}>(el, "hc-item-change");
    one(el, "hc-emoji-picker")!.dispatchEvent(new CustomEvent("hc-value-change", {detail: {value: "💡"}, bubbles: true, composed: true}));
    expect((await changed).detail.patch).toEqual({emoji: "💡"});
  });

  it("has no extra fields for battery items", async () => {
    const el = await item(3);
    expect(one(el, "input")).toBeNull();
  });
});

describe("hc-emoji-picker", () => {
  it("renders 64 buttons and emits the normalised value", async () => {
    const picker = await mount(html`<hc-emoji-picker .value=${"👋"}></hc-emoji-picker>`);
    const buttons = all(picker, "button.emoji");
    expect(buttons).toHaveLength(64);
    const changed = nextEvent<{value: string}>(picker, "hc-value-change");
    buttons[3].click();
    expect((await changed).detail.value).toBe(buttons[3].textContent!.trim().replaceAll("️", ""));
  });
});

describe("hc-preview", () => {
  it("shows the entity state for entity blocks", async () => {
    const el = await mount(html`<hc-preview .hass=${hass} .block=${validLayouts.reference.blocks[0]}></hc-preview>`);
    expect(el.shadowRoot!.textContent).toContain("Kitchen");
    expect(el.shadowRoot!.textContent).toContain("on");
  });

  it("shows one line per item for custom blocks", async () => {
    const el = await mount(html`<hc-preview .hass=${hass} .block=${validLayouts.reference.blocks[2]}></hc-preview>`);
    expect(all(el, ".line")).toHaveLength(5);
    expect(el.shadowRoot!.textContent).toContain("21.5");
  });
});
