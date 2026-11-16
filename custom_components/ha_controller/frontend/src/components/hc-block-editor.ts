import {LitElement, css, html, nothing} from "lit";
import {property} from "lit/decorators.js";
import {defineElement} from "../define";
import "./hc-entity-input";
import "./hc-item-editor";
import "./hc-preview";
import {deleteReason} from "../messages";
import {canDelete} from "../model/grid";
import {
  PALETTE, addItem, deleteBlock, moveItem, removeItem, setStart, updateBlock, updateItem,
} from "../model/edit";
import {MAX_ITEMS} from "../model/limits";
import type {Block, FontSize, Hass, Item, ItemKind, Layout} from "../types";

const FONT_SIZES: [FontSize, string][] = [["s", "S"], ["m", "M"], ["l", "L"], ["xl", "XL"]];
const ITEM_KINDS: [ItemKind, string][] = [
  ["text", "Text"],
  ["emoji", "Emoji"],
  ["entity", "Entity state"],
  ["battery", "Battery"],
  ["brightness", "Screen brightness"],
];

/** Editor for the selected block. Emits `hc-layout-change` with the complete new layout. */
export class HcBlockEditor extends LitElement {
  @property({attribute: false}) hass?: Hass;
  @property({attribute: false}) layout!: Layout;
  @property() blockId = "";

  static styles = css`
    :host {
      display: block;
      color: var(--primary-text-color, #212121);
    }
    .form {
      display: grid;
      gap: 12px;
    }
    label,
    .label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color, #727272);
      margin-bottom: 4px;
    }
    input[type="text"],
    select {
      box-sizing: border-box;
      width: 100%;
      font: inherit;
      padding: 6px 8px;
      color: var(--primary-text-color, #212121);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
    .row {
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
    }
    button.swatch {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid transparent;
      cursor: pointer;
      padding: 0;
    }
    button.swatch[aria-pressed="true"] {
      border-color: var(--primary-text-color, #212121);
    }
    button.font-size {
      min-width: 36px;
      padding: 4px 8px;
      cursor: pointer;
      color: var(--primary-text-color, #212121);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
    button.font-size[aria-pressed="true"] {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 1px var(--primary-color, #03a9f4);
    }
    input[type="color"] {
      width: 36px;
      height: 28px;
      padding: 0;
    }
    .items {
      display: grid;
      gap: 8px;
    }
    .reason {
      font-size: 12px;
      color: var(--error-color, #db4437);
    }
    button.delete:not([disabled]) {
      color: var(--error-color, #db4437);
    }
  `;

  private get block(): Block | undefined {
    return this.layout?.blocks.find((b) => b.id === this.blockId);
  }

  render() {
    const block = this.block;
    if (!block) return nothing;
    const check = canDelete(this.layout, block.id);
    const isStart = this.layout.start === block.id;
    return html`<div class="form">
      <div>
        <label for="name">Name</label>
        <input id="name" type="text" name="name" maxlength="32" .value=${block.name} @input=${this.onName} />
      </div>
      <div>
        <span class="label" id="bg-label">Background</span>
        <div class="row" role="group" aria-labelledby="bg-label">
          ${PALETTE.map(
            (colour) => html`<button
              type="button"
              class="swatch"
              style="background: ${colour}"
              aria-label=${`Background ${colour}`}
              aria-pressed=${block.background.toLowerCase() === colour.toLowerCase() ? "true" : "false"}
              @click=${() => this.change(updateBlock(this.layout, block.id, {background: colour}))}
            ></button>`,
          )}
          <input
            type="color"
            name="background"
            aria-label="Custom background colour"
            .value=${block.background.toLowerCase()}
            @change=${(e: Event) =>
              this.change(updateBlock(this.layout, block.id, {background: (e.target as HTMLInputElement).value.toUpperCase()}))}
          />
        </div>
      </div>
      <div>
        <span class="label" id="fs-label">Font size</span>
        <div class="row" role="group" aria-labelledby="fs-label">
          ${FONT_SIZES.map(
            ([size, label]) => html`<button
              type="button"
              class="font-size"
              aria-pressed=${block.font_size === size ? "true" : "false"}
              @click=${() => this.change(updateBlock(this.layout, block.id, {font_size: size}))}
            >${label}</button>`,
          )}
        </div>
      </div>
      <div>
        <label for="type">Type</label>
        <select id="type" name="type" @change=${this.onType}>
          <option value="entity">Entity</option>
          <option value="custom">Custom</option>
        </select>
      </div>
      ${block.type === "entity" ? this.entityFields(block) : this.customFields(block)}
      <div class="row">
        <button type="button" class="start" ?disabled=${isStart} @click=${() => this.change(setStart(this.layout, block.id))}>
          Set as start block
        </button>
        <button
          type="button"
          class="delete"
          ?disabled=${!check.ok}
          @click=${() => this.change(deleteBlock(this.layout, block.id))}
        >Delete block</button>
      </div>
      ${check.ok ? nothing : html`<div class="reason">${deleteReason[check.reason]}</div>`}
      <hc-preview .block=${block} .hass=${this.hass}></hc-preview>
    </div>`;
  }

