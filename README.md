# Quest for Aethelgard

*Quest for Aethelgard* is a retro, gothic-fantasy roguelike RPG built with [Pyxel](https://github.com/kitao/pyxel). Choose a hero, navigate branching dungeon routes, survive automatic turn-based battles, collect equipment and abilities, and defeat the bosses of all three acts.

The game runs locally as a Python application. It has English and Spanish localization, keyboard and mouse controls, pixel-art assets, music, and sound effects.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Install and run](#install-and-run)
- [User manual](#user-manual)
  - [Start a run](#start-a-run)
  - [Explore the map](#explore-the-map)
  - [Fight enemies](#fight-enemies)
  - [Manage equipment and items](#manage-equipment-and-items)
  - [Events, shops, and rewards](#events-shops-and-rewards)
  - [Controls](#controls)
- [Project structure](#project-structure)
- [Development and tests](#development-and-tests)
- [Assets and audio](#assets-and-audio)
- [Known limitations](#known-limitations)
- [License](#license)

## Features

- Three starting classes: Warrior, Rogue, and Mage.
- Three acts, each with a choice of two themed biomes when using Pathfinder routes.
- Randomized, branching dungeon maps with combat, elite, rest, treasure, event, shop, and boss nodes.
- Automatic battles driven by speed-based action gauges, with active and passive abilities.
- Equipment slots, a 10-item pouch, and a 3-slot quick-use belt.
- Experience, levels, gold, combat loot, and class-specific starter gear.
- Pyxel pixel-art graphics, biome music, sound effects, and English/Spanish text.

## Requirements

- Python 3.10 or newer
- pip

The game dependency is [Pyxel](https://github.com/kitao/pyxel) 2.0 or newer. Pytest is included for running the project tests.

## Install and run

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Start the game:

```bash
python main.py
```

## User manual

### Start a run

1. On the title screen, choose **New Game** (press `1`).
2. Select Warrior, Rogue, or Mage with `1`-`3` or the left/right arrow keys.
3. Choose a route style using `B` or `T`:
   - **Fate** picks the biome for each act at random.
   - **Pathfinder** lets you choose between that act's two biomes.
4. Press `Enter` or `Space` to begin. In Pathfinder mode, choose a biome with the left/right arrows and confirm with `1` or `2`.

The three classes begin with different stats, equipment, and abilities. Your hero also starts with a health potion in belt slot 1.

### Explore the map

The map is a branching path. Only highlighted, numbered nodes are currently reachable. Choose one with its number key or click it; your choice determines which connected nodes become available next. You cannot revisit a node.

| Map node | What to expect |
| --- | --- |
| Combat | Fight a regular enemy and earn experience, gold, and possible loot. |
| Elite | A tougher battle with elite rewards. |
| Rest | Recover a random 25-40 HP, up to your maximum. |
| Treasure | Gain 25-40 gold. |
| Event | Choose from the options presented; some choices may have requirements or costs. |
| Shop | Buy from the merchant or sell items from your pouch. |
| Boss | Fight the act's final enemy. Defeating it advances the run. |

Acts 1 and 2 have 12 map floors each; Act 3 has 18. The final floor of each act is a boss. After defeating an act boss, your hero is fully healed and moves on to the next act. Defeating the final boss in Act 3 wins the run. If your HP reaches zero, the run ends.

### Fight enemies

Combat runs automatically in ticks: the hero and enemy build action gauges according to their speed and attack when ready. Each tick advances the simulation, and battles continue without requiring repeated input. Press `Space` to advance a tick immediately, or press `Z` to cycle the automatic combat speed.

You can use a belt item or queue an active ability at any time during battle. An active ability executes on your next available player action if it is ready; abilities have cooldowns. You can have up to two active and two passive abilities equipped. Passive abilities apply automatically. Ability drafts offer two choices: standard abilities at levels 4, 8, 12, and 16, and epic abilities at levels 10 and 20. Watch the combat log for hits, critical strikes, status effects, and battle results.

Winning grants experience and gold and opens the loot screen. Leveling up restores HP and can offer an ability choice. Losing ends the run.

### Manage equipment and items

Open the inventory with `I` while exploring, fighting, viewing rewards, or visiting a shop. Close it with `I` or `Esc`. You can also click inventory items and equipment slots.

- Equipment can occupy Head, Shoulders, Chest, Waist, Hands, Legs, Main Hand, and Off Hand slots. Gear bonuses affect your stats.
- Select an item in the pouch and press `E` to equip it. Selecting an occupied equipment slot and pressing `E` moves that gear to the pouch.
- The pouch holds up to 10 items. Press `D` to discard the selected pouch item.
- Consumables must be assigned to one of the three belt slots before they can be used in battle. Select a consumable in the pouch and press `E` to assign it to the next available belt slot (or replace slot 1 if all are full). In the inventory's Belt pane, select a slot and press `E` to use its item.
- While fighting, press `1`, `2`, or `3` to use the corresponding belt slot. A used consumable is consumed.
- Two-handed weapons occupy the Main Hand and cannot be equipped if there is no pouch space for displaced Off Hand gear.
- The pouch and belt are separate: belt items do not count toward the pouch's 10-item capacity.

Use the arrow keys or `W`/`A`/`S`/`D` to navigate inventory panes. Press `Tab` to cycle between Pouch, Equipment, and Belt. Mouse clicks can select visible slots and buttons.

### Events, shops, and rewards

- **Events:** Press `1`, `2`, or `3` to choose an available option. Unavailable options are disabled. After resolving the event, press `Space` or `Enter` to return to the map.
- **Shops:** Use the Up/Down arrows or `W`/`S` to browse. Press `Tab` to switch between buying and selling. Press `Enter` or `B` to buy or sell the selected item; purchases require enough gold, and items you sell must be in your pouch. Press `Space` or `Esc` to leave.
- **Loot:** Press `1`-`3` to take an item, `Space` to take all available items, or `Enter`/`C` to continue. Items go into the pouch if there is room; anything that does not fit remains on the loot screen.
- **Ability choices:** Press `1` or `2` to choose an ability, or `Esc` to skip. If the relevant ability slots are already full, follow the prompt to select which ability to replace.

### Controls

| Screen or action | Keyboard |
| --- | --- |
| Title: New Game / Credits | `1` / `3` |
| Title: language / music / sound effects | `L` / `M` / `S` |
| Class selection | `1`-`3` or Left/Right; `Enter` or `Space` to start; `Esc` to go back |
| Toggle Fate/Pathfinder | `B` or `T` |
| Biome selection | Left/Right to choose; `1` or `2` to confirm |
| Map | Number shown on an available node (`1`-`4`) |
| Open/close inventory | `I`; `Esc` also closes it |
| Combat: advance one tick | `Space` |
| Combat: cycle automatic speed | `Z` |
| Combat: use belt slots | `1`-`3` |
| Combat: queue active abilities | `4`-`5` |
| Inventory: navigate / switch panes | Arrow keys or `W`/`A`/`S`/`D`; `Tab` |
| Inventory: equip, assign, or use selected item | `E` |
| Inventory: discard selected item | `D` |
| Event choices | `1`-`3`; `Space` or `Enter` to continue |
| Loot | `1`-`3` to take; `Space` to take all; `Enter` or `C` to continue |
| Shop: browse / switch Buy-Sell | Up/Down or `W`/`S`; `Tab` |
| Shop: buy or sell / leave | `Enter` or `B` / `Space` or `Esc` |
| Ability choice | `1`-`2`; `Esc` to skip or cancel replacement |
| End screen | `Enter` or `Space` to return to the title |

Most in-game actions can also be performed by clicking the on-screen controls. The title screen's **Load Game** entry is currently unavailable.

## Project structure

```text
QuestForAethelgard/
├── assets/
│   ├── game.pyxres              # Pyxel sprites, sounds, and music
│   └── spleen-5x8.bdf            # Bitmap font
├── src/
│   ├── config.py                 # Display, audio, and gameplay constants
│   ├── core/                     # Engine lifecycle, game state, audio, localization
│   ├── data/                     # Classes, abilities, biomes, enemies, events, items
│   ├── entities/                 # Actors, player, enemies, and items
│   ├── systems/                  # Combat, inventory, map, loot, status effects
│   ├── tools/                    # Asset-generation utilities
│   └── ui/                       # Renderer and game-screen views
├── tests/                        # Automated tests
├── main.py                       # Application entry point
├── requirements.txt
└── README.md
```

## Development and tests

Install the requirements as described above, then run the test suite from the repository root:

```bash
python -m pytest
```

## Assets and audio

The Pyxel resource file at `assets/game.pyxres` supplies the game's sprites and audio. To open it in the Pyxel editor:

```bash
pyxel edit assets/game.pyxres
```

Music is off by default; sound effects are on. Toggle language, music, and sound effects on the title screen with `L`, `M`, and `S` respectively. Music themes change with the biome and switch to combat or boss tracks during battles.

## Known limitations

- The title-screen **Load Game** option is not implemented; runs cannot currently be saved or resumed.
- The game is launched from source with Python; a packaged desktop release is not documented here.

## License

No license file is currently included in this repository. Until a license is added, all rights remain with the copyright holder.
