# Testing Quest for Aethelgard

Use the project virtual environment explicitly on Windows. The system `python`
command can resolve to the Microsoft Store alias rather than the project
interpreter.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run the pure gameplay/domain suite while working on systems code:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/core tests/entities tests/systems tests/test_architecture_boundary.py -q
```

Run the architecture boundary check alone:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_architecture_boundary.py -q
```

Run a headless Pygame smoke test:

```powershell
.\.venv\Scripts\python.exe main.py --headless
```

CI runs the compile check and full headless suite before artifact builds. Do not
replace a failing test with an xfail or skip without documenting the production
reason and a removal condition.
