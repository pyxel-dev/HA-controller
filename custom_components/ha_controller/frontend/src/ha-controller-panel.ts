import {LitElement, css, html, nothing} from "lit";
import {property, state} from "lit/decorators.js";
import {defineElement} from "./define";
import {getLayout, listScreens, saveLayout} from "./api";
import "./components/hc-grid";
import "./components/hc-block-editor";
import {UI, errorMessage} from "./messages";
import {addBlock, setSleepTimeout} from "./model/edit";
import {EMOJI_SET} from "./model/emoji";
import {validateLayout} from "./model/validate";
import type {Hass, Layout, LayoutError, ScreenInfo} from "./types";

const REFRESH_MS = 10_000;

interface Notice {
  kind: "ok" | "error";
  text: string;
}

/** Root of the sidebar panel: screen picker, status, block map, editor and save. */
export class HaControllerPanel extends LitElement {
  @property({attribute: false}) hass?: Hass;
  @property({type: Boolean}) narrow = false;
  @property({attribute: false}) panel?: unknown;
  @property({attribute: false}) route?: unknown;

  @state() private screens: ScreenInfo[] = [];
  @state() private entryId: string | null = null;
  @state() private saved: Layout | null = null;
  @state() private layout: Layout | null = null;
  @state() private selectedId: string | null = null;
  @state() private notice: Notice | null = null;
  @state() private saving = false;

  private started = false;
  private timer?: ReturnType<typeof setInterval>;
  private loadToken = 0;

  static styles = css`
    :host {
      display: block;
      min-height: 100%;
      box-sizing: border-box;
      color: var(--primary-text-color, #212121);
      background: var(--primary-background-color, #fafafa);
      font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
    }
    header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 16px;
      padding: 12px 16px;
      background: var(--app-header-background-color, var(--card-background-color, #fff));
      color: var(--app-header-text-color, var(--primary-text-color, #212121));
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 500;
    }
    .status {
      font-size: 13px;
      color: var(--secondary-text-color, #727272);
    }
    .actions {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }
    select,
    input[type="number"] {
      font: inherit;
      padding: 6px 8px;
      color: var(--primary-text-color, #212121);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      border-radius: 6px;
    }
    button.action {
      font: inherit;
      padding: 6px 16px;
      border-radius: 6px;
      cursor: pointer;
      color: var(--primary-color, #03a9f4);
      background: transparent;
      border: 1px solid var(--primary-color, #03a9f4);
    }
    button.action.save {
      color: var(--text-primary-color, #fff);
      background: var(--primary-color, #03a9f4);
    }
    button.action:disabled {
      opacity: 0.4;
      cursor: default;
    }
    button.action:focus-visible {
      outline: 2px solid var(--primary-text-color, #212121);
      outline-offset: 2px;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 340px;
      gap: 24px;
      padding: 16px;
      align-items: start;
    }
    main.narrow {
      grid-template-columns: minmax(0, 1fr);
    }
    section {
      margin-top: 16px;
    }
    h2 {
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 500;
    }
    .help {
      margin-top: 4px;
      font-size: 12px;
      color: var(--secondary-text-color, #727272);
    }
    .errors {
      margin: 12px 0 0;
      padding-left: 20px;
      color: var(--error-color, #db4437);
    }
    .notice {
      margin: 12px 16px 0;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      background: var(--card-background-color, #fff);
    }
    .notice.error {
      color: var(--error-color, #db4437);
      border-color: var(--error-color, #db4437);
    }
    .empty {
      padding: 24px 16px;
      color: var(--secondary-text-color, #727272);
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    this.timer = setInterval(() => void this.refreshScreens(), REFRESH_MS);
  }

  disconnectedCallback(): void {
    clearInterval(this.timer);
    this.timer = undefined;
    super.disconnectedCallback();
  }

  protected updated(changed: Map<string, unknown>): void {
    if (changed.has("hass") && this.hass && !this.started) {
      this.started = true;
      void this.init();
    }
  }

  private async init(): Promise<void> {
    const hass = this.hass as Hass;
    try {
      this.screens = await listScreens(hass);
    } catch (err) {
      this.notice = {kind: "error", text: this.describe(err, UI.loadFailed)};
      return;
    }
    if (this.screens.length > 0) await this.selectScreen(this.screens[0].entry_id);
  }

  /** Refresh the screen list only; the working layout is never touched. */
  private async refreshScreens(): Promise<void> {
    if (!this.hass) return;
    try {
      this.screens = await listScreens(this.hass);
    } catch {
      // A failed refresh keeps the previous status; the next tick tries again.
    }
  }

  private async selectScreen(entryId: string): Promise<void> {
    const token = ++this.loadToken;
    try {
      const layout = await getLayout(this.hass as Hass, entryId);
      if (token !== this.loadToken) return;
      this.entryId = entryId;
      this.saved = layout;
      this.layout = layout;
      this.selectedId = layout.start ?? layout.blocks[0]?.id ?? null;
      this.notice = null;
    } catch (err) {
      if (token !== this.loadToken) return;
      this.notice = {kind: "error", text: this.describe(err, UI.loadFailed)};
    }
  }

  private describe(err: unknown, fallback: string): string {
    const message = (err as {message?: unknown} | null)?.message;
    return typeof message === "string" && message !== "" ? message : fallback;
  }

  private get errors(): LayoutError[] {
    return this.layout ? validateLayout(this.layout, EMOJI_SET) : [];
  }

  private get dirty(): boolean {
    return JSON.stringify(this.layout) !== JSON.stringify(this.saved);
  }

  private errorText(error: LayoutError): string {
    const message = errorMessage(error.code);
    const block = this.layout?.blocks.find((b) => b.id === error.ref);
    return block ? UI.withBlock(message, block.name) : message;
  }

  private setLayout(layout: Layout): void {
    this.layout = layout;
    this.notice = null;
    if (!layout.blocks.some((b) => b.id === this.selectedId)) {
      this.selectedId = layout.start ?? layout.blocks[0]?.id ?? null;
    }
  }

  private onAddBlock = (e: CustomEvent<{x: number; y: number}>): void => {
    if (!this.layout) return;
    const {layout, id} = addBlock(this.layout, e.detail);
    this.setLayout(layout);
    this.selectedId = id;
  };

  private onSleep = (e: Event): void => {
    const input = e.target as HTMLInputElement;
    if (!this.layout || input.value === "") return;
    this.setLayout(setSleepTimeout(this.layout, Number(input.value)));
  };

  private onRevert = (): void => {
    if (!this.saved) return;
    this.setLayout(this.saved);
  };

  private onSave = async (): Promise<void> => {
    if (!this.hass || !this.entryId || !this.layout || this.saving) return;
    const layout = this.layout;
    this.saving = true;
    try {
      const result = await saveLayout(this.hass, this.entryId, layout);
      this.saved = layout;
      this.notice = {kind: "ok", text: result.pushed ? UI.savedPushed : UI.savedOffline};
      void this.refreshScreens();
    } catch (err) {
      this.notice = {kind: "error", text: this.saveError(err, layout)};
    } finally {
      this.saving = false;
    }
  };

  private saveError(err: unknown, layout: Layout): string {
    const {code, message} = (err ?? {}) as {code?: string; message?: string};
    if (code === "invalid_layout" && typeof message === "string") {
      return message
        .split(",")
        .map((part) => part.trim())
        .filter((part) => part !== "")
        .map((part) => {
          const [errorCode, ref = ""] = part.split("@");
          const block = layout.blocks.find((b) => b.id === ref);
          return block ? UI.withBlock(errorMessage(errorCode), block.name) : errorMessage(errorCode);
        })
        .join(" ");
    }
    return this.describe(err, UI.saveFailed);
  }

  private get screen(): ScreenInfo | undefined {
    return this.screens.find((s) => s.entry_id === this.entryId);
  }

  private statusText(): string {
    const s = this.screen;
    if (!s) return "";
    if (!s.online) return UI.statusOffline;
    const version = s.firmware_version ?? UI.unknownVersion;
    if (s.firmware_version !== s.integration_version) return UI.statusUpdateAvailable(version);
    return s.revision === s.device_revision ? UI.statusInSync(version) : UI.statusSyncing(version);
  }

  protected render() {
    const errors = this.errors;
    const canSave = this.dirty && errors.length === 0 && !this.saving;
    return html`
      <header>
        ${this.narrow ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>` : nothing}
        <h1>${UI.title}</h1>
        ${this.screens.length > 1
          ? html`<select
              aria-label=${UI.screenSelect}
              .value=${this.entryId ?? ""}
              @change=${(e: Event) => void this.selectScreen((e.target as HTMLSelectElement).value)}
            >
              ${this.screens.map(
                (s) => html`<option value=${s.entry_id} ?selected=${s.entry_id === this.entryId}>${s.title}</option>`,
              )}
            </select>`
          : nothing}
        <span class="status">${this.statusText()}</span>
        <div class="actions">
          <button class="action revert" ?disabled=${!this.dirty || this.saving} @click=${this.onRevert}>${UI.revert}</button>
          <button class="action save" ?disabled=${!canSave} @click=${this.onSave}>${UI.save}</button>
        </div>
      </header>
      ${this.notice
        ? html`<div class="notice ${this.notice.kind}" role=${this.notice.kind === "error" ? "alert" : "status"}>${this.notice.text}</div>`
        : nothing}
      ${this.layout ? this.renderBody(this.layout, errors) : this.renderEmpty()}
    `;
  }

