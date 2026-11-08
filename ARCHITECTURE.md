# Architecture

Quest for Aethelgard separates the game domain from two presentation clients.

```text
Pygame-CE / Pyxel views
          |
      GameSession
          |
   GameState + systems + entities + data
          |
 GameServices: persistence, event bus, RNG
```

## Domain

- `src/core`: sessions, game state, state machine, persistence, events, and
  application-service ports.
- `src/entities`: player, enemy, actor, item, and stat models.
- `src/systems`: combat, map generation, inventory, QTE, progression, loot,
  shop, and draft rules.
- `src/data`: catalog data only.

The AST boundary test prevents domain imports from Pygame, Pyxel, or `src.ui`.
Gameplay randomness is session-scoped, and a run seed is saved with the run for
reproducible investigation.

## Presentation

- `src/frontends/pygame_ce`: default 16-bit client.
- `src/ui`: Pyxel client.

Views should render session state and use `GameSession` commands/transitions
rather than importing persistence or mutating the state machine directly.
The Pygame client has begun this migration; Pyxel migration and shared view
models are tracked in `PRODUCTION_HARDENING_PLAN.md`.

## Persistence

`src/core/persistence.py` owns the storage protocol, save schema version, and
validation. `SaveManager` adapts it to file or browser storage. Invalid desktop
saves are retained as timestamped `.corrupt.json` copies; a caller can inspect
`SaveManager.last_load_error` to present recovery guidance.

## Invariants

- A session owns its event bus, persistence port, RNG, and optional run seed.
- Terminal states cannot transition directly back into gameplay.
- Generated maps have a reachable boss route for tested seeds.
- The game never deploys without compilation, correctness lint, asset
  verification, and headless tests passing in CI.
