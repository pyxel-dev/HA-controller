import {html} from "lit";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import "../src/ha-controller-panel";
import type {HaControllerPanel} from "../src/ha-controller-panel";
import {createMockHass} from "../dev/mock-hass";
import type {Hass, Layout, ScreenInfo} from "../src/types";
import {all, cleanup, mount, one} from "./dom";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

function spied(screen: Partial<ScreenInfo> = {}) {
  const hass = createMockHass(screen);
  const real = hass.callWS.bind(hass);
  const callWS = vi.fn(real);
  hass.callWS = callWS as unknown as Hass["callWS"];
  return {hass, callWS, real};
}

function saveCall(callWS: {mock: {calls: unknown[][]}}): {entry_id: string; layout: Layout} {
  const msgs = callWS.mock.calls.map((c) => c[0] as {type: string; entry_id: string; layout: Layout});
  return msgs.find((m) => m.type === "ha_controller/layout/save")!;
}

async function settle(el: HaControllerPanel): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
    await el.updateComplete;
  }
}

async function open(hass: Hass): Promise<HaControllerPanel> {
  const el = await mount<HaControllerPanel>(html`<ha-controller-panel .hass=${hass}></ha-controller-panel>`);
  await settle(el);
  return el;
}

const blocks = (el: HaControllerPanel) => all(one(el, "hc-grid")!, ".block");
const saveButton = (el: HaControllerPanel) => one<HTMLButtonElement>(el, "button.save")!;
const click = async (el: HaControllerPanel, node: Element) => {
  (node as HTMLElement).click();
  await settle(el);
};
const addBlockRight = async (el: HaControllerPanel) => {
  await click(el, one(one(el, "hc-grid")!, '.placeholder[data-x="1"][data-y="0"]')!);
};

describe("ha-controller-panel", () => {
  it("loads the first screen and renders its map", async () => {
    const {hass} = spied();
    const el = await open(hass);
    expect(blocks(el)).toHaveLength(4);
  });

  it("save is disabled until something changes", async () => {
    const {hass} = spied();
    const el = await open(hass);
    expect(saveButton(el).disabled).toBe(true);
    await addBlockRight(el);
    expect(saveButton(el).disabled).toBe(false);
    await click(el, one(el, "button.revert")!);
    expect(blocks(el)).toHaveLength(4);
    expect(saveButton(el).disabled).toBe(true);
  });

  it("adding a block and saving sends the new layout", async () => {
    const {hass, callWS} = spied();
    const el = await open(hass);
    await addBlockRight(el);
    await click(el, saveButton(el));
    const call = saveCall(callWS);
    expect(call.entry_id).toBe("mock-entry");
    expect(call.layout.blocks).toHaveLength(5);
    expect(one(el, ".notice")!.textContent).toContain("Saved — sent to the screen.");
    expect(saveButton(el).disabled).toBe(true);
  });

  it("save error keeps changes", async () => {
    const {hass, callWS, real} = spied();
    const el = await open(hass);
    await addBlockRight(el);
    callWS.mockImplementation((msg: {type: string}) =>
      msg.type === "ha_controller/layout/save"
        ? Promise.reject({code: "invalid_layout", message: "invalid_name@b2"})
        : real(msg),
    );
    await click(el, saveButton(el));
    expect(one(el, ".notice")!.textContent).toContain("Names need 1 to 32 characters.");
    expect(blocks(el)).toHaveLength(5);
    expect(saveButton(el).disabled).toBe(false);
  });

  it("shows the message of other save errors", async () => {
    const {hass, callWS, real} = spied();
    const el = await open(hass);
    await addBlockRight(el);
    callWS.mockImplementation((msg: {type: string}) =>
      msg.type === "ha_controller/layout/save" ? Promise.reject({code: "not_found", message: "Screen not found"}) : real(msg),
    );
    await click(el, saveButton(el));
    expect(one(el, ".notice")!.textContent).toContain("Screen not found");
  });

  describe("with fake timers", () => {
    beforeEach(() => vi.useFakeTimers());

    it("refresh does not reset working copy", async () => {
      const {hass, callWS} = spied();
      const el = await open(hass);
      await addBlockRight(el);
      callWS.mockClear();
      await vi.advanceTimersByTimeAsync(10_000);
      await settle(el);
      expect(callWS.mock.calls.map((c) => c[0].type)).toEqual(["ha_controller/screens"]);
      el.hass = {...hass};
      await settle(el);
      expect(blocks(el)).toHaveLength(5);
      expect(callWS.mock.calls.map((c) => c[0].type)).toEqual(["ha_controller/screens"]);
    });

    it("stops refreshing when removed", async () => {
      const {hass, callWS} = spied();
      const el = await open(hass);
      el.remove();
      callWS.mockClear();
      await vi.advanceTimersByTimeAsync(30_000);
      expect(callWS).not.toHaveBeenCalled();
    });
  });

  it("changing the sleep delay enables Save and sends it", async () => {
    const {hass, callWS} = spied();
    const el = await open(hass);
    const input = one<HTMLInputElement>(el, 'input[name="sleep_timeout"]')!;
    expect(input.value).toBe("20");
    input.value = "45";
    input.dispatchEvent(new Event("input"));
    await settle(el);
    expect(saveButton(el).disabled).toBe(false);
    await click(el, saveButton(el));
    const call = saveCall(callWS);
    expect(call.layout.settings.sleep_timeout).toBe(45);
  });

  it("disables Save and lists local errors for an invalid sleep delay", async () => {
    const {hass} = spied();
    const el = await open(hass);
    const input = one<HTMLInputElement>(el, 'input[name="sleep_timeout"]')!;
    input.value = "2";
    input.dispatchEvent(new Event("input"));
    await settle(el);
    expect(saveButton(el).disabled).toBe(true);
    expect(one(el, ".errors")!.textContent).toContain("The sleep delay must be 0");
  });

  describe("status line", () => {
    it("reports update available", async () => {
      const el = await open(spied({firmware_version: "0.0.9"}).hass);
      expect(one(el, ".status")!.textContent).toContain("Online · firmware 0.0.9 — update available");
    });
    it("reports in sync", async () => {
      const el = await open(spied().hass);
      expect(one(el, ".status")!.textContent).toContain("Online · firmware 0.1.0 · in sync");
    });
    it("reports syncing", async () => {
      const el = await open(spied({device_revision: "old"}).hass);
      expect(one(el, ".status")!.textContent).toContain("Online · firmware 0.1.0 · syncing…");
    });
    it("reports offline", async () => {
      const el = await open(spied({online: false}).hass);
      expect(one(el, ".status")!.textContent?.trim()).toBe("Offline");
    });
  });

  it("shows the menu button only when narrow", async () => {
    const {hass} = spied();
    const el = await open(hass);
    expect(one(el, "ha-menu-button")).toBeNull();
    el.narrow = true;
    await settle(el);
    expect(one(el, "ha-menu-button")).not.toBeNull();
  });
});
