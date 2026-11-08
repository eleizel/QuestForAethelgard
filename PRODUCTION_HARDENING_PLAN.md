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
| H0 | Complete - audio work isolated, PR #85 merged to master, assets reconciled (<24MB, 0 WAVs remaining), and test baseline verified. |
| H1 | Complete - metadata, bounded dependencies, developer tooling, correctness lint, explicit test commands, asset verification, and CI quality gates (PR #86 merged). |
| H2 | Complete - session-scoped persistence, decoupled event bus, deterministic RNG, logger service, and independent concurrent sessions verified. |
| H3 | Complete - enforced modal stack (`push_modal`, `pop_modal`), strict transition guards preventing terminal re-entry, and modal layering tests passing. |
| H4 | Complete - consolidated persistence protocol, versioned save migration pipeline (`register_save_migration`), forward migration tests, and timestamped corrupt-save quarantine (`preserve_invalid`). |
| H5 | Complete - lazy frontend launcher loading, emergency frame failure fallback diagnostics screen, asset verification suite, and safe unrecoverable exception handling. |
| H6 | Complete - shared frontend contract with immutable ViewModels (`CombatViewModel`, `ShopViewModel`, `LootViewModel`, `MapViewModel`, `AbilityDraftViewModel`, `StatusViewModel`) and `GameSession` snapshot producers. |
| H7 | Complete - deterministic invariant test suite covering combat replay reproducibility, spire map topology invariants, inventory equip/unequip stat conservation, and memento round-trips. |
| H8 | Complete - release operations and attribution (`src/version.py`, v1.0.0 title display, `CHANGELOG.md`, `ATTRIBUTION.md`, bug report template, and comprehensive architecture/release documentation). |
