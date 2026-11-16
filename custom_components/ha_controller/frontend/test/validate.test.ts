import {describe, expect, it} from "vitest";
import {EMOJI_SET} from "../src/model/emoji";
import {validateLayout} from "../src/model/validate";
import {colors, invalidLayouts, validLayouts} from "./fixtures";

describe("validateLayout", () => {
  it("has fixtures", () => {
    expect(Object.keys(validLayouts).length).toBeGreaterThan(0);
    expect(Object.keys(invalidLayouts).length).toBeGreaterThan(0);
    expect(colors.length).toBeGreaterThan(0);
  });
  for (const [name, layout] of Object.entries(validLayouts)) {
    it(`accepts valid/${name}`, () => {
      expect(validateLayout(layout, EMOJI_SET)).toEqual([]);
    });
  }
  for (const [name, c] of Object.entries(invalidLayouts)) {
    it(`rejects invalid/${name}`, () => {
      expect(validateLayout(c.layout, EMOJI_SET)).toEqual([c.expect]);
    });
  }
});
