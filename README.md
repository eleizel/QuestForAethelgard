# Quest for Aethelgard

*Quest for Aethelgard* is a gothic-fantasy roguelike RPG with a decoupled pure-Python domain core and pluggable frontends, featuring both a retro 16-color [Pyxel](https://github.com/kitao/pyxel) engine and a modern high-resolution [Pygame-CE](https://pyga.me) client. Choose a hero, navigate branching dungeon routes, survive automatic turn-based battles with interactive timing mechanics, collect tiered equipment and synergistic abilities, promote into specialized advanced classes, and vanquish the bosses across all three acts.

The game runs locally as a desktop application across multiple display engines and on the web as a progressive web app (PWA). It features complete English and Spanish localization, keyboard, mouse, and touchscreen controls, custom pixel-art assets, biome music, and procedural sound effects.

---

## Contents

- [Features](#features)
- [Architecture & Design Patterns](#architecture--design-patterns)
- [Requirements](#requirements)
- [Install and Run](#install-and-run)
  - [Frontend Selection (Pyxel vs. Pygame-CE)](#frontend-selection)
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
  - [Architectural Boundary Linter](#architectural-boundary-linter)
- [Assets and Audio](#assets-and-audio)
- [License](#license)

---

## Features

- **Multi-Frontend Support**: Seamlessly switch between the classic 256×256 retro Pyxel engine and the modern 960×540 high-DPI Pygame-CE desktop client.
- **Pure Domain Core**: 100% decoupled Python core with zero GUI dependencies, strictly validated by automated AST boundary checks.
- **Three Starting Classes & Six Advanced Promotions**: Start as Warrior, Rogue, or Mage. At level 10, promote into Paladin, Berserker, Venomancer, Duelist, Archmage, or Warlock, unlocking permanent signature passives and epic abilities.
- **Three Dungeon Acts & Branching Biomes**: Explore multi-floor dungeons with Fate (random biomes) or Pathfinder (player-chosen biomes) routing.
- **Dynamic Branching Map**: Navigate Combat, Elite, Rest, Treasure, Event, Shop, and Act Boss nodes.
- **Speed-Driven Combat Engine with QTEs**: Automatic tick-based combat governed by speed gauges, active skill queues, and interactive timing Quick Time Events during Elite and Boss encounters.
- **192-Item Tiered Equipment System**: Equip 8 slots (Head, Shoulders, Chest, Waist, Hands, Legs, Main Hand, Off Hand) across 5 rarity tiers with on-hit and on-damaged triggers.
- **Interactive Events & Class Armories**: Biome-exclusive narrative events, including Act 1 & 2 weapon racks and mystic caches offering choices between 3 class-specific next-tier gear pieces.
- **Full Save & Resume**: Cross-platform persistence supporting atomic JSON saves on desktop and LocalStorage on the web, backed by the Memento and Repository patterns.
- **Rich Retro Presentation**: 16-color Pyxel gothic pixel art, full soundtrack, sound effects, BDF bitmap font, and EN/ES localization.

---

## Architecture & Design Patterns

The codebase adheres strictly to clean architecture and modern software design patterns:

| Pattern | Architectural Component | Purpose & Implementation |
| :--- | :--- | :--- |
| **Facade Pattern** | `GameSession` (`src.core.session`) | Cohesive entry point for frontends and simulations. Exposes state queries and high-level commands without leaking entity internals. |
| **State Pattern** | `GameStateMachine` & `ModeState` (`src.core.fsm`) | Manages operational game modes (`WELCOME`, `MAP`, `COMBAT`, `SHOP`, etc.) with validated, deterministic state transitions. |
| **Command Pattern** | `Command` & `CommandDispatcher` (`src.core.commands`) | Encapsulates user actions (`BuyItemCommand`, `TakeLootCommand`, `ChooseAbilityCommand`, `PromoteClassCommand`). |
| **Observer Pattern** | `EventBus` & `DomainEvent` (`src.core.events`) | Decouples audio, combat popups, and analytics into reactive event streams (`AudioCueEvent`, `DamageDealtEvent`, `HealthRestoredEvent`). |
| **Domain Services** | `ShopService`, `LootService`, `DraftService`, `ProgressionService` | Business logic isolated from presentation views into dedicated, pure domain services. |
| **Memento / Repository** | `RunMemento` & `RunRepository` (`src.core.persistence`) | Serializable snapshots decouple persistence from live models, supporting File, Memory, and LocalStorage backends. |
| **Semantic Tokens** | `ThemeToken` (`src.core.theme`) | Abstract color mapping resolving to 0–15 palette indices in Pyxel and 24-bit RGB tuples in Pygame-CE. |

---

## Requirements

- Python 3.10 or newer
- pip

Main runtime dependencies:
- [Pyxel](https://github.com/kitao/pyxel) 2.0+ (Retro engine and PWA web deployment)
- [pygame-ce](https://pyga.me) 2.5+ (Modern high-DPI desktop client)
- `pytest` (Test suites, architectural boundary linter, and balance telemetry)

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

#### Frontend Selection

```bash
# Launch with default retro 256x256 Pyxel engine
python main.py

# Launch explicitly with Pyxel
python main.py --frontend pyxel

# Launch with modern 960x540 Pygame-CE desktop client
python main.py --frontend pygame

# Launch headless simulation mode (CI / bot trials)
python main.py --headless
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

- **Warrior**:
  - **Paladin**: Holy bastion specializing in shields, healing, and damage mitigation (*Holy Aegis*).
  - **Berserker**: Low-health juggernaut trading defense for massive attack speed and damage (*Deathless Onslaught*).
- **Rogue**:
  - **Venomancer**: Master of stacking toxic damage-over-time debuffs (*Venom Mastery*).
  - **Duelist**: Evasive critical striker triggering free counter-attacks (*Riposte Mastery*).
- **Mage**:
  - **Archmage**: Pure arcane elementalist wielding spell echoes and cooldown acceleration (*Arcane Overload*).
  - **Warlock**: Dark summoner sacrificing health for life-leeching soulfire and bone armor (*Soul Siphon*).

---

### Explore the Dungeon Map

- The dungeon map is a branching spire reverse-tree.
- Choose your path floor-by-floor:
  - **Combat / Elite**: Battle enemies to earn gold, experience, and gear.
  - **Rest Site**: Rest to recover HP.
  - **Merchant / Shop**: Purchase potions, rare weapons, and armor.
  - **Treasure**: Collect free gold and equipment.
  - **Event**: Encounter narrative events with risk-reward choices.
  - **Act Boss**: Vanquish the act guardian to advance to the next act.

---

### Combat System & QTE Mechanics

- Battles are speed-gauge driven: faster fighters take actions more frequently.
- **Action Buttons & Belt Hotkeys**: Use `[1]`, `[2]`, `[3]` to quickly consume belt potions.
- **Combat Speed Toggle**: Press `[Z]` to cycle combat speed (1x, 2x, 4x).
- **Elite/Boss QTEs**: When an elite or boss triggers a signature ability, interact with the timed Quick Time Event to parry or evade incoming lethal damage.

---

### Save and Load System

- Runs are saved automatically upon entering dungeon nodes and completing battles.
- On desktop, progress is saved atomically to `saves/quest_for_aethelgard_save.json`.
- In the browser, saves are stored in `window.localStorage`.
- Resume anytime from the Title Screen by selecting **Continue Run** (`[C]`).

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
│   ├── core/                    # Pure Python domain core (Zero GUI dependencies)
│   │   ├── commands.py          # Command pattern definitions & dispatcher
│   │   ├── events.py            # EventBus & reactive domain events
│   │   ├── fsm.py               # State machine & ModeState protocols
│   │   ├── game_state.py        # Core GameState & mode transitions
│   │   ├── persistence.py       # RunMemento & RunRepository
│   │   ├── save_manager.py      # Cross-platform storage backends
│   │   ├── session.py           # GameSession facade
│   │   └── theme.py             # Semantic ThemeToken color abstraction
│   ├── data/                    # Class archetypes, tiered equipment, biomes, events
│   ├── entities/                # Actor, Player, Enemy, Item, Stats data models
│   ├── frontends/               # Pluggable modern presentation layers
│   │   └── pygame_ce/           # High-DPI 960x540 desktop client
│   │       ├── app.py           # PygameApp master lifecycle
│   │       ├── renderer.py      # Themed anti-aliased surface renderer
│   │       ├── audio_adapter.py # Procedural audio cue synthesizer
│   │       └── views/           # Title, Map, and Combat high-DPI screens
│   ├── systems/                 # Combat, QTE, map generator, domain services
│   │   ├── shop_service.py      # Isolated merchant transaction logic
│   │   ├── loot_service.py      # Isolated loot distribution logic
│   │   ├── draft_service.py     # Isolated ability draft logic
│   │   └── progression_service.py # Isolated class promotion logic
│   ├── tools/                   # Asset generation, HTML patcher, build scripts
│   └── ui/                      # Classic 256x256 Pyxel engine & views
├── tests/
│   ├── core/                    # GameSession, FSM, events, and repository tests
│   ├── entities/                # Actor, Player progression, and equipment tests
│   ├── frontends/               # Pygame-CE client test suite
│   ├── simulations/             # Monte Carlo headless simulation runner & balance telemetry
│   ├── systems/                 # Combat engine, QTE, abilities, and inventory tests
│   └── test_architecture_boundary.py # AST-based GUI decoupling import linter
├── main.py                      # Multi-frontend CLI entry point
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## Development, Testing & Monte Carlo Telemetry

Run the full automated test suite (250 tests):

```powershell
python -m pytest
```

### Architectural Boundary Linter

Enforce that the domain core (`src/core`, `src/entities`, `src/systems`, `src/data`) maintains zero imports from GUI frameworks (`pyxel`, `pygame`, `src.ui`):

```powershell
python -m pytest tests/test_architecture_boundary.py
```

### Monte Carlo Balance Telemetry

To test game balance, class win-rates, and equipment drop rates without running the GUI, execute the headless Monte Carlo simulation harness:

```powershell
python -m pytest tests/simulations/test_monte_carlo_balance.py -s
```

All 6 promoted classes are calibrated to an Act 3 victory rate between **40% and 50%**.

---

## Assets and Audio

- Sprite graphics and audio cues for the retro client are bundled in `assets/game.pyxres`.
- Open in the Pyxel editor using:
  ```powershell
  pyxel edit assets/game.pyxres
  ```
- Pygame-CE generates procedural 8-bit sound waveforms directly in memory for audio cues.

---

## License

All rights reserved. See repository metadata for licensing terms.
