import type {Hass, Layout, ScreenInfo} from "./types";

export async function listScreens(hass: Hass): Promise<ScreenInfo[]> {
  const result = await hass.callWS<{screens: ScreenInfo[]}>({type: "ha_controller/screens"});
  return result.screens;
}

export async function getLayout(hass: Hass, entryId: string): Promise<Layout> {
  const result = await hass.callWS<{layout: Layout}>({type: "ha_controller/layout/get", entry_id: entryId});
  return result.layout;
}

export function saveLayout(
  hass: Hass,
  entryId: string,
  layout: Layout,
): Promise<{revision: string; pushed: boolean}> {
  return hass.callWS({type: "ha_controller/layout/save", entry_id: entryId, layout});
}
