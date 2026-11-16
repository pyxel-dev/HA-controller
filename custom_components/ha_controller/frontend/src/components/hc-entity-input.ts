import {LitElement, css, html} from "lit";
import {property} from "lit/decorators.js";
import {defineElement} from "../define";
import type {Hass} from "../types";

let counter = 0;

/** Entity picker built from `hass.states`: a text input with a datalist of matching ids. */
export class HcEntityInput extends LitElement {
  @property({attribute: false}) hass?: Hass;
  @property() value = "";
  @property({attribute: false}) domains?: string[];

  private readonly listId = `entities-${counter++}`;

  static styles = css`
    :host {
      display: block;
    }
    input {
      box-sizing: border-box;
      width: 100%;
      font: inherit;
      padding: 6px 8px;
      color: var(--primary-text-color, #212121);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
  `;

  render() {
    const ids = Object.keys(this.hass?.states ?? {})
      .filter((id) => !this.domains || this.domains.includes(id.split(".")[0]))
      .sort();
    return html`<input
        type="text"
        list=${this.listId}
        aria-label="Entity"
        placeholder="domain.entity"
        .value=${this.value ?? ""}
        @change=${(e: Event) => this.emit((e.target as HTMLInputElement).value.trim())}
      />
      <datalist id=${this.listId}>
        ${ids.map((id) => {
          const name = this.hass?.states[id]?.attributes.friendly_name;
          return html`<option value=${id} label=${typeof name === "string" ? name : id}></option>`;
        })}
      </datalist>`;
  }

  private emit(value: string): void {
    this.dispatchEvent(new CustomEvent("hc-value-change", {detail: {value}, bubbles: true, composed: true}));
  }
}

defineElement("hc-entity-input", HcEntityInput);

declare global {
  interface HTMLElementTagNameMap {
    "hc-entity-input": HcEntityInput;
  }
}
