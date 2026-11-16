import {LitElement, css, html, nothing} from "lit";
import {customElement, property} from "lit/decorators.js";
import {gridBounds, placeholders} from "../model/grid";
import {textColorFor} from "../model/color";
import type {Layout} from "../types";

/** Block map: x grows to the right, y grows downwards, like navigation on the screen. */
@customElement("hc-grid")
export class HcGrid extends LitElement {
  @property({attribute: false}) layout: Layout = {version: 1, start: null, settings: {sleep_timeout: 0}, blocks: []};
  @property({attribute: false}) selectedId: string | null = null;
  @property({attribute: false}) errorRefs: ReadonlySet<string> = new Set();

  static styles = css`
    :host {
      display: block;
      overflow: auto;
    }
    .grid {
      display: grid;
      grid-auto-columns: 96px;
      grid-auto-rows: 96px;
      gap: 12px;
      padding: 12px;
      width: max-content;
    }
    button {
      all: unset;
      box-sizing: border-box;
      cursor: pointer;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      position: relative;
      font: inherit;
      font-weight: 500;
      padding: 8px;
      overflow: hidden;
      overflow-wrap: anywhere;
    }
    button:focus-visible {
      box-shadow: 0 0 0 3px var(--primary-color, #03a9f4);
    }
    .block.start {
      outline: 3px solid var(--primary-text-color, #212121);
      outline-offset: -3px;
    }
    .block.selected {
      box-shadow: 0 0 0 3px var(--card-background-color, #fff), 0 0 0 6px var(--primary-color, #03a9f4);
      overflow: visible;
    }
    .block.has-error {
      box-shadow: 0 0 0 3px var(--card-background-color, #fff), 0 0 0 6px var(--error-color, #db4437);
      overflow: visible;
    }
    .start-badge {
      position: absolute;
      top: 6px;
      left: 8px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      opacity: 0.8;
    }
    .placeholder {
      border: 2px dashed var(--divider-color, rgba(0, 0, 0, 0.12));
      color: var(--secondary-text-color, #727272);
      font-size: 28px;
      font-weight: 300;
    }
    .placeholder:hover {
      border-color: var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }
  `;

  render() {
    const {blocks, start} = this.layout;
    const empty = placeholders(this.layout);
    const cells = [...blocks, ...empty];
    if (cells.length === 0) return nothing;
    const {minX, minY} = gridBounds(cells);
    const place = (x: number, y: number) => `grid-column: ${x - minX + 1}; grid-row: ${y - minY + 1}`;
    return html`<div class="grid">
      ${blocks.map(
        (b) => html`<button
          class="block ${b.id === start ? "start" : ""} ${b.id === this.selectedId ? "selected" : ""} ${this.errorRefs.has(b.id) ? "has-error" : ""}"
          data-id=${b.id}
          style="${place(b.x, b.y)}; background: ${b.background}; color: ${textColorFor(b.background)}"
          @click=${() => this.emit("hc-select-block", {id: b.id})}
        >
          ${b.id === start ? html`<span class="start-badge">start</span>` : nothing}${b.name}
        </button>`,
      )}
      ${empty.map(
        (c) => html`<button
          class="placeholder"
          data-x=${c.x}
          data-y=${c.y}
          style=${place(c.x, c.y)}
          aria-label="Add block"
          @click=${() => this.emit("hc-add-block", {x: c.x, y: c.y})}
        >+</button>`,
      )}
    </div>`;
  }

  private emit(name: string, detail: unknown): void {
    this.dispatchEvent(new CustomEvent(name, {detail, bubbles: true, composed: true}));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hc-grid": HcGrid;
  }
}
