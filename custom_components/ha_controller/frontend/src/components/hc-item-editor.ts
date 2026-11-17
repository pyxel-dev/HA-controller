import {LitElement, css, html, nothing} from "lit";
import {property} from "lit/decorators.js";
import {defineElement} from "../define";
import "./hc-entity-input";
import "./hc-emoji-picker";
import {FONT_SIZE_LABEL, FONT_SIZE_ORDER, ITEM_KIND_LABEL, UI} from "../messages";
import type {FontSize, Hass, Item} from "../types";

/** Editor for one item of a custom block. */
export class HcItemEditor extends LitElement {
  @property({attribute: false}) hass?: Hass;
  @property({attribute: false}) item!: Item;
  @property({type: Number}) index = 0;
  @property({type: Number}) count = 0;

  static styles = css`
    :host {
      display: block;
    }
    .item {
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 8px;
      padding: 8px;
      display: grid;
      gap: 8px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #212121);
    }
    .head,
    .actions {
      display: flex;
      gap: 6px;
      align-items: center;
    }
    .head strong {
      flex: 1;
    }
    input[type="text"] {
      box-sizing: border-box;
      width: 100%;
      font: inherit;
      padding: 6px 8px;
      color: var(--primary-text-color, #212121);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
    label {
      font-size: 12px;
      color: var(--secondary-text-color, #727272);
    }
    button.remove {
      color: var(--error-color, #db4437);
    }
  `;

  render() {
    const item = this.item;
    return html`<div class="item">
      <div class="head">
        <strong>${ITEM_KIND_LABEL[item.kind]}</strong>
        <button type="button" class="up" aria-label=${UI.moveUp} ?disabled=${this.index <= 0} @click=${() => this.move(-1)}>↑</button>
        <button type="button" class="down" aria-label=${UI.moveDown} ?disabled=${this.index >= this.count - 1} @click=${() => this.move(1)}>↓</button>
        <button type="button" class="remove" aria-label=${UI.removeItem} @click=${() => this.emit("hc-item-remove")}>✕</button>
      </div>
      ${this.fields(item)}
      <div class="actions">
        <label for="font-size">${UI.fontSize}</label>
        <select id="font-size" name="font-size" @change=${this.onFontSize}>
          <option value="">${UI.fontSizeInherit}</option>
          ${FONT_SIZE_ORDER.map((size) => html`<option value=${size}>${FONT_SIZE_LABEL[size]}</option>`)}
        </select>
      </div>
    </div>`;
  }

  protected updated(): void {
    const select = this.renderRoot.querySelector<HTMLSelectElement>("select[name=font-size]");
    if (select) select.value = this.item.font_size ?? "";
  }

  private fields(item: Item) {
    switch (item.kind) {
      case "text":
        return html`<input
          type="text"
          name="text"
          aria-label=${UI.text}
          maxlength="64"
          .value=${item.text ?? ""}
          @input=${(e: Event) => this.patch({text: (e.target as HTMLInputElement).value})}
        />`;
      case "emoji":
        return html`<hc-emoji-picker
          .value=${item.emoji ?? ""}
          @hc-value-change=${(e: CustomEvent<{value: string}>) => {
            e.stopPropagation();
            this.patch({emoji: e.detail.value});
          }}
        ></hc-emoji-picker>`;
      case "entity":
        return html`<hc-entity-input
            .hass=${this.hass}
            .value=${item.entity_id ?? ""}
            @hc-value-change=${(e: CustomEvent<{value: string}>) => {
              e.stopPropagation();
              this.patch({entity_id: e.detail.value});
            }}
          ></hc-entity-input>
          <input
            type="text"
            name="attribute"
            aria-label=${UI.attributeOptional}
            placeholder=${UI.attributeOptional}
            .value=${item.attribute ?? ""}
            @input=${(e: Event) => this.patch({attribute: (e.target as HTMLInputElement).value || null})}
          />`;
      default:
        return nothing;
    }
  }

  private onFontSize = (e: Event): void => {
    const value = (e.target as HTMLSelectElement).value;
    this.patch({font_size: value === "" ? null : (value as FontSize)});
  };

  private patch(patch: Partial<Item>): void {
    this.emit("hc-item-change", {patch});
  }

  private move(delta: -1 | 1): void {
    this.emit("hc-item-move", {delta});
  }

  private emit(name: string, detail?: unknown): void {
    this.dispatchEvent(new CustomEvent(name, {detail, bubbles: true, composed: true}));
  }
}

defineElement("hc-item-editor", HcItemEditor);

declare global {
  interface HTMLElementTagNameMap {
    "hc-item-editor": HcItemEditor;
  }
}
