```
  _________      .__  .__  __                                 .__
 /   _____/ _____|  | |__|/  |_  ____     _____ _____    ____ |__|____
 \_____  \ / ____/  | |  \   __\/ __ \   /     \\__  \  /    \|  \__  \
 /        < <_|  |  |_|  ||  | \  ___/  |  Y Y  \/ __ \|   |  \  |/ __ \_
/_______  /\__   |____/__||__|  \___  > |__|_|  (____  /___|  /__(____  /
        \/    |__|                  \/        \/     \/     \/        \/
```

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

| Table          | What it stores                                                                      |
| -------------- | ----------------------------------------------------------------------------------- |
| `players`      | The active session — username, class, equipped gear, level, XP, kills, deaths       |
| `player_stats` | The stat record — HP, hit, wisdom tracked as base + bonus columns separately        |
| `class`        | The schema definition — base stat values for each class                             |
| `inventory`    | The join table — items linked to players with stack amounts                         |
| `weapons`      | The weapon registry — all generated weapons with stats and a `found` flag           |
| `armors`       | The armor registry — all generated armors with stats and a `found` flag             |
| `enemies`      | The enemy log — spawned enemies with HP, hit, and XP drop                           |
| `map`          | The world index — 500 procedurally generated encounter nodes across 10 level ranges |
| `events`       | The event flags — global boolean toggles that alter world behavior                  |

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

| ID  | Node type          | Description                                                     |
| --- | ------------------ | --------------------------------------------------------------- |
| `0` | `TRANSACTION`      | A merchant — swap gold for gear, commit or rollback             |
| `1` | `QUERY`            | Standard combat — execute or be executed                        |
| `2` | `STORED_PROCEDURE` | Dungeon — a scripted multi-step sequence with guaranteed output |
| `3` | `DEADLOCK`         | Cave — two forces collide, only one proceeds                    |
| `4` | `CONSTRAINT`       | Forest — the world pushes back, events fire here                |
| `5` | `OVERFLOW`         | Boss — a value so large it breaks the expected range            |

### World events (fire in CONSTRAINT nodes)

| Event              | Effect                                              |
| ------------------ | --------------------------------------------------- |
| **Blood Moon**     | All enemies `UPDATE base_hit * 2`                   |
| **Solar Eclipse**  | Indexer bonuses doubled for the session             |
| **Flood of Omnya** | Certain map nodes set to `WHERE accessible = 0`     |
| **Monster Rush**   | Each fight spawns extra rows in the `enemies` table |
| **Fateful Day**    | Rare loot `found` flag chance tripled               |

---

## Running

```bash
python main.py
```

Requirements: Python 3.10+, no external dependencies.

---

## TODO

### `QUERY` — Combat encounters

- [ ] Wire up the combat loop
- [ ] Player attack action in the fight menu
- [ ] Flee mechanic — abort the query, take a penalty
- [ ] Death handling — `UPDATE players SET deaths = deaths + 1`, respawn or game over
- [ ] XP gain on kill — `UPDATE player_stats` then check level threshold
- [ ] Combat log printed with typewriter effect

### `TRANSACTION` — Shops

- [ ] Shop encounter using encounter_type `0` nodes from `map`
- [ ] Buy items — `SELECT` stock, `UPDATE gold`, `INSERT` into `inventory`
- [ ] Sell items — `DELETE` from `inventory`, `UPDATE gold`
- [ ] Stock pool scales with node `level_range`

### `STORED_PROCEDURE` / `DEADLOCK` — Caves & Dungeons

- [ ] Multi-room crawl through encounter_types `2` and `3`
- [ ] Room-by-room navigation with branching paths
- [ ] Traps as `CONSTRAINT` violations — damage if you fail a check
- [ ] Guaranteed loot `INSERT` on final room clear
- [ ] `UPDATE map SET finished = 1` when a node is fully cleared

### `OVERFLOW` — Bosses

- [ ] Boss nodes via encounter_type `5`
- [ ] Boss stats seeded far above normal enemy ranges
- [ ] Unique named loot `INSERT` on kill — not in the regular pool
- [ ] One boss per `level_range`, gated by player level check

### `CONSTRAINT` — Forest events

- [ ] Forest encounters via encounter_type `4`
- [ ] Read `events` table flags at encounter start
- [ ] Apply modifiers for each active event flag
- [ ] Event expiry — flags auto-reset after N completed encounters

### World / Map

- [ ] Travel menu — `SELECT` from `map WHERE level_range = ?` filtered by player level
- [ ] Show node name, type, and whether `finished`
- [ ] Prevent revisiting `finished = 1` nodes (or allow with reduced rewards)

### Quality of Life

- [ ] Player stats screen — full `SELECT` from `player_stats` displayed cleanly
- [ ] XP progress bar toward next level
- [ ] Confirm prompt before `DELETE FROM inventory`
- [ ] Paginate large inventory lists
