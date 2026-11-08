# Quest for Aethelgard

*Quest for Aethelgard* is a gothic-fantasy roguelike RPG featuring a pure-Python domain core and a **dual-frontend presentation architecture**:
1. **16-Bit Super Nintendo Golden Age Edition** ([Pygame-CE](https://pyga.me)): A 960×540 widescreen presentation styled after classic SNES JRPGs (*Secret of Evermore*, *Terranigma*, *Chrono Trigger*) with authentic Alagard typography, 9-slice gold ornate frames, scenic biome vistas, detailed hero busts, golden class crests, and procedural waveform audio cues.
2. **8-Bit Retro Classic Edition** ([Pyxel](https://github.com/kitao/pyxel)): A 256×256 retro console experience featuring a 16-color palette, classic chiptunes, and bitmap fonts.

Choose a champion, navigate branching spire dungeons, survive speed-governed ATB battles with interactive Quick Time Events, collect tiered equipment with on-hit and on-damaged triggers, promote into specialized advanced classes at Level 10, and vanquish bosses across all three acts.

The game runs locally as a desktop Python application, as a **standalone native desktop executable (`.exe`)**, and in the browser as a **dual-frontend Progressive Web App (PWA)** hosted on GitHub Pages.

---

## Contents

- [Features](#features)
- [Architecture & Design Patterns](#architecture--design-patterns)
- [Requirements](#requirements)
- [Install and Run](#install-and-run)
  - [Frontend Selection (Pygame-CE vs. Pyxel)](#frontend-selection)
- [Packaging & Distribution](#packaging--distribution)
  - [Standalone Desktop Executable (.exe)](#standalone-desktop-executable-exe)
  - [Dual-Frontend Web Deployment (GitHub Pages / PWA)](#dual-frontend-web-deployment-github-pages--pwa)
- [User Manual](#user-manual)
  - [Start a Run & Route Selection](#start-a-run--route-selection)
  - [Class System & Level 10 Promotions](#class-system--level-10-promotions)
  - [Spire Exploration Map](#spire-exploration-map)
  - [Speed-Driven Combat & Boss QTEs](#speed-driven-combat--boss-qtes)
  - [Tiered Equipment & Paperdoll Inventory](#tiered-equipment--paperdoll-inventory)
  - [Character Sheet & Hero Attributes](#character-sheet--hero-attributes)
  - [Merchant Shop, Events & Battle Rewards](#merchant-shop-events--battle-rewards)
  - [Save and Resume System](#save-and-resume-system)
  - [Controls Reference](#controls-reference)
- [Project Structure](#project-structure)
- [Development, Testing & Monte Carlo Telemetry](#development-testing--monte-carlo-telemetry)
  - [Automated Test Suite](#automated-test-suite)
  - [Architectural Boundary Linter](#architectural-boundary-linter)
  - [Monte Carlo Balance Telemetry](#monte-carlo-balance-telemetry)
- [License](#license)

---

## Features

- **Dual-Frontend Architecture**:
  - **16-Bit SNES Edition** (`pygame-ce`): Full 960×540 widescreen layout across all 14 game screens, featuring 9-slice golden ornate frames, Alagard pixel typography, animated hero sprites, class crests, scenic vista windows, threat intelligence, and procedural audio.
  - **8-Bit Retro Edition** (`pyxel`): Authentic 256×256 chiptune console styling.
- **Pure Domain Core (Clean Architecture)**: 100% decoupled Python domain model with zero GUI framework imports, continuously validated by an AST boundary enforcement test suite.
- **Three Starting Classes & Six Advanced Promotions**: Start as Warrior, Rogue, or Mage. At Level 10, promote into Paladin, Berserker, Venomancer, Duelist, Archmage, or Warlock, unlocking permanent signature passives and epic abilities.
- **Three Dungeon Acts & Biome Routes**: Explore multi-floor dungeons with Fate (random biomes) or Pathfinder (player-chosen expedition routes) mechanics.
- **Dynamic Spire Node Tree**: Navigate Combat, Elite, Rest, Treasure, Event, Merchant Shop, and Act Boss nodes.
- **Speed-Driven Combat Engine with QTEs**: Real-time ATB tick gauges governed by speed attributes, active ability cooldowns, 3-slot quick potion belts, and interactive timed circle Quick Time Events against Elite and Boss adversaries.
- **192-Item Tiered Equipment System**: Equip 7 paperdoll slots (Main Hand, Off Hand, Helmet, Armor, Legs, Ring 1, Ring 2) across 5 rarity tiers with dynamic stat comparison diffs and on-hit/on-damaged procs.
- **Interactive Narrative Events**: Rich story scenarios with stat/gold/item requirement checks, risk-reward decision trees, and consequence resolution.
- **Merchant Shop with Live Feedback**: Merchant inventory offering equipment, potions, and herbs with dynamic stat comparisons and live transaction toasts.
- **Cross-Platform Persistence**: Atomic JSON saves in the desktop user's application-data directory and Web `LocalStorage`, backed by the Memento and Repository design patterns.
- **No Virtual Gamepad Clutter**: Web builds feature clean, unobtrusive canvas layouts with mobile touch controls routed directly to interactive UI components rather than overlay joysticks.

---

## Architecture & Design Patterns

The codebase strictly follows clean architecture principles and software design patterns:

| Pattern | Architectural Component | Purpose & Implementation |
| :--- | :--- | :--- |
| **Facade Pattern** | `GameSession` (`src.core.session`) | Unified domain gateway used by all frontends and simulations. Exposes state queries and commands without leaking entity internals. |
| **State Pattern** | `GameStateMachine` & `ModeState` (`src.core.fsm`) | Manages all operational modes (`WELCOME`, `MAP`, `COMBAT`, `SHOP`, `INVENTORY`, `PROMOTION`, etc.) with strict state validation. |
| **Command Pattern** | `Command` & `CommandDispatcher` (`src.core.commands`) | Encapsulates user intent (`BuyItemCommand`, `TakeLootCommand`, `ChooseAbilityCommand`, `PromoteClassCommand`). |
| **Observer Pattern** | `EventBus` & `DomainEvent` (`src.core.events`) | Reactive event streams decoupling audio cues, floating popups, and battle logs (`AudioCueEvent`, `DamageDealtEvent`, `HealthRestoredEvent`). |
| **Domain Services** | `ShopService`, `LootService`, `DraftService`, `ProgressionService` | Pure business logic completely isolated from frontend views. |
| **Memento / Repository** | `RunMemento` & `RunRepository` (`src.core.persistence`) | Immutable serialization snapshots decoupling persistence from live models, supporting File, Memory, and LocalStorage backends. |
| **Semantic Tokens** | `ThemeToken` (`src.core.theme`) | Abstract design tokens resolving to 0–15 palette indices in Pyxel and 24-bit RGB tuples in Pygame-CE. |

---

## Requirements

- Python 3.12 or 3.13 (the CI-supported versions)
- pip

Main runtime dependencies:
- [pygame-ce](https://pyga.me) 2.5+ (16-Bit SNES Golden Age client)
- [Pyxel](https://github.com/kitao/pyxel) 2.0+ (8-Bit Retro client)
- `pytest` (Test suites, architectural boundary linter, balance telemetry)
- `pyinstaller` (Desktop standalone executable compilation)
- `pygbag` (WebAssembly compilation for Pygame-CE)
- `pillow` (Asset format conversion)

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
# Launch with default 16-Bit SNES Pygame-CE client (960x540)
python main.py

# Launch explicitly with Pygame-CE
python main.py --frontend pygame

# Launch in fullscreen mode
python main.py --frontend pygame --fullscreen

# Launch in maximized window
python main.py --frontend pygame --maximized

# Launch with retro 8-Bit Pyxel engine (256x256)
python main.py --frontend pyxel

# Launch headless simulation mode (for CI / automated trials)
python main.py --headless
```

---

## Packaging & Distribution

### Standalone Desktop Executable (.exe)

Compile Quest for Aethelgard into a standalone single-file binary with all fonts, backgrounds, sprites, and audio cues embedded:

```powershell
python tools/build_desktop.py
```

The resulting executable is generated at `dist/desktop/QuestForAethelgard.exe` (~46 MB) and can be distributed to players on Windows without requiring Python.

### Dual-Frontend Web Deployment (GitHub Pages / PWA)

Build the complete dual-frontend web distribution:

```powershell
python tools/build_web.py
```

This compiles:
1. **Root (`/`)**: 16-Bit SNES Golden Age Edition (Pygame-CE via `pygbag` WebAssembly).
2. **Subpath (`/pyxel/`)**: 8-Bit Retro Edition (Pyxel via Pyodide WebAssembly).
3. **No Virtual Gamepads**: Both editions are patched to deactivate on-screen touch joysticks and d-pad overlays.
4. **Cross-Edition Links**: Bidirectional switching pills allow players to jump between the 16-bit SNES and 8-bit retro presentations in real time.

Both editions are automatically built and deployed via the GitHub Actions CI/CD workflow in [`.github/workflows/deploy.yml`](file:///c:/Users/Sergio/PycharmProjects/QuestForAethelgard/.github/workflows/deploy.yml).

---

## User Manual

### Start a Run & Route Selection

1. **Title Screen**: Select **New Game** (`[1]`), **Load Game** (`[2]`), or **Credits** (`[4]`). Toggle language using `[3]` or `[L]`.
2. **Class Selection**: Select your champion:
   - **Warrior** (`[1]`): High Armor & Brutal Cleaves.
   - **Rogue** (`[2]`): Lethal Daggers & Toxic Venoms.
   - **Mage** (`[3]`): Arcane Spells & Barrier Shields.
3. **Route Mode**: Toggle between **Fate** (random biomes) and **Pathfinder** (choose biomes at the start of each act) using `[B]` or `[T]`.

### Class System & Level 10 Promotions

At **Level 10**, your champion qualifies for subclass promotion:

| Base Class | Advanced Class | Role | Signature Passive & Mechanics |
| :--- | :--- | :--- | :--- |
| **Warrior** | **Paladin** | Holy Bastion | **Holy Aegis**: Casting abilities heals for a percentage of impact. Enhanced shield and armor scaling. |
| **Warrior** | **Berserker** | Rage Brawler | **Deathless Onslaught**: Attack speed and damage increase inversely with current health. Emergency healing burst on critical low HP. |
| **Rogue** | **Venomancer** | Toxin Master | **Venom Mastery**: Poison detonations restore health and amplify ongoing tick damage. |
| **Rogue** | **Duelist** | Critical Striker | **Riposte Mastery**: High dodge chance triggering immediate counter-attacks upon evasion. |
| **Mage** | **Archmage** | Burst Elementalist | **Arcane Overload**: Spell echoes trigger chance-based double casts and rapid cooldown reduction. |
| **Mage** | **Warlock** | Dark Siphon | **Soul Siphon**: Dark spells drain enemy vitality to restore hero HP and reinforce barrier shields. |

Promoting immediately launches an **Epic Ability Draft** offering class-exclusive signature spells.

### Spire Exploration Map

- Progress upward floor-by-floor through the Spire node tree:
  - **Combat / Elite**: Battle monsters for EXP, gold, and gear.
  - **Rest**: Recover hero HP.
  - **Shop**: Browse equipment, health potions, and attribute herbs.
  - **Treasure**: Claim gold caches and rare equipment.
  - **Event**: Encounter narrative dilemmas with requirement-based choices.
  - **Boss**: Vanquish the Act Guardian to advance to the next Act.
- **Save & Quit**: Press `[Q]` or `[ESC]` on the Map to save your run and safely return to the title screen.

### Speed-Driven Combat & Boss QTEs

- Battles feature symmetrical ATB gauges where action frequency scales with the Speed attribute.
- **Quick-Belt**: Consume belt potions in combat using keys `[1]`, `[2]`, or `[3]`.
- **Combat Speed**: Press `[Z]` to cycle battle pacing between 1x, 2x, and 4x speed.
- **Quick Time Events (QTE)**: When Elites and Bosses initiate signature strikes, a shrinking ring clash minigame appears. Press `[Space]` or click when the ring aligns inside the golden target zone for **Perfect** parries or damage mitigation.

### Tiered Equipment & Paperdoll Inventory

- Equip gear across 7 slots: Main Hand, Off Hand, Helmet, Armor, Legs, Ring 1, Ring 2.
- Items span 5 rarity tiers: Common, Uncommon, Rare, Epic, and Legendary.
- The item inspection panel provides live **`Diff: +X / -X`** stat deltas compared against your currently equipped gear.
- High-tier equipment features **on-hit** (burn, bleed, poison) and **on-damaged** (thorns, barrier procs) triggers.

### Save and Resume System

- Runs are saved automatically upon navigating spire nodes and concluding battles.
- Save manually at any point on the map via `[Q] SAVE` or `[ESC]`.
- Resume anytime from the Title Screen by selecting **Load Game** (`[2]`).

---

## Project Structure

```text
QuestForAethelgard/
├── assets/                      # Shared visual and audio assets
│   ├── backgrounds/             # 16-Bit SNES vista panoramas & combat arenas
│   ├── fonts/                   # Alagard, DotGothic16, Silkscreen typography
│   ├── icons/                   # Status badges, map nodes, class crests
│   ├── portraits/               # Large hero busts & class artwork
│   ├── sprites/                 # SNES combatants & basic/elite/boss enemies
│   ├── ui/                      # 9-slice gold ornate frames & title logos
│   ├── game.pyxres              # Pyxel 8-bit soundbank & spritesheet
│   └── manifest.json            # PWA web manifest
├── src/
│   ├── config.py                # Visual constants and display parameters
│   ├── core/                    # Pure Python domain core (Zero GUI dependencies)
│   │   ├── commands.py          # Command pattern definitions & dispatcher
│   │   ├── events.py            # Reactive EventBus & domain events
│   │   ├── fsm.py               # State machine & ModeState protocols
│   │   ├── game_state.py        # Core GameState & mode transitions
│   │   ├── persistence.py       # RunMemento & RunRepository
│   │   ├── save_manager.py      # Cross-platform storage backends
│   │   ├── session.py           # GameSession facade
│   │   └── theme.py             # Semantic ThemeToken color abstraction
│   ├── data/                    # Class catalog, 192 tiered items, biomes, enemies, events
│   ├── entities/                # Actor, Player, Enemy, Item, Stats models
│   ├── frontends/               # Pluggable presentation clients
│   │   └── pygame_ce/           # 16-Bit SNES Golden Age JRPG engine (960x540)
│   │       ├── app.py           # PygameApp master lifecycle & async Web loop
│   │       ├── asset_manager.py # 9-slice gold frames, fonts, vistas, busts
│   │       ├── renderer.py      # Anti-aliased font & surface renderer
│   │       ├── audio_adapter.py # Procedural sound waveform synthesizer
│   │       ├── components/      # Reusable TopHUDComponent status header
│   │       └── views/           # Complete 14-screen SNES Golden Age suite
│   ├── systems/                 # Combat, QTE, inventory, map generator, domain services
│   ├── tools/                   # Asset generation, HTML patcher, build scripts
│   └── ui/                      # Classic 8-Bit Pyxel engine (256x256)
├── tests/                       # 263 automated unit, integration, and boundary tests
│   ├── core/                    # GameSession, FSM, events, and persistence tests
│   ├── entities/                # Player progression, enemy scaling, and item tests
│   ├── frontends/               # Pygame-CE client test suite
│   ├── simulations/             # Headless Monte Carlo balance simulation trials
│   ├── systems/                 # Combat engine, QTE, abilities, and inventory tests
│   └── test_architecture_boundary.py # AST import decoupling boundary linter
├── tools/                       # Build automation scripts
│   ├── build_desktop.py         # PyInstaller standalone .exe packager
│   └── build_web.py             # Dual-frontend Pygbag + Pyxel WebAssembly builder
├── main.py                      # Multi-frontend async launcher
├── pyxel_main.py                # Standalone Pyxel web entrypoint
├── pygbag.ini                   # Pygbag packaging configuration
├── requirements.txt             # Project dependencies
└── README.md                    # Project documentation
```

---

## Development, Testing & Monte Carlo Telemetry

### Automated Test Suite

Run the full automated test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Architectural Boundary Linter

Enforce that the domain core (`src/core`, `src/entities`, `src/systems`, `src/data`) maintains zero imports from GUI frameworks (`pyxel`, `pygame`, `src.ui`):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_architecture_boundary.py -q
```

### Monte Carlo Balance Telemetry

Execute headless Monte Carlo simulation trials to measure win rates and balance across thousands of simulated runs:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/simulations/test_monte_carlo_balance.py -s
```

All 6 promoted classes are calibrated to an Act 3 victory rate between **40% and 50%**.

---

## License

All rights reserved. See repository metadata for licensing terms.

## Project Operations

- [Contributing](CONTRIBUTING.md)
- [Architecture](ARCHITECTURE.md)
- [Testing](TESTING.md)
- [Release checklist](RELEASING.md)
- [Security policy](SECURITY.md)
