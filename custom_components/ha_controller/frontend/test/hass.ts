import type {Hass, HassEntity} from "../src/types";

const entity = (entity_id: string, state: string, friendly_name: string, extra: Record<string, unknown> = {}): HassEntity => ({
  entity_id,
  state,
  attributes: {friendly_name, ...extra},
});

/** Minimal fake `hass` for component tests. */
export function fakeHass(): Hass {
  const states = Object.fromEntries(
    [
      entity("light.kitchen", "on", "Kitchen"),
      entity("light.living_room", "off", "Living room"),
      entity("climate.bedroom", "heat", "Bedroom"),
      entity("sensor.outdoor_temperature", "21.5", "Outdoor temperature", {unit_of_measurement: "°C"}),
    ].map((e) => [e.entity_id, e]),
  );
  return {states, callWS: () => Promise.reject(new Error("not available in tests"))};
}
