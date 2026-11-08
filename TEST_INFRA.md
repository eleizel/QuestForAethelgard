# E2E Test Infra: QuestForAethelgard Dynamic Music Engine

## Test Philosophy
- Opaque-box, requirement-driven. Tests verify external observable behavior of the audio engine, mute persistence, view transitions, and asset availability, independent of private implementation details.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Asset Resolution & Formats | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 2 | Music Context Resolution | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Randomized Track Selection | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | Combat Encounter Distinction | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Seamless View Transitions | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 6 | Mute/Unmute Toggle & Silencing | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 7 | Persistent Mute across Restarts | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 8 | Welcome View Mute Button UI | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |

## Test Architecture
- **Test runner**: `pytest` invoked via `.venv\Scripts\python.exe -m pytest tests/`
- **Invocation**: All tests must execute cleanly in headless environments (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`)
- **Pass/Fail Semantics**: 0 exit code, 100% assertions pass, 0 regressions in pre-existing test suites
- **Directory layout**:
  - `tests/e2e/test_music_engine_e2e.py`: End-to-end tests covering Tiers 1–4
  - `tests/frontends/pygame_ce/test_music_engine.py`: Unit and component tests

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Game Loop Session: Welcome -> Class Select -> Map -> Combat (Common) -> Map -> Combat (Boss) -> Game Over -> Welcome | F2, F3, F4, F5 | High |
| 2 | Mute Toggle & App Restart Cycle: Launch game -> Toggle Mute ON -> Play across Views -> Quit -> Restart Game -> Verify Muted -> Toggle Unmute -> Verify Audio Restored | F6, F7, F8 | Medium |
| 3 | Rapid View Navigation & Modal Overlays: Switch rapidly between Welcome, Class Select, Map, open Inventory/Character modals, return to Map | F2, F5 | Medium |
| 4 | Repeated Combat Enqueue: Common Combat -> Victory -> Map -> Elite Combat -> Defeat -> New Game -> Boss Combat | F4, F5 | High |
| 5 | Track Shuffle & Loop Validation: Enter context repeatedly across 100 transitions, verify both tracks selected with non-zero probability and proper distribution | F3 | Medium |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per feature (40 tests minimum across 8 features)
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature covering edge cases, missing files, corrupted configs, dummy audio devices, empty/None states (40 tests minimum)
- **Tier 3 (Cross-Feature Combinations)**: Pairwise coverage of context transitions x mute states x restart events (≥15 tests)
- **Tier 4 (Real-World Application Scenarios)**: ≥5 complete realistic multi-step user session workflows
- **Total Minimum**: ≥100 comprehensive test cases verifying dynamic music engine, mute persistence, UI interaction, and asset resolution.
