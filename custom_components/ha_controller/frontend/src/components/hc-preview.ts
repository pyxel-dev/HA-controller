import {LitElement, css, html} from "lit";
import {property} from "lit/decorators.js";
import {defineElement} from "../define";
import {textColorFor} from "../model/color";
import {UI} from "../messages";
import type {Block, Hass, Item} from "../types";

const SIZES: Record<string, string> = {s: "11px", m: "14px", l: "18px", xl: "24px"};

/** Round preview of a block, approximating the screen. */
export class HcPreview extends LitElement {
  @property({attribute: false}) block?: Block;
  @property({attribute: false}) hass?: Hass;

  static styles = css`
    :host {
      display: block;
    }
    .circle {
      box-sizing: border-box;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      margin: 0 auto;
      padding: 32px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      overflow: hidden;
      overflow-wrap: anywhere;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }
    .name {
      font-weight: 600;
    }
  `;

  private stateOf(entityId: string | undefined, attribute?: string | null): string {
    const entity = entityId ? this.hass?.states[entityId] : undefined;
    if (!entity) return UI.unavailable;
    if (attribute) return String(entity.attributes[attribute] ?? "");
    const unit = entity.attributes.unit_of_measurement;
    return typeof unit === "string" ? `${entity.state} ${unit}` : entity.state;
  }

  private line(block: Block, item: Item) {
    let text = "";
    switch (item.kind) {
      case "text": text = item.text ?? ""; break;
      case "emoji": text = item.emoji ?? ""; break;
      case "entity": text = this.stateOf(item.entity_id, item.attribute); break;
      case "battery": text = UI.previewBattery; break;
      case "brightness": text = UI.previewBrightness; break;
    }
    return html`<div class="line" style="font-size: ${SIZES[item.font_size ?? block.font_size]}">${text}</div>`;
  }

  render() {
    const block = this.block;
    if (!block) return html``;
    return html`<div
      class="circle"
      style="background: ${block.background}; color: ${textColorFor(block.background)}; font-size: ${SIZES[block.font_size]}"
    >
      <div class="name">${block.name}</div>
      ${block.type === "entity"
        ? html`<div class="line">${this.stateOf(block.entity_id)}</div>`
        : (block.items ?? []).map((item) => this.line(block, item))}
    </div>`;
  }
}

defineElement("hc-preview", HcPreview);

declare global {
  interface HTMLElementTagNameMap {
    "hc-preview": HcPreview;
  }
}
