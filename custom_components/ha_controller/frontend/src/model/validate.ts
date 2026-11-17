import type {Block, LayoutError} from "../types";
import {normalizeEmoji} from "./emoji";
import {reachable} from "./grid";
import {COORD_LIMIT, MAX_BLOCKS, MAX_ITEMS} from "./limits";

const MAX_NAME_LEN = 32;
const MAX_TEXT_LEN = 64;
const MAX_ATTRIBUTE_LEN = 64;
const MIN_SLEEP_TIMEOUT = 5;
const MAX_SLEEP_TIMEOUT = 3600;
const FONT_SIZES = ["s", "m", "l", "xl"];
const ITEM_KINDS = ["text", "emoji", "entity", "battery", "brightness"];
const ENTITY_BLOCK_DOMAINS = ["light", "climate"];

const ID_RE = /^[a-z][a-z0-9]{0,7}$/;
const COLOR_RE = /^#[0-9A-Fa-f]{6}$/;
const ENTITY_RE = /^[a-z0-9_]+\.[a-z0-9_]+$/;

type Obj = Record<string, unknown>;

const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const isInt = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const isId = (v: unknown): v is string => typeof v === "string" && ID_RE.test(v);
const isEntityId = (v: unknown): v is string => typeof v === "string" && ENTITY_RE.test(v);
const cpLen = (s: string): number => Array.from(s).length;
const refOf = (v: unknown): string | null => (typeof v === "string" ? v : null);

function checkStructure(layout: unknown): layout is Obj & {settings: Obj; blocks: Obj[]} {
  if (!isObj(layout) || layout.version !== 1 || !isObj(layout.settings)) return false;
  const blocks = layout.blocks;
  if (!Array.isArray(blocks) || !blocks.every(isObj)) return false;
  for (const block of blocks as Obj[]) {
    if (block.type === "custom") {
      const items = block.items;
      if (!Array.isArray(items) || !items.every(isObj)) return false;
    }
  }
  return true;
}

function validEntityItem(item: Obj): boolean {
  if (!isEntityId(item.entity_id)) return false;
  const attr = item.attribute;
  return attr === undefined || attr === null ||
    (typeof attr === "string" && cpLen(attr) >= 1 && cpLen(attr) <= MAX_ATTRIBUTE_LEN);
}

function validEntityBlock(block: Obj): boolean {
  const id = block.entity_id;
  return isEntityId(id) && ENTITY_BLOCK_DOMAINS.includes(id.split(".", 1)[0]);
}

function checkItem(item: Obj, seen: Set<string>, emoji: ReadonlySet<string>, errors: LayoutError[]): void {
  const ref = refOf(item.id);
  if (!isId(item.id)) errors.push({code: "invalid_id", ref});
  if (typeof item.id === "string") {
    if (seen.has(item.id)) errors.push({code: "duplicate_id", ref: item.id});
    seen.add(item.id);
  }
  const kind = item.kind;
  if (typeof kind !== "string" || !ITEM_KINDS.includes(kind)) errors.push({code: "invalid_item", ref});
  const fontSize = item.font_size;
  if (fontSize !== undefined && fontSize !== null &&
      (typeof fontSize !== "string" || !FONT_SIZES.includes(fontSize))) {
    errors.push({code: "invalid_font_size", ref});
  }
  if (kind === "text") {
    const text = item.text;
    if (typeof text !== "string" || cpLen(text) < 1 || cpLen(text) > MAX_TEXT_LEN) {
      errors.push({code: "invalid_text", ref});
    }
  } else if (kind === "emoji") {
    const value = item.emoji;
    if (typeof value !== "string" || !emoji.has(normalizeEmoji(value))) {
      errors.push({code: "unsupported_emoji", ref});
    }
  } else if (kind === "entity" && !validEntityItem(item)) {
    errors.push({code: "invalid_entity", ref});
  }
}

function checkBlock(
  block: Obj, seen: Set<string>, positions: Set<string>, emoji: ReadonlySet<string>, errors: LayoutError[],
): void {
  const ref = refOf(block.id);
  if (!isId(block.id)) errors.push({code: "invalid_id", ref});
  if (typeof block.id === "string") {
    if (seen.has(block.id)) errors.push({code: "duplicate_id", ref: block.id});
    seen.add(block.id);
  }

  const {x, y} = block;
  if (![x, y].every((v) => isInt(v) && Math.abs(v) <= COORD_LIMIT)) {
    errors.push({code: "coordinate_out_of_range", ref});
  } else {
    const k = `${x},${y}`;
    if (positions.has(k)) errors.push({code: "duplicate_position", ref});
    positions.add(k);
  }

  const name = block.name;
  if (typeof name !== "string" || cpLen(name.trim()) < 1 || cpLen(name.trim()) > MAX_NAME_LEN) {
    errors.push({code: "invalid_name", ref});
  }
  if (typeof block.background !== "string" || !COLOR_RE.test(block.background)) {
    errors.push({code: "invalid_background", ref});
  }
  if (typeof block.font_size !== "string" || !FONT_SIZES.includes(block.font_size)) {
    errors.push({code: "invalid_font_size", ref});
  }

  if (block.type === "entity") {
    if (!validEntityBlock(block)) errors.push({code: "invalid_entity", ref});
  } else if (block.type === "custom") {
    const items = block.items as Obj[];
    if (items.length > MAX_ITEMS) errors.push({code: "too_many_items", ref});
    for (const item of items) checkItem(item, seen, emoji, errors);
  } else {
    errors.push({code: "invalid_type", ref});
  }
}

function unreachable(layout: Obj & {blocks: Obj[]}): LayoutError[] {
  if (layout.blocks.length === 0) return [];
  const blocks = layout.blocks as unknown as Block[];
  const seen = reachable(blocks, layout.start as string);
  return blocks.filter((b) => !seen.has(b.id)).map((b) => ({code: "disconnected", ref: b.id}));
}

/** Validate a layout; an empty list means it is valid. Mirrors layout.py. */
export function validateLayout(layout: unknown, emoji: ReadonlySet<string>): LayoutError[] {
  if (!checkStructure(layout)) return [{code: "invalid_structure", ref: null}];

  const errors: LayoutError[] = [];
  const blocks = layout.blocks;
  if (blocks.length > MAX_BLOCKS) errors.push({code: "too_many_blocks", ref: null});
  const timeout = layout.settings.sleep_timeout;
  if (!isInt(timeout) || !(timeout === 0 || (timeout >= MIN_SLEEP_TIMEOUT && timeout <= MAX_SLEEP_TIMEOUT))) {
    errors.push({code: "invalid_sleep_timeout", ref: null});
  }

  const seen = new Set<string>();
  const positions = new Set<string>();
  for (const block of blocks) checkBlock(block, seen, positions, emoji, errors);

  const start = layout.start;
  const startOk = start === undefined || start === null
    ? blocks.length === 0
    : typeof start === "string" && blocks.some((b) => b.id === start);
  if (!startOk) errors.push({code: "invalid_start", ref: null});

  return errors.length > 0 ? errors : unreachable(layout);
}
