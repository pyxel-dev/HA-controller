import {describe, expect, it} from "vitest";
import {EMOJI_SET, SUPPORTED_EMOJI, normalizeEmoji} from "../src/model/emoji";

describe("emoji", () => {
  it("has 64 supported emoji", () => {
    expect(SUPPORTED_EMOJI).toHaveLength(64);
    expect(EMOJI_SET.size).toBe(64);
  });
  it("strips the variation selector", () => {
    expect(normalizeEmoji("❄️")).toBe("❄");
    expect(normalizeEmoji("💡")).toBe("💡");
  });
});
