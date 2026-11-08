# Production Hardening Plan

This document is the implementation roadmap for taking Quest for Aethelgard
from a polished project to a production-clean release. Each phase has a clear
completion criterion; later phases must not silently weaken an earlier one.

## Operating rules

- Keep gameplay behavior stable unless a change is explicitly documented.
- Preserve deterministic reproduction: record and inject a run seed for all
  game-affecting randomness.
- Prefer explicit dependencies over module-level singletons.
- Ship only from CI after tests and artifact verification pass.
- Treat saves and player data as backward-compatible public contracts.

## Roadmap

### H0 — Stabilize the baseline

1. Reconcile the in-progress music asset set before release: the committed
   formats, filenames, licenses, and manifest must agree.
2. Separate audio code, audio binaries, tests, and documentation into focused
   commits.
3. Record a clean baseline for the full test suite, headless launch, desktop
   package, and web package.

**Done when:** the working tree is intentional, every release asset is tracked
or explicitly ignored, and the baseline is reproducible from a fresh clone.

### H1 — Reproducible tooling and CI gates

1. Maintain project metadata and developer tooling in `pyproject.toml`.
2. Keep runtime and developer dependencies distinct.
3. Run compilation and the complete headless test suite on pull requests and
   before any deploy build.
4. Add linting, formatting, type checking, coverage, and dependency audits as
   passing baselines are established; do not add a red gate without first
   resolving its baseline findings.

**Done when:** a documented clean checkout can create an environment, test,
and build with supported Python versions, and deployment cannot bypass tests.

### H2 — Explicit application services

1. Introduce a `GameServices` composition object containing an event bus, save
   manager, random-number generator, and logger.
2. Make `GameSession` own these services and pass them to gameplay systems.
3. Remove direct core imports of global `event_bus` and `save_manager`.
4. Persist the run seed in save metadata and make it available in diagnostics.

**Done when:** two sessions can run with independent storage, events, and RNG
without cross-talk, including in the same process.

### H3 — Enforced game-flow state machine

1. Define the permitted mode-transition table and test every edge.
2. Remove normal-path forced transitions.
3. Route gameplay actions through typed session commands rather than views
   mutating state directly.
4. Replace implicit `previous_mode` overlay behavior with a modal stack that
   retains its return context.

**Done when:** invalid transitions are rejected without state mutation and
every valid transition has a tested command path.

### H4 — One persistence contract

1. Consolidate storage protocols, save keys, and schema versions in one module.
2. Add versioned save migrations and input validation before restoration.
3. Preserve corrupt saves as recoverable backups and present a controlled UI
   recovery path.
4. Keep run saves, audio settings, and future application settings in separate
   storage namespaces.

**Done when:** old supported saves migrate correctly, malformed saves never
crash startup, and atomic writes cannot discard a valid previous save.

### H5 — Runtime resilience and assets

1. Replace broad exception swallowing with targeted handling and structured
   local diagnostics.
2. Route unrecoverable frame errors to a safe error/title screen rather than
   continuing an exception loop.
3. Lazy-load the selected frontend so Pyxel does not require Pygame imports.
4. Add an asset verification command for fonts, images, music, manifests, and
   referenced game data.

**Done when:** corrupted saves, unavailable audio, missing optional assets, and
unexpected frontend exceptions fail safely and are diagnosable.

### H6 — Shared frontend contract

1. Define view models for combat, rewards, inventory comparisons, shop data,
   ability drafts, and map nodes.
2. Move shared gameplay calculations out of Pygame/Pyxel views.
3. Require frontends to render snapshots and dispatch commands only.

**Done when:** a gameplay-rule change is implemented once outside the two UI
trees and verified against both frontends.

### H7 — Test quality and release verification

1. Add deterministic property/invariant tests for maps, inventory, combat,
   generation, and save/load round trips.
2. Use fixed seeds for CI balance checks; reserve expensive statistical runs
   for scheduled/manual jobs.
3. Build and smoke-test desktop and web artifacts after quality gates pass.
4. Add browser checks for both deployed web frontends.

**Done when:** tests are deterministic, failure reports include a seed, and
packaged artifacts are validated rather than merely generated.

### H8 — Documentation and release operations

1. Keep README commands, supported versions, test totals, and deployment claims
   accurate.
2. Maintain contributor, architecture, testing, release, security, and asset
   attribution documentation.
3. Add version display, changelog/release notes, and an actionable bug-report
   template.

**Done when:** a new contributor can set up, test, build, and release the game
without reverse-engineering repository conventions.

## Current status

| Phase | Status |
| --- | --- |
| H0 | Complete — audio work isolated and committed cleanly on feature branch `feat/dynamic-music-engine-and-audio-compression`, assets reconciled (<24MB, 0 WAVs remaining), and test baseline verified (1,144 passed, 0 failed). |
| H1 | Implemented locally — metadata, bounded dependencies, developer tooling, correctness lint, explicit test commands, asset verification, and CI quality gates are in place. Remote CI execution remains to be observed after push. Broader lint/style cleanup is tracked separately from the passing correctness baseline. |
| H2 | In progress — session-scoped persistence, event bus, RNG, and persisted run seeds now exist; remaining systems and views still need to stop using compatibility globals. |
| H3 | In progress — ordinary transitions no longer bypass guards, and terminal states reject gameplay re-entry. The full per-mode transition table and command routing remain. |
| H4 | In progress — storage constants/protocol are single-sourced; payload validation/version handling and timestamped corrupt-save backups are implemented. Concrete schema migrations and UI recovery messaging remain. |
| H5 | In progress — frontend imports are lazy at launcher level, frame failures terminate safely, and manifest-referenced assets are verified. |
| H6 | In progress — default Pygame views now route mode changes through `GameSession`; shared view models and Pyxel migration remain. |
| H7 | In progress — deterministic map-generation invariant tests now run in the suite; broader generated-state and artifact smoke coverage remain. |
| H8 | In progress — contributor, architecture, release, and security documentation now exists; versioned release publication and attribution inventory remain. |
