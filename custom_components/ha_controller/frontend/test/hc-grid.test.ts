import {html} from "lit";
import {afterEach, describe, expect, it} from "vitest";
import "../src/components/hc-grid";
import {all, cleanup, mount, nextEvent, one} from "./dom";
import {defineElement} from "../src/define";
import {validLayouts} from "./fixtures";

afterEach(cleanup);

const reference = () =>
  mount(html`<hc-grid .layout=${validLayouts.reference} .selectedId=${null} .errorRefs=${new Set(["b4"])}></hc-grid>`);

describe("hc-grid", () => {
  it("renders blocks, placeholders, start badge and error state", async () => {
    const el = await reference();
    expect(all(el, ".block")).toHaveLength(4);
    expect(all(el, ".placeholder")).toHaveLength(8);
    expect(one(el, '.block[data-id="b1"] .start-badge')?.textContent).toBe("start");
    expect(all(el, ".start-badge")).toHaveLength(1);
    expect(one(el, '.block[data-id="b1"]')!.classList.contains("start")).toBe(true);
    expect(one(el, '.block[data-id="b1"] .start-badge')).not.toBeNull();
    expect(all(el, ".block.start")).toHaveLength(1);
    expect(one(el, '.block[data-id="b4"]')!.classList.contains("has-error")).toBe(true);
    expect(one(el, '.block[data-id="b1"]')!.classList.contains("has-error")).toBe(false);
  });

  it("places cells on the grid with x right and y down", async () => {
    const el = await reference();
    expect(one(el, '.block[data-id="b3"]')!.style.gridColumn).toBe("2");
    expect(one(el, '.block[data-id="b3"]')!.style.gridRow).toBe("3");
  });

  it("marks the selected block and colours its text", async () => {
    const layout = validLayouts.reference;
    const el = await mount(html`<hc-grid .layout=${layout} .selectedId=${"b2"} .errorRefs=${new Set<string>()}></hc-grid>`);
    expect(one(el, '.block[data-id="b2"]')!.classList.contains("selected")).toBe(true);
    expect(all(el, ".block.selected")).toHaveLength(1);
    const block = layout.blocks[0];
    const node = one(el, `.block[data-id="${block.id}"]`)!;
    expect(node.style.background).not.toBe("");
    expect(["#000000", "#ffffff", "rgb(0, 0, 0)", "rgb(255, 255, 255)"]).toContain(node.style.color.toLowerCase());
  });

  it("emits hc-add-block from a placeholder", async () => {
    const el = await reference();
    const added = nextEvent<{x: number; y: number}>(el, "hc-add-block");
    one(el, '.placeholder[data-x="1"][data-y="0"]')!.click();
    const event = await added;
    expect(event.detail).toEqual({x: 1, y: 0});
    expect(event.bubbles && event.composed).toBe(true);
  });

  it("emits hc-select-block from a block", async () => {
    const el = await reference();
    const selected = nextEvent<{id: string}>(el, "hc-select-block");
    one(el, '.block[data-id="b3"]')!.click();
    const event = await selected;
    expect(event.detail).toEqual({id: "b3"});
    expect(event.bubbles && event.composed).toBe(true);
  });

  it("can show selected and has-error on the same block", async () => {
    const el = await mount(html`<hc-grid .layout=${validLayouts.reference} .selectedId=${"b4"} .errorRefs=${new Set(["b4"])}></hc-grid>`);
    const node = one(el, '.block[data-id="b4"]')!;
    expect(node.classList.contains("selected") && node.classList.contains("has-error")).toBe(true);
  });

  it("renders a single origin placeholder for an empty layout", async () => {
    const empty = {version: 1 as const, start: null, settings: {sleep_timeout: 0}, blocks: []};
    const el = await mount(html`<hc-grid .layout=${empty}></hc-grid>`);
    const ph = all(el, ".placeholder");
    expect(ph).toHaveLength(1);
    expect(ph[0].dataset.x).toBe("0");
    expect(ph[0].dataset.y).toBe("0");
  });
});

describe("defineElement", () => {
  it("does not throw when the same name is defined twice", () => {
    class Dummy extends HTMLElement {}
    expect(() => {
      defineElement("hc-define-test", Dummy);
      defineElement("hc-define-test", Dummy);
    }).not.toThrow();
  });
});
