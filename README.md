# Quest for Aethelgard

*Quest for Aethelgard* is a retro, gothic-fantasy roguelike RPG built with [Pyxel](https://github.com/kitao/pyxel). Choose a hero, navigate branching dungeon routes, survive automatic turn-based battles with interactive timing mechanics, collect tiered equipment and synergistic abilities, promote into specialized advanced classes, and vanquish the bosses across all three acts.

The game runs locally as a Python desktop application and on the web as a progressive web app (PWA). It features complete English and Spanish localization, keyboard, mouse, and touchscreen controls, custom pixel-art assets, biome music, and sound effects.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Install and Run](#install-and-run)
- [User Manual](#user-manual)
  - [Start a Run](#start-a-run)
  - [Class System & Level 10 Promotions](#class-system--level-10-promotions)
  - [Explore the Dungeon Map](#explore-the-dungeon-map)
  - [Combat System & QTE Mechanics](#combat-system--qte-mechanics)
  - [Character Sheet & Detailed Stats](#character-sheet--detailed-stats)
  - [Tiered Equipment & Inventory](#tiered-equipment--inventory)
  - [Events, Shops, and Rewards](#events-shops-and-rewards)
  - [Save and Load System](#save-and-load-system)
  - [Controls Reference](#controls-reference)
- [Project Structure](#project-structure)
- [Development, Testing & Monte Carlo Telemetry](#development-testing--monte-carlo-telemetry)
- [Assets and Audio](#assets-and-audio)
- [License](#license)

---

## Features

- **Three Starting Classes & Six Advanced Promotions**: Start as Warrior, Rogue, or Mage. At level 10, promote into Paladin, Berserker, Venomancer, Duelist, Archmage, or Warlock, unlocking permanent signature passives and epic abilities.
- **Three Dungeon Acts & Branching Biomes**: Explore multi-floor dungeons with Fate (random biomes) or Pathfinder (player-chosen biomes) routing.
- **Dynamic Branching Map**: Navigate Combat, Elite, Rest, Treasure, Event, Shop, and Act Boss nodes.
- **Speed-Driven Combat Engine with QTEs**: Automatic tick-based combat governed by speed gauges, active skill queues, and interactive timing Quick Time Events during Elite and Boss encounters.
- **192-Item Tiered Equipment System**: Equip 8 slots (Head, Shoulders, Chest, Waist, Hands, Legs, Main Hand, Off Hand) across 5 rarity tiers with on-hit and on-damaged triggers.
- **Interactive Events & Class Armories**: Biome-exclusive narrative events, including Act 1 & 2 weapon racks and mystic caches offering choices between 3 class-specific next-tier gear pieces.
- **Full Save & Resume**: Cross-platform persistence supporting local JSON saves on desktop and LocalStorage on the web.
- **Rich Retro Presentation**: 16-color Pyxel gothic pixel art, full soundtrack, sound effects, BDF bitmap font, and EN/ES localization.

---

## Requirements

- Python 3.10 or newer
- pip

Main runtime dependency is [Pyxel](https://github.com/kitao/pyxel) 2.0+. `pytest` is used for test suites and balance simulations.

---

## Install and Run

### 1. Set Up Virtual Environment

From the project root:

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Launch the Game

```bash
python main.py
```

---

## User Manual

### Start a Run

1. On the title screen:
   - Press `1` for **New Game**.
   - Press `2` for **Load Game** (resumes saved run).
   - Press `3` for **Credits**.
2. Select your hero class: **Warrior** (`1`), **Rogue** (`2`), or **Mage** (`3`).
3. Select your route style using `B` or `T`:
   - **Fate**: Randomly picks biomes for each act.
   - **Pathfinder**: Allows you to pick your preferred biome at the start of each act.
4. Press `Enter` or `Space` to begin.

---

### Class System & Level 10 Promotions

Each starting class has unique base attributes, stat scaling, and starter gear. At **Level 10**, players choose between two specialized advanced classes. Promoting restores 50% max HP, unlocks an epic ability draft, permanently boosts attribute growth, and grants a signature passive:

| Base Class | Advanced Class | Signature Ability & Mechanics |
| :--- | :--- | :--- |
| **Warrior** | **Paladin** | **Paladin's Oath**: Holy light heals for 18% of ability impact whenever an ability is cast. Exceptional armor and health growth. |
| **Warrior** | **Berserker** | **Blood Frenzy**: Dynamic 10%–25% lifesteal that scales inversely with current HP. Dropping to or below 46% HP triggers a one-time emergency burst heal for 22% max HP. |
| **Rogue** | **Venomancer** | **Toxic Eruption**: Poison detonations restore health equal to 30% of total poison tick damage, enabling self-sustaining damage-over-time playstyles. |
| **Rogue** | **Duelist** | **Riposte / Flourish**: Counter-attacks and high critical strike affinity. Features defensive parry stances and devastating 65% counter-flourishes. |
| **Mage** | **Archmage** | **Arcane Ward**: Grants an arcane shield equal to 15% maximum HP that refreshes whenever any non-basic spell is cast. |
| **Mage** | **Warlock** | **Soul Harvest**: Burns siphon vitality from foes; the first tick of every Burn effect leeches 30% of damage dealt back to the Warlock. |

#### Signature Reworked Abilities:
- **Shadow Step**: Reworked into an **Evade** system. Grants stacking Evade charges; each charge completely negates the next incoming attack before being consumed.
- **Toxic Blood**: Passively infects unpoisoned attackers on hit with poison and triggers reactive self-healing.
- **Phoenix Rebirth**: Upon death, revives the hero and immediately deploys a protective shield equal to 15% maximum HP.

---

### Explore the Dungeon Map

The dungeon is generated as a branching graph:
- Numbered, illuminated nodes (`1`–`4`) represent valid moves. You cannot revisit cleared nodes.
- **Acts 1 & 2** feature 12 floors; **Act 3** features 18 floors.
- Defeating an Act Boss fully restores HP and advances the run to the next act.

| Node Type | Icon / Indicator | Encounter Details |
| :--- | :--- | :--- |
| **Combat** | Crossed Swords | Standard enemy battle. Grants XP, gold, and chance for item drops. |
| **Elite** | Crowned Skull | High-threat enemy featuring **QTE timing challenges**. Drops elite rewards and high-tier equipment. |
| **Rest** | Campfire | Recover 25–40 HP (capped at max HP). |
| **Treasure** | Chest | Free cache yielding 25–40 gold and occasional oddities. |
| **Event** | Question Mark | Branching narrative encounters, stat checks, and class armories (choose 1 of 3 next-tier equipment pieces). |
| **Shop** | Coin Pouch | Trade gold with the merchant to buy weapons, armor, potions, or sell unwanted pouch gear. |
| **Boss** | Demonic Skull | Act climax with multi-phase mechanics and mandatory QTE defense sequences. |

---

### Combat System & QTE Mechanics

Combat runs in automatic ticks calculated from hero and enemy **Speed**:
- Each tick charges the combatant's action gauge. When full, an action triggers.
- **Active Abilities**: Queue abilities using `4` or `5`. The ability fires on the hero's next ready action.
- **Belt Potions**: Use quick-belt slots instantly with `1`, `2`, or `3`.
- **Combat Speed**: Press `Z` to toggle between 1x, 2x, 4x, and Instant combat playback. Press `Space` to step forward one tick manually.

#### Quick Time Events (QTEs)
During **Elite** and **Boss** encounters, special high-impact moves trigger a circular QTE:
- A shrinking outer ring contracts toward a stationary target bullseye.
- Press `Space` or tap the screen when the rings align inside the sweet spot.
- Achieving a **Hit / Perfect** timing breaks the enemy's stance, negating incoming damage or delivering counter-stagger critical damage.

---

### Character Sheet & Detailed Stats

Press `C` or click the character portrait button on the HUD at any time to open the **Character Sheet**:
- **Attributes**: View current Strength, Agility, Intelligence, Armor, Crit Chance, and Speed.
- **Effective Stats**: Hover/inspect all active gear contributions and passive synergies.
- **Passives & Promotion**: Review active signatures, unlocked class perks, and hero lore.

---

### Tiered Equipment & Inventory

Press `I` or click the bag icon to toggle the inventory:
- **8 Equipment Slots**: Head, Shoulders, Chest, Waist, Hands, Legs, Main Hand, and Off Hand.
- **Pouch**: Stores up to 10 unequipped items. Press `E` to equip or `D` to discard. Promoted classes retain full proficiency with starting class equipment.
- **Belt**: 3 quick-use slots dedicated to combat consumables. Assign items from pouch using `E`.
- **Tiered Rarities**:
  - Tier 1: Common
  - Tier 2: Uncommon
  - Tier 3: Rare
  - Tier 4: Epic
  - Tier 5: Legendary
- High-tier armors and weapons feature dynamic **on-hit** (chance to burn/bleed/poison) and **on-damaged** (thorns, barrier procs) triggers.

---

### Save and Load System

*Quest for Aethelgard* includes an integrated persistence engine:
- **Auto-Saving**: Progress is automatically serialized upon navigating map nodes and completing encounters.
- **Manual Save**: Save directly to disk (`saves/run_save.json`) or browser storage.
- **Resume**: Select **Load Game** (`2`) on the title screen to resume an ongoing run exactly where you left off.

---

### Controls Reference

| Screen / Context | Keyboard | Mouse / Touch |
| :--- | :--- | :--- |
| **Title Screen** | `1` New Game, `2` Load Game, `3` Credits | Click menu buttons |
| **Title Settings** | `L` Language (EN/ES), `M` Music On/Off, `S` SFX On/Off | Click HUD icons |
| **Class Select** | `1`–`3` or Arrow keys; `Enter`/`Space` to confirm | Click class cards |
| **Route Mode** | `B` or `T` to toggle Fate / Pathfinder | Click route badge |
| **Dungeon Map** | `1`–`4` (node numbers) | Click available nodes |
| **Character Sheet** | `C` or `Esc` to toggle | Click HUD portrait |
| **Inventory / Pouch** | `I` or `Esc` to toggle; `Tab` to cycle panes; `E` equip/use; `D` discard | Click slots and tabs |
| **Combat Ticks & Speed** | `Space` step tick; `Z` cycle speed (1x / 2x / 4x / max) | Click speed toggle button |
| **Combat Consumables** | `1`–`3` to use quick-belt slots | Click belt icons |
| **Combat Abilities** | `4`–`5` to queue active abilities | Click ability buttons |
| **Combat QTE** | `Space` when rings align | Tap target ring |
| **Promotion Dialog** | `1`–`2` to select class; `Enter`/`Space` to confirm | Click class banner |
| **Events** | `1`–`3` to select choice; `Space`/`Enter` to continue | Click choice options |
| **Shop** | `Up`/`Down` or `W`/`S` to navigate; `Tab` Buy/Sell; `Enter`/`B` confirm; `Esc` leave | Click trade buttons |
| **Loot Screen** | `1`–`3` take item; `Space` take all; `Enter`/`C` continue | Click loot items / button |

---

## Project Structure

```text
QuestForAethelgard/
├── assets/
│   ├── game.pyxres              # Pyxel spritesheets, SFX, and chip music
│   ├── spleen-5x8.bdf           # Bitmap font
│   ├── manifest.json            # PWA web manifest
│   └── screenshots/             # Gameplay and marketing previews
├── src/
│   ├── config.py                # Gameplay, layout, and visual constants
│   ├── core/                    # Engine loop, GameState, SaveManager, i18n localization
│   ├── data/                    # Class archetypes, tiered equipment catalog, biomes, events
│   ├── entities/                # Actor, Player, Enemy, Item, Stats data models
│   ├── systems/                 # Combat, QTE, inventory, map generator, status effects
│   ├── tools/                   # Asset generation, HTML patcher, build scripts
│   └── ui/                      # ViewManager and individual screen views (Combat, Map, Inventory, etc.)
├── tests/
│   ├── core/                    # GameState, SaveManager, and lifecycle tests
│   ├── entities/                # Actor, Player progression, and equipment tests
│   ├── simulations/             # Monte Carlo headless simulation runner & balance telemetry
│   └── systems/                 # Combat engine, QTE, abilities, and inventory tests
├── main.py                      # Game launcher
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## Development, Testing & Monte Carlo Telemetry

Run the full automated test suite (unit and system tests):

```powershell
python -m pytest
```

### Monte Carlo Balance Telemetry
To test game balance, class win-rates, and equipment drop rates without running the GUI, execute the headless Monte Carlo simulation harness:

```powershell
python -m pytest tests/simulations/test_monte_carlo_balance.py -s
```

The simulation tests all classes across thousands of runs with AI pathfinding and synergistic build drafts, exporting telemetry to `monte_carlo_build_telemetry.json`. All 6 promoted classes are calibrated to an Act 3 victory rate between **40% and 50%**.

---

## Assets and Audio

- Sprite graphics and audio cues are bundled in `assets/game.pyxres`.
- Open in the Pyxel editor using:
  ```powershell
  pyxel edit assets/game.pyxres
  ```
- Music themes dynamically adapt to the active biome and switch into combat/boss tracks during battle.

---

## License

All rights reserved. See repository metadata for licensing terms.
