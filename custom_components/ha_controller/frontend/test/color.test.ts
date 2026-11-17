import {describe, expect, it} from "vitest";
import {textColorFor} from "../src/model/color";
import {colors} from "./fixtures";

describe("textColorFor", () => {
  it("matches the shared vectors", () => {
    expect(colors.length).toBeGreaterThan(0);
    for (const c of colors) expect(textColorFor(c.bg)).toBe(c.text);
  });
});
