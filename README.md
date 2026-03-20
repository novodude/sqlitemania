# SQLite Mania — A Terminal RPG

A text-based RPG that lives entirely inside a single SQLite database file (`game_data.db`).

The main goal of this project is **learning SQLite** — every piece of game state (schemas, rows, queries, transactions) maps directly to real game mechanics. The world is a database. You are a query.

---

## How it works

| File               | Purpose                                                 |
| ------------------ | ------------------------------------------------------- |
| `main.py`          | The client — game loop, menus, UI                       |
| `database.py`      | The engine — all SQL logic, init, and game functions    |
| `game_data.db`     | The world — the entire game state lives here            |
| `weapon_name.json` | Name parts used to procedurally `INSERT` weapon records |
| `armor_name.json`  | Armor name pool for random `SELECT` on generation       |

### Schema (tables)

| Table           | What it stores                                                                      |
| --------------- | ----------------------------------------------------------------------------------- |
| `players`       | The active session — username, class, equipped gear, level, XP, kills, deaths       |
| `player_stats`  | The stat record — HP, hit, wisdom tracked as base + bonus columns separately        |
| `class`         | The schema definition — base stat values for each class                             |
| `inventory`     | The join table — items linked to players with stack amounts                         |
| `weapons`       | The weapon registry — all generated weapons with stats and a `found` flag           |
| `armors`        | The armor registry — all generated armors with stats and a `found` flag             |
| `potions`       | The potion registry — typed consumables with heal, hit, wisdom, and barrier effects |
| `enemies`       | The enemy log — spawned enemies with HP, hit, and XP drop                           |
| `map`           | The world index — procedurally generated encounter nodes across 10 level ranges     |
| `events`        | The event flags — global boolean toggles that alter world behavior                  |
| `runs`          | The run log — each adventure seeded and tied to a player and level range            |
| `path`          | The branching path — tree of nodes generated per run with parent/depth/branch       |
| `boss_loot`     | The unique drop registry — named items tied to specific OVERFLOW bosses             |
| `visited_shops` | The shop log — tracks which TRANSACTION nodes a player has previously visited       |

### Classes

| Class            | HP  | Hit | Wisdom | Class bonus on matching gear |
| ---------------- | --- | --- | ------ | ---------------------------- |
| **The Executor** | 120 | 15  | 5      | +2x bonus HP                 |
| **The Indexer**  | 70  | 5   | 20     | +2x bonus Wisdom             |
| **The Trigger**  | 90  | 12  | 10     | +2x bonus Hit + 20 flat      |

> **The Executor** — Runs every query with maximum resource usage. Brute-force, unstoppable, no regard for optimization.
>
> **The Indexer** — Knows where everything is before the fight starts. Precomputed, precise, always one step ahead.
>
> **The Trigger** — Fires automatically on every event. Reacts before you can blink. You didn't call it — it just ran.

Equipping gear that matches your class fires the **class bonus**, applied on top of the item's base stats.

### Encounter types

| ID  | Node type          | Description                                                    |
| --- | ------------------ | -------------------------------------------------------------- |
| `0` | `TRANSACTION`      | A merchant — swap gold for gear, commit or rollback            |
| `1` | `QUERY`            | Standard combat — execute or be executed                       |
| `2` | `STORED_PROCEDURE` | Dungeon — a scripted multi-room sequence with guaranteed loot  |
| `3` | `DEADLOCK`         | Cave — two forces move as one, mirror enemy doubles hit damage |
| `4` | `CONSTRAINT`       | Forest — a world event fires before combat begins              |
| `5` | `OVERFLOW`         | Boss — a massive scaled enemy with unique named loot on kill   |

### World events (fire in CONSTRAINT nodes)

| Event              | Effect                                                             |
| ------------------ | ------------------------------------------------------------------ |
| **Blood Moon**     | All enemies `UPDATE base_hit * 2` at spawn                         |
| **Solar Eclipse**  | The Indexer's `bonus_wisdom` is doubled for the run                |
| **Flood of Omnya** | CONSTRAINT nodes are marked inaccessible — you are turned back     |
| **Monster Rush**   | Each enemy fires a second strike (50% base hit) every combat round |
| **Fateful Day**    | Shop stock is weighted toward high-stat gear and expensive potions |

Events are tracked with an `encounters_since_reset` counter. After **10 combat encounters**, all active events expire and the world resets.

---

## Branching Runs

Each adventure is a **seeded branching path** generated as a tree of `path` nodes stored in the database. You can enter a custom seed or let the game generate one.

- Depth 1–3 nodes are drawn from the `map` pool, weighted by encounter type
- Depth 1 always starts with a merchant (`TRANSACTION`) on the first branch
- All paths converge at depth 4 on a guaranteed **OVERFLOW** boss
- After clearing a node, you choose between branching paths
- You can backtrack to any previously visited shop at any time

### Dungeon layout (STORED_PROCEDURE / DEADLOCK)

Multi-room crawls with 3 rooms + a final chamber:

| Room type | Chance | Effect                                                    |
| --------- | ------ | --------------------------------------------------------- |
| Combat    | 55%    | Standard fight; DEADLOCK rooms double the enemy's hit     |
| Trap      | 25%    | Wisdom check — high wisdom halves damage (cap 60%)        |
| Rest      | 20%    | Heals 12% of max HP                                       |
| Final     | Fixed  | Guaranteed combat + guaranteed unfound gear drop on clear |

---

## Potions

Potions are bought from shops or dropped by enemies (35% drop chance, weighted toward cheaper types). They are consumed from the inventory during combat.

| Type              | Effect                                   |
| ----------------- | ---------------------------------------- |
| `RESTORE`         | Heals HP immediately                     |
| `SURGE`           | Adds % bonus hit for the combat          |
| `CLARITY`         | Adds % bonus wisdom for the combat       |
| `BARRIER`         | Absorbs incoming damage before HP is hit |
| `RESTORE_SURGE`   | Heal + hit bonus                         |
| `RESTORE_CLARITY` | Heal + wisdom bonus                      |
| `SURGE_CLARITY`   | Hit + wisdom bonus                       |

---

## Bosses and Unique Loot

Each **OVERFLOW** boss drops two unique named items (one weapon, one armor) on first kill. These items are seeded in the `boss_loot` table at startup and marked `claimed = 1` once dropped — they cannot be obtained again.

| Boss         | Loot                                                                 |
| ------------ | -------------------------------------------------------------------- |
| The Warlord  | Warlord's Cleave (weapon), Siege Plate (armor)                       |
| The Tyrant   | Tyrant's Decree (weapon), Nullchain Cowl (armor)                     |
| The Behemoth | Behemoth Crasher (weapon), Plated Colossus Shell (armor)             |
| The Archmage | Staff of Final Queries (weapon), Archmage's Inscription Robe (armor) |
| The Overseer | Overseer's Verdict (weapon), All-Seeing Carapace (armor)             |

---

## Running

### Run from source (recommended for development)

```bash
python main.py
```

Requirements: Python 3.10+, no external dependencies.

---

### Build executable

You can compile the game into a standalone executable using `pyinstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile main.py
```

The built executable will be located in the `dist/` directory.

Run it with:

```bash
./dist/main
```

---

### Notes

- A prebuilt **Linux version** is included in the project files.
- The game uses `game_data.db` as its persistent world file, so keep it in the same directory as the executable.
