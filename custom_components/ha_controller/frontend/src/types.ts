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

/** One screen as listed by `ha_controller/screens` (spec section 8). */
export interface ScreenInfo {
  entry_id: string;
  title: string;
  device_id: string;
  online: boolean;
  firmware_version: string | null;
  integration_version: string;
  protocol_ok: boolean | null;
  revision: string;
  device_revision: string | null;
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
