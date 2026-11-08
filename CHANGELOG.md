# Changelog

All notable changes to **Quest for Aethelgard** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-08

### Added
- **Dynamic Music Engine**: Multi-track music player with dynamic intensity transitions, seamless crossfading, audio settings persistence, and Welcome screen audio controls.
- **Dual-Frontend Architecture**: Unified gameplay domain supporting desktop (Pygame-CE) and lightweight retro/web deployment (Pyxel).
- **Session-Scoped Services**: Fully decoupled `GameSession` container with isolated event bus, seedable RNG, and repository-backed persistence.
- **Frontend View Models**: Immutable data transfer snapshots (`CombatViewModel`, `ShopViewModel`, `LootViewModel`, `MapViewModel`, `AbilityDraftViewModel`, `StatusViewModel`) preventing frontend-to-domain coupling.
- **Deterministic Invariant Test Suite**: Rigorous automated checks verifying combat replay reproducibility, spire map topology invariants, inventory equip/unequip stat conservation, and save/load memento round-trips.
- **Robust Persistence & Migration**: Versioned save migration pipeline (`register_save_migration`) and automatic timestamped quarantine for corrupt saves (`preserve_invalid`).
- **Emergency Frame Failure Fallback**: Graceful visual diagnostics screen when unhandled exceptions occur during rendering.
- **Asset Verification Tool**: Automated CLI utility (`tools/verify_assets.py`) checking existence, sizes, and integrity of audio tracks, fonts, and graphical manifests.

### Changed
- **Audio Optimization**: Compressed all soundtrack assets to `.ogg` and `.mp3` formats, reducing music footprint to <24MB with 0 uncompressed WAV files.
- **Strict Domain Isolation**: Clean separation between game engine logic and presentation layers; zero Pygame imports in `src/core/`, `src/entities/`, `src/systems/`, and `src/data/`.
- **Production CI Pipeline**: Multi-platform GitHub Actions workflow executing asset verification, ruff lint checks, full test suites, and headless run verification.
