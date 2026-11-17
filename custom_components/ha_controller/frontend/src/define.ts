/** Register a custom element once; safe when a module is evaluated twice (HMR, duplicate bundle). */
export function defineElement(name: string, ctor: CustomElementConstructor): void {
  if (customElements.get(name) === undefined) customElements.define(name, ctor);
}
