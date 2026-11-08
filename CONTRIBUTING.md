# Contributing to Quest for Aethelgard

## Setup

Use Python 3.12 or 3.13 for supported development and CI parity.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Required checks

Run these from the repository root before opening a pull request:

```powershell
.\.venv\Scripts\ruff.exe check src tests tools
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe tools\verify_assets.py
.\.venv\Scripts\python.exe -m pytest -q
```

The CI workflow reruns the correctness lint, compilation, asset verification,
and full headless test suite. Deployment artifacts are not built when that job
fails.

## Change guidelines

- Keep core gameplay free of Pygame, Pyxel, and presentation imports.
- Add deterministic tests for a gameplay change; pass a seed when randomness
  is relevant.
- Treat save data as a versioned public contract. Add a migration before
  changing persisted fields.
- Do not add binary assets without confirming their license and adding them to
  the relevant manifest or asset verification coverage.
- Keep source, assets, tests, and documentation in focused commits where
  practical.

## Reporting bugs

Include the game version/commit, OS, frontend, reproduction steps, error log,
and the displayed run seed when reporting a gameplay issue.
