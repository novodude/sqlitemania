# Building SQLite Mania Executables

The Linux binary is included in this folder (`SQLiteMania-linux`).  
Windows and macOS binaries must be built on their respective platforms — use one of the methods below.

---

## Option A — GitHub Actions (recommended, builds all 3 automatically)

1. Push your repo to GitHub with this folder's `.github/` directory at the root.
2. Go to **Actions → Build Executables → Run workflow**.
3. When the run completes, download the binaries from the **Releases** page or the **Artifacts** section of the run.

The workflow builds Linux, Windows (.exe), and macOS in parallel and uploads them as a GitHub Release.

---

## Option B — Build locally on each machine

Run this command on whichever platform you want to target.  
Requires Python 3.10+ and `pip install pyinstaller`.

### Windows (run in Command Prompt or PowerShell)
```
pyinstaller --onefile --name SQLiteMania-windows --add-data "weapon_name.json;." --add-data "armor_name.json;." --add-data "game_data.db;." main.py
```

### macOS (run in Terminal)
```
pyinstaller --onefile --name SQLiteMania-macos --add-data "weapon_name.json:." --add-data "armor_name.json:." --add-data "game_data.db:." main.py
```

### Linux (run in Terminal)
```
pyinstaller --onefile --name SQLiteMania-linux --add-data "weapon_name.json:." --add-data "armor_name.json:." --add-data "game_data.db:." main.py
```

The output binary will be in the `dist/` folder after each run.

---

## Notes

- The bundled `game_data.db` is a starting-state database. On first run the executable
  extracts it to the working directory. **Save files live in the same folder as the binary.**
- PyInstaller cannot cross-compile — a Windows `.exe` can only be built on Windows,
  macOS binary only on macOS, etc. GitHub Actions is the easiest way to get all three
  without needing access to every OS.
