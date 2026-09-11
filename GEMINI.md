# Project Guidelines & Release Rules for AI Camera People Counter

## 🚀 Mandatory Release & GitHub Synchronization Rule
Whenever a new feature is completed, a bug is resolved, or a new version/release is requested:
1. **Recompile Executables:**
   - Always recompile `PeopleCounter.exe` from `PeopleCounter.cs`.
   - Always recompile `PeopleCounter-Setup.exe` with embedded `payload.zip` from `PeopleCounterSetup.cs`.
2. **Git Commit & Push:**
   - Stage all modified and new files (`git add -A`).
   - Create a clear, descriptive commit message and push immediately to `origin/main`.
3. **Tagging & GitHub Release:**
   - Create the semantic version tag (e.g. `git tag -a v1.X.X -m "Release v1.X.X"`).
   - Push the tag to GitHub (`git push origin v1.X.X`).
   - Create the formal GitHub Release and upload `PeopleCounter-Setup.exe` and `PeopleCounter.exe` as release assets (or run `python build_release.py <version>`).
   - Never leave GitHub un-synced after a version bump.
4. **Always Install Latest Version Locally:**
   - Always install/deploy the latest compiled version directly onto the local machine (`%LOCALAPPDATA%\Programs\PeopleCounter`).
   - Ensure the Desktop shortcut (`People Counter.lnk`) points to the latest executable with `app.ico`.
   - Never leave the user's local machine with an outdated version.
