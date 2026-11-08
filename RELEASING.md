# Release Checklist

1. Work from a clean, reviewed worktree; do not release staged-but-missing or
   untracked runtime assets.
2. Update the project version, changelog, and user-visible version display.
3. Confirm asset licenses and attribution are complete.
4. Run the required checks in `CONTRIBUTING.md`.
5. Build and smoke-test both outputs:

   ```powershell
   .\.venv\Scripts\python.exe tools\build_desktop.py
   .\.venv\Scripts\python.exe tools\build_web.py
   ```

6. Verify the desktop executable on a clean Windows environment, including
   launch, save/load, audio disabled/unavailable behavior, and asset loading.
7. Verify both web frontends from the built web output, including asset paths,
   first interaction, save/load, and browser audio permission behavior.
8. Tag the reviewed commit and publish artifacts only after CI is green.

The current CI creates deploy artifacts after quality gates pass. Automated
versioned release publication remains planned work.
