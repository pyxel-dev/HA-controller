import type {Hass, HassEntity, Layout, ScreenInfo} from "../src/types";
import reference from "../../../../docs/protocol/fixtures/layouts/valid/reference.json";

const entity = (entity_id: string, state: string, friendly_name: string, extra: Record<string, unknown> = {}): HassEntity => ({
  entity_id,
  state,
  attributes: {friendly_name, ...extra},
});

/** A `hass` with a few entities and one screen whose layout lives in memory. */
export function createMockHass(screen: Partial<ScreenInfo> = {}): Hass {
  let layout = structuredClone(reference) as Layout;
  let revision = 1;
  const info = (): ScreenInfo => ({
    entry_id: "mock-entry",
    title: "Kitchen screen",
    device_id: "mock-device",
    online: true,
    firmware_version: "0.1.0",
    integration_version: "0.1.0",
    protocol_ok: true,
    revision: `r${revision}`,
    device_revision: `r${revision}`,
    ...screen,
  });
  const states = Object.fromEntries(
    [
      entity("light.kitchen", "on", "Kitchen"),
      entity("light.living_room", "off", "Living room"),
      entity("climate.bedroom", "heat", "Bedroom"),
      entity("sensor.outdoor_temperature", "21.5", "Outdoor temperature", {unit_of_measurement: "°C"}),
    ].map((e) => [e.entity_id, e]),
  );
  return {
    states,
    async callWS<T>(msg: {type: string; [key: string]: unknown}): Promise<T> {
      switch (msg.type) {
        case "ha_controller/screens":
          return {screens: [info()]} as T;
        case "ha_controller/layout/get":
          return {layout: structuredClone(layout)} as T;
        case "ha_controller/layout/save":
          layout = structuredClone(msg.layout as Layout);
          revision += 1;
          return {revision: `r${revision}`, pushed: true} as T;
        default:
          throw {code: "unknown_command", message: `Unknown command ${msg.type}`};
      }
    },
  };
}
