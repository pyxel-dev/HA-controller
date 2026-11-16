import emoji from "../../../emoji.json";

export const SUPPORTED_EMOJI: readonly string[] = emoji;
export const EMOJI_SET: ReadonlySet<string> = new Set(SUPPORTED_EMOJI);

/** Remove the emoji variation selector U+FE0F. */
export function normalizeEmoji(text: string): string {
  return text.replaceAll("️", "");
}
