export type FontSize = "s" | "m" | "l" | "xl";
export type ItemKind = "text" | "emoji" | "entity" | "battery" | "brightness";

export interface Item {
  id: string;
  kind: ItemKind;
  font_size: FontSize | null;
  text?: string;
  emoji?: string;
  entity_id?: string;
  attribute?: string | null;
}

export interface Block {
  id: string;
  x: number;
  y: number;
  name: string;
  background: string;
  font_size: FontSize;
  type: "entity" | "custom";
  entity_id?: string;
  items?: Item[];
}

export interface Layout {
  version: 1;
  start: string | null;
  settings: {sleep_timeout: number};
  blocks: Block[];
}

export interface LayoutError {
  code: string;
  ref: string | null;
}

export interface Cell {
  x: number;
  y: number;
}

/** Screen status as sent by the websocket API (spec section 8). */
export interface ScreenInfo {
  device_id: string;
  name: string;
  online: boolean;
  firmware_version: string | null;
  battery: number | null;
  charging: boolean | null;
  brightness: number | null;
  layout: Layout;
  [key: string]: unknown;
}

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface Hass {
  states: Record<string, HassEntity>;
  callWS<T>(msg: {type: string; [key: string]: unknown}): Promise<T>;
}