  private renderEmpty() {
    return this.started && this.screens.length === 0 && !this.notice ? html`<div class="empty">${UI.noScreens}</div>` : nothing;
  }

  private renderBody(layout: Layout, errors: LayoutError[]) {
    const refs = new Set(errors.map((e) => e.ref).filter((r): r is string => r !== null));
    return html`<main class=${this.narrow ? "narrow" : ""}>
      <div>
        <hc-grid
          aria-label=${UI.mapLabel}
          .layout=${layout}
          .selectedId=${this.selectedId}
          .errorRefs=${refs}
          @hc-select-block=${(e: CustomEvent<{id: string}>) => (this.selectedId = e.detail.id)}
          @hc-add-block=${this.onAddBlock}
        ></hc-grid>
        ${errors.length > 0
          ? html`<ul class="errors">${errors.map((e) => html`<li>${this.errorText(e)}</li>`)}</ul>`
          : nothing}
        <section>
          <h2>${UI.screenSection}</h2>
          <label for="sleep">${UI.sleepAfter}</label>
          <input
            id="sleep"
            type="number"
            name="sleep_timeout"
            min="0"
            max="3600"
            step="1"
            .value=${String(layout.settings.sleep_timeout)}
            @input=${this.onSleep}
          />
          <div class="help">${UI.sleepHelp}</div>
        </section>
      </div>
      <hc-block-editor
        .hass=${this.hass}
        .layout=${layout}
        .blockId=${this.selectedId ?? ""}
        @hc-layout-change=${(e: CustomEvent<{layout: Layout}>) => this.setLayout(e.detail.layout)}
      ></hc-block-editor>
    </main>`;
  }
}

defineElement("ha-controller-panel", HaControllerPanel);

declare global {
  interface HTMLElementTagNameMap {
    "ha-controller-panel": HaControllerPanel;
  }
}
