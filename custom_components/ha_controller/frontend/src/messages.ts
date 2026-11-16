import type {FontSize, ItemKind} from "./types";

/** English UI strings for validation error codes and delete refusals. */
const ERRORS: Record<string, string> = {
  invalid_structure: "The layout is malformed.",
  too_many_blocks: "A screen holds at most 32 blocks.",
  invalid_id: "Invalid identifier.",
  duplicate_id: "Duplicate identifier.",
  coordinate_out_of_range: "This block is too far from the centre of the map.",
  duplicate_position: "Two blocks share the same cell.",
  invalid_start: "Choose a start block.",
  disconnected: "This block can't be reached from the start block.",
  invalid_name: "Names need 1 to 32 characters.",
  invalid_background: "Pick a background colour.",
  invalid_font_size: "Pick a font size.",
  invalid_type: "Pick a block type.",
  invalid_entity: "Pick a valid entity.",
  too_many_items: "A custom block holds at most 6 items.",
  invalid_item: "Unknown item type.",
  invalid_text: "Text needs 1 to 64 characters.",
  unsupported_emoji: "This emoji is not available on the screen.",
  payload_too_large: "The layout is too large for the screen. Remove blocks or shorten texts.",
  invalid_sleep_timeout: "The sleep delay must be 0 (never) or between 5 and 3600 seconds.",
};

export function errorMessage(code: string): string {
  return ERRORS[code] ?? "Invalid layout.";
}

export const deleteReason: Record<"start" | "disconnects", string> = {
  start: "Choose another start block first.",
  disconnects: "Other blocks would become unreachable.",
};

/** Item kind labels, in the order offered by the "add item" menu. */
export const ITEM_KIND_LABEL: Record<ItemKind, string> = {
  text: "Text",
  emoji: "Emoji",
  entity: "Entity state",
  battery: "Battery",
  brightness: "Screen brightness",
};

export const FONT_SIZE_LABEL: Record<FontSize, string> = {s: "S", m: "M", l: "L", xl: "XL"};

export const FONT_SIZE_ORDER: FontSize[] = ["s", "m", "l", "xl"];

export const UI = {
  name: "Name",
  background: "Background",
  backgroundColour: (colour: string) => `Background ${colour}`,
  customBackground: "Custom background colour",
  fontSize: "Font size",
  fontSizeInherit: "Inherit",
  type: "Type",
  typeEntity: "Entity",
  typeCustom: "Custom",
  entity: "Entity",
  entityPlaceholder: "domain.entity",
  setStart: "Set as start block",
  deleteBlock: "Delete block",
  addItemLabel: "Add item",
  addItemPlaceholder: "Add item…",
  moveUp: "Move up",
  moveDown: "Move down",
  removeItem: "Remove item",
  text: "Text",
  attributeOptional: "Attribute (optional)",
  emoji: "Emoji",
  unavailable: "unavailable",
  previewBattery: "Battery",
  previewBrightness: "Brightness",
};
