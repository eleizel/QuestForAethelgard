# Quest for Aethelgard

*Quest for Aethelgard* is a retro-styled tactical roguelike RPG built with the [Pyxel](https://github.com/kitao/pyxel)
retro game engine.

---

## Folder Structure

```
QuestForAethelgard/
├── .venv/
├── assets/
│   └── game.pyxres          # Created via `pyxel edit assets/game.pyxres`
├── src/
│   ├── __init__.py
│   ├── config.py            # Global constants (screen dimensions, FPS, colors)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── game_state.py    # Master state machine (Map, Combat, Inventory, Events)
│   │   └── engine.py        # Pyxel App lifecycle (init, update, draw)
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── actor.py         # Base entity class for stats and HP
│   │   ├── player.py        # Hero class, promotions, inventory references
│   │   └── enemy.py         # Mob generation, stats, tier scaling
│   ├── systems/
│   │   ├── __init__.py
│   │   ├── combat.py        # Deterministic tick-based auto-battle logic
│   │   ├── inventory.py     # 6+2 Equipment, 10-slot Pouch, 3-slot Belt
│   │   └── map_gen.py       # Spire-like reverse-tree node graph generator
│   └── ui/
│       ├── __init__.py
│       ├── renderer.py      # HUD, combat logs, stat panels
│       └── views.py         # View switching (CombatView, MapView, InventoryView)
├── main.py                  # Entry point
├── requirements.txt
└── README.md
```

---

## Architectural Highlights

- **Pyxel Engine & Lifecycle (`src/core/engine.py`)**:
  Manages initialization (`init`), frame tick updates (`update`), and screen drawing (`draw`) targeting a 256x256 retro
  canvas at 30 FPS.
- **Master State Machine (`src/core/game_state.py`)**:
  Orchestrates screen transitions and game modes across `MAP`, `COMBAT`, `INVENTORY`, `EVENTS`, `GAME_OVER`, and
  `VICTORY`.
- **Entities & Class Promotions (`src/entities/`)**:
    - `actor.py`: Base entity with health point management, damage mitigation, and attack calculations.
    - `player.py`: Hero character featuring branching class promotions (Novice -> Warrior/Mage/Rogue ->
      Paladin/Archmage/Assassin), stat points, and progression.
    - `enemy.py`: Tier-scaled adversaries (Common, Uncommon, Elite, Boss) with dynamic attribute scaling per dungeon
      floor.
- **Tactical Systems (`src/systems/`)**:
    - `combat.py`: Deterministic tick-based auto-battle simulation driven by actor speed and action gauges.
    - `inventory.py`: Complete inventory system with 6+2 Equipment (Head, Chest, Hands, Legs, Main Hand, Off Hand +
      Ring, Amulet), a 10-slot Pouch, and a 3-slot quick-use Belt.
    - `map_gen.py`: Reverse-tree node graph generator replicating convergent Slay the Spire style floor progression.
- **UI & Views (`src/ui/`)**:
    - `renderer.py`: HUD overlay, battle logs, gauge bars, and stat panels.
    - `views.py`: Dedicated views for Map navigation, Combat, Inventory, and Room Encounters.

---

## Installation & Setup

1. **Activate Virtual Environment**:
   ```bash
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Asset Editing**:
   Open the built-in Pyxel graphical and audio editor to inspect and edit sprites, tilemaps, sounds, and music:
   ```bash
   pyxel edit assets/game.pyxres
   ```

4. **Run the Game**:
   ```bash
   python main.py
   ```

---

## Default Controls

- **Map Screen**:
    - `[1] - [4]`: Select available node on the next floor
    - `[I]`: Open / close Inventory
- **Combat Screen**:
    - `[SPACE]`: Advance combat tick manually (auto-ticks automatically)
- **Inventory Screen**:
    - `[1] - [3]`: Use quick consumable from Belt slots
    - `[I]` or `[ESC]`: Close Inventory
- **Event Screen**:
    - `[SPACE]` or `[ENTER]`: Return to Map
