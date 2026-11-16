import {render, type TemplateResult} from "lit";

/** Render a Lit template into document.body and wait for the first element to settle. */
export async function mount<T extends HTMLElement = HTMLElement>(template: TemplateResult): Promise<T> {
  const host = document.createElement("div");
  document.body.append(host);
  render(template, host);
  const el = host.firstElementChild as T & {updateComplete?: Promise<unknown>};
  await el.updateComplete;
  return el;
}

export function all<E extends Element = HTMLElement>(el: Element, selector: string): E[] {
  return [...(el.shadowRoot as ShadowRoot).querySelectorAll<E>(selector)];
}

export function one<E extends Element = HTMLElement>(el: Element, selector: string): E | null {
  return (el.shadowRoot as ShadowRoot).querySelector<E>(selector);
}

export function nextEvent<D = unknown>(el: EventTarget, name: string): Promise<CustomEvent<D>> {
  return new Promise((resolve) => el.addEventListener(name, (e) => resolve(e as CustomEvent<D>), {once: true}));
}
