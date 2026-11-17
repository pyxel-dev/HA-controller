# Configuring HA Controller

The HA Controller panel edits what each screen shows. Changes only reach the screen when you press Save.

## Opening the panel

Open **HA Controller** in the Home Assistant sidebar. The panel is only available to administrators. If you have several screens, pick one in the header.

The status line next to the title tells you whether the screen is online and whether it is up to date:

- `Offline`: the screen is not connected. Saved changes are delivered when it reconnects.
- `Online · firmware <version> · syncing…`: the screen is receiving the latest layout.
- `Online · firmware <version> · in sync`: the screen shows the saved layout.
- `Online · firmware <version> — update available`: the screen firmware differs from the integration version. Update the firmware.

## The block map

The map shows every block of the screen as a tile. Each block is a full-screen page on the device. The block marked **start** is the one shown when the screen wakes up.

- Select a block to edit it on the right (below the map on narrow windows).
- Click a **+** next to a block to add a neighbouring block there. New blocks are named "Block 5", "Block 6" and so on.
- Set another start block with "Set as start block". You cannot delete the start block, nor a block that would leave other blocks unreachable from the start.

## How swiping follows the map

The map is the layout of the pages on the screen. Put a finger on the right edge and slide left to open the block on the right. The same works for every edge: slide right from the left edge to open the block on the left, slide up from the bottom edge to open the block below, and slide down from the top edge to open the block above.

## Block types

- **Light**: controls a light entity (tap to toggle, slide to change brightness).
- **Thermostat**: controls a climate entity.
- **Custom**: a free page of up to 6 items, shown in order. Items are a text, an emoji, an entity state (optionally an attribute), the screen battery or the screen brightness. Use the arrows to reorder items and the remove button to delete one.

## Fonts and backgrounds

Each block has a font size (S, M, L or XL) and a background colour, chosen from the palette or with a custom colour. The text colour is chosen automatically so it stays readable. Custom items can inherit the font size of their block or override it.

## Screen settings

Under the map, **Sleep after (seconds)** sets how long the screen stays on without interaction. The default is 20 seconds. `0` keeps the screen on. Otherwise use a value between 5 and 3600.

## Saving

Save and Revert are enabled once you change something. Save is disabled while the layout has errors, which are listed under the map. Revert discards your changes. After saving, the panel tells you whether the new layout was sent to the screen or will be delivered when it reconnects. The panel never overwrites your unsaved changes when the status refreshes.

## Limits

- 32 blocks per screen
- 6 items per custom block
- 32 characters per block name
- 64 characters per text
- 64 supported emoji; only emoji from that set can be used
- 24 KB (24,576 bytes) for the whole layout once compiled for the screen. A layout above that limit is refused when you save it