  protected updated(): void {
    const select = this.renderRoot.querySelector<HTMLSelectElement>("select[name=type]");
    if (select && this.block) select.value = this.block.type;
  }

  private entityFields(block: Block) {
    return html`<div>
      <span class="label">Entity</span>
      <hc-entity-input
        .hass=${this.hass}
        .value=${block.entity_id ?? ""}
        .domains=${["light", "climate"]}
        @hc-value-change=${(e: CustomEvent<{value: string}>) => {
          e.stopPropagation();
          this.change(updateBlock(this.layout, block.id, {entity_id: e.detail.value}));
        }}
      ></hc-entity-input>
    </div>`;
  }

  private customFields(block: Block) {
    const items = block.items ?? [];
    return html`<div class="items">
      ${items.map(
        (item, index) => html`<hc-item-editor
          .hass=${this.hass}
          .item=${item}
          .index=${index}
          .count=${items.length}
          @hc-item-change=${(e: CustomEvent<{patch: Partial<Item>}>) => {
            e.stopPropagation();
            this.change(updateItem(this.layout, block.id, item.id, e.detail.patch));
          }}
          @hc-item-move=${(e: CustomEvent<{delta: -1 | 1}>) => {
            e.stopPropagation();
            this.change(moveItem(this.layout, block.id, item.id, e.detail.delta));
          }}
          @hc-item-remove=${(e: Event) => {
            e.stopPropagation();
            this.change(removeItem(this.layout, block.id, item.id));
          }}
        ></hc-item-editor>`,
      )}
      <div>
        <label for="add-item">Add item</label>
        <select id="add-item" name="add-item" ?disabled=${items.length >= MAX_ITEMS} @change=${this.onAddItem}>
          <option value="">Add item…</option>
          ${ITEM_KINDS.map(([kind, label]) => html`<option value=${kind}>${label}</option>`)}
        </select>
      </div>
    </div>`;
  }

  private onName = (e: Event): void => {
    const block = this.block;
    if (block) this.change(updateBlock(this.layout, block.id, {name: (e.target as HTMLInputElement).value}));
  };

  private onType = (e: Event): void => {
    const block = this.block;
    if (!block) return;
    const type = (e.target as HTMLSelectElement).value as Block["type"];
    if (type === block.type) return;
    this.change(updateBlock(this.layout, block.id, type === "custom" ? {type, items: block.items ?? []} : {type}));
  };

  private onAddItem = (e: Event): void => {
    const select = e.target as HTMLSelectElement;
    const block = this.block;
    if (!block || select.value === "") return;
    const kind = select.value as ItemKind;
    select.value = "";
    this.change(addItem(this.layout, block.id, kind).layout);
  };

  private change(layout: Layout): void {
    this.dispatchEvent(new CustomEvent("hc-layout-change", {detail: {layout}, bubbles: true, composed: true}));
  }
}

defineElement("hc-block-editor", HcBlockEditor);

declare global {
  interface HTMLElementTagNameMap {
    "hc-block-editor": HcBlockEditor;
  }
}
