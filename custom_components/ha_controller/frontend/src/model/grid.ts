import type {Block, Cell, Layout} from "../types";
import {COORD_LIMIT, MAX_BLOCKS} from "./limits";

const DIRECTIONS: readonly Cell[] = [
  {x: 1, y: 0},
  {x: -1, y: 0},
  {x: 0, y: 1},
  {x: 0, y: -1},
];

const key = (x: number, y: number): string => `${x},${y}`;

/** Empty cells next to a block, within the coordinate limit, sorted by y then x. */
export function placeholders(layout: Layout): Cell[] {
  const {blocks} = layout;
  if (blocks.length === 0) return [{x: 0, y: 0}];
  if (blocks.length >= MAX_BLOCKS) return [];
  const taken = new Set(blocks.map((b) => key(b.x, b.y)));
  const found = new Map<string, Cell>();
  for (const block of blocks) {
    for (const d of DIRECTIONS) {
      const x = block.x + d.x;
      const y = block.y + d.y;
      if (Math.abs(x) > COORD_LIMIT || Math.abs(y) > COORD_LIMIT) continue;
      const k = key(x, y);
      if (!taken.has(k)) found.set(k, {x, y});
    }
  }
  return [...found.values()].sort((a, b) => a.y - b.y || a.x - b.x);
}

/** Ids of the blocks reachable from the start block through adjacent blocks. */
export function reachable(blocks: Block[], start: string | null): Set<string> {
  const first = blocks.find((b) => b.id === start);
  if (!first) return new Set();
  const byCell = new Map(blocks.map((b) => [key(b.x, b.y), b]));
  const seen = new Set([first.id]);
  const queue = [first];
  while (queue.length > 0) {
    const current = queue.shift() as Block;
    for (const d of DIRECTIONS) {
      const next = byCell.get(key(current.x + d.x, current.y + d.y));
      if (next && !seen.has(next.id)) {
        seen.add(next.id);
        queue.push(next);
      }
    }
  }
  return seen;
}

export type DeleteCheck = {ok: true} | {ok: false; reason: "start" | "disconnects"};

export function canDelete(layout: Layout, id: string): DeleteCheck {
  if (layout.blocks.length > 1 && layout.start === id) return {ok: false, reason: "start"};
  const rest = layout.blocks.filter((b) => b.id !== id);
  if (rest.length === 0) return {ok: true};
  const seen = reachable(rest, layout.start);
  return rest.every((b) => seen.has(b.id)) ? {ok: true} : {ok: false, reason: "disconnects"};
}

export function gridBounds(cells: Cell[]): {minX: number; maxX: number; minY: number; maxY: number} {
  const xs = cells.map((c) => c.x);
  const ys = cells.map((c) => c.y);
  return {minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys)};
}
