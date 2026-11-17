import {LitElement, css, html} from "lit";
import {property} from "lit/decorators.js";
import {defineElement} from "../define";
import {UI} from "../messages";
import {SUPPORTED_EMOJI, normalizeEmoji} from "../model/emoji";

/** Grid of the emoji the screen can render. */
export class HcEmojiPicker extends LitElement {
  @property() value = "";

  static styles = css`
    :host {
      display: block;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      gap: 4px;
    }
    button {
      font-size: 20px;
      padding: 4px;
      cursor: pointer;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
    button[aria-pressed="true"] {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
    }
  `;

  render() {
    const current = normalizeEmoji(this.value ?? "");
    return html`<div class="grid" role="group" aria-label=${UI.emoji}>
      ${SUPPORTED_EMOJI.map(
        (e) => html`<button
          type="button"
          class="emoji"
          aria-label=${e}
          aria-pressed=${normalizeEmoji(e) === current ? "true" : "false"}
          @click=${() => this.emit(e)}
        >${e}</button>`,
      )}
    </div>`;
  }

  private emit(value: string): void {
    this.dispatchEvent(
      new CustomEvent("hc-value-change", {detail: {value: normalizeEmoji(value)}, bubbles: true, composed: true}),
    );
  }
}

defineElement("hc-emoji-picker", HcEmojiPicker);

declare global {
  interface HTMLElementTagNameMap {
    "hc-emoji-picker": HcEmojiPicker;
  }
}
