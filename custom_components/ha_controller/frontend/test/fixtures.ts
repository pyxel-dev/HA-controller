import type {Layout, LayoutError} from "../src/types";

function byName<T>(modules: Record<string, T>): Record<string, T> {
  return Object.fromEntries(
    Object.entries(modules).map(([path, value]) => [path.split("/").pop()!.replace(/\.json$/, ""), value]),
  );
}

export const validLayouts = byName(
  import.meta.glob<Layout>("../../../../docs/protocol/fixtures/layouts/valid/*.json", {eager: true, import: "default"}),
);

export const invalidLayouts = byName(
  import.meta.glob<{expect: LayoutError; layout: unknown}>(
    "../../../../docs/protocol/fixtures/layouts/invalid/*.json", {eager: true, import: "default"}),
);

export const colors = Object.values(
  import.meta.glob<{bg: string; text: string}[]>("../../../../docs/protocol/fixtures/colors.json", {eager: true, import: "default"}),
)[0];
