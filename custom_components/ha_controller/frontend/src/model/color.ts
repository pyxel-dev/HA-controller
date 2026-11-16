const channel = (value: number): number => {
  const c = value / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};

/** WCAG relative luminance of a #RRGGBB colour. */
function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

/** Black text on light backgrounds, white on dark ones (spec section 5.5). */
export function textColorFor(bg: string): "#000000" | "#FFFFFF" {
  return luminance(bg) > 0.3 ? "#000000" : "#FFFFFF";
}
