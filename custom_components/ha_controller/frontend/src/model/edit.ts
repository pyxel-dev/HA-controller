import type {Block, Cell, Item, ItemKind, Layout} from "../types";
import {canDelete} from "./grid";
import {MAX_BLOCKS} from "./limits";

export const PALETTE: readonly string[] = [
  "#C94F3D", "#4F86DD", "#5B9E4D", "#7B2FA0", "#E08A2E", "#2E9E8F", "#D2477A", "#5C6BC0",
];

const suffix = (id: string, prefix: string): number =>
  id.startsWith(prefix) && /^\d+$/.test(id.slice(prefix.length)) ? Number(id.slice(prefix.length)) : 0;

/** One plus the highest numeric suffix among block and item ids with this prefix. */
export function nextId(layout: Layout, prefix: "b" | "i"): string {
  let max = 0;
  for (const block of layout.blocks) {
    max = Math.max(max, suffix(block.id, prefix));
    for (const item of block.items ?? []) max = Math.max(max, suffix(item.id, prefix));
  }
  return `${prefix}${max + 1}`;
}

export function addBlock(layout: Layout, cell: Cell): {layout: Layout; id: string} {
  if (layout.blocks.length >= MAX_BLOCKS) throw new Error("too_many_blocks");
  const id = nextId(layout, "b");
  const block: Block = {
    id,
    x: cell.x,
    y: cell.y,
    name: `Block ${suffix(id, "b")}`,
    background: PALETTE[layout.blocks.length % PALETTE.length],
    font_size: "m",
    type: "custom",
    items: [],
  };
  return {layout: {...layout, start: layout.start ?? id, blocks: [...layout.blocks, block]}, id};
}

export function deleteBlock(layout: Layout, id: string): Layout {
  const check = canDelete(layout, id);
  if (!check.ok) throw new Error(check.reason);
  const blocks = layout.blocks.filter((b) => b.id !== id);
  return {...layout, start: blocks.length === 0 ? null : layout.start, blocks};
}

export function setStart(layout: Layout, id: string): Layout {
  return {...layout, start: id};
}

export function updateBlock(layout: Layout, id: string, patch: Partial<Block>): Layout {
  return {...layout, blocks: layout.blocks.map((b) => (b.id === id ? {...b, ...patch} : b))};
}

export function setSleepTimeout(layout: Layout, seconds: number): Layout {
  return {...layout, settings: {...layout.settings, sleep_timeout: seconds}};
}

function withItems(layout: Layout, blockId: string, change: (items: Item[]) => Item[]): Layout {
  return {
    ...layout,
    blocks: layout.blocks.map((b) => (b.id === blockId ? {...b, items: change(b.items ?? [])} : b)),
  };
}

const DEFAULT_ITEMS: Record<ItemKind, Partial<Item>> = {
  text: {text: "Text"},
  emoji: {emoji: "💡"},
  entity: {entity_id: "", attribute: null},
  battery: {},
  brightness: {},
};

export function addItem(layout: Layout, blockId: string, kind: ItemKind): {layout: Layout; id: string} {
  const id = nextId(layout, "i");
  const item: Item = {id, kind, ...DEFAULT_ITEMS[kind], font_size: null};
  return {layout: withItems(layout, blockId, (items) => [...items, item]), id};
}

export function updateItem(layout: Layout, blockId: string, itemId: string, patch: Partial<Item>): Layout {
  return withItems(layout, blockId, (items) => items.map((i) => (i.id === itemId ? {...i, ...patch} : i)));
}

export function removeItem(layout: Layout, blockId: string, itemId: string): Layout {
  return withItems(layout, blockId, (items) => items.filter((i) => i.id !== itemId));
}

export function moveItem(layout: Layout, blockId: string, itemId: string, delta: -1 | 1): Layout {
  return withItems(layout, blockId, (items) => {
    const from = items.findIndex((i) => i.id === itemId);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= items.length) return items;
    const next = [...items];
    [next[from], next[to]] = [next[to], next[from]];
    return next;
  });
}
