# SQLite Mania — A Terminal RPG

#### Video Demo: <URL HERE>

#### Description

SQLite Mania is a text-based terminal RPG built entirely around SQLite as its world engine. Every piece of game state — player stats, inventory, enemies, encounters, events, run history — lives in a single `game_data.db` file. The project was built as a practical exploration of SQLite: every mechanic maps directly to a real SQL concept. Combat is a `SELECT` and `UPDATE` loop. The shop is a `JOIN` between `inventory` and `weapons`. World events are boolean flags on a single row. The run history is a tree of `path` nodes stored with parent/depth/branch columns.

The game features three player classes (The Executor, The Indexer, The Trigger), each with different base stats and class bonuses that activate when matching gear is equipped. Runs are seeded branching paths that grow longer as the player levels up — every 5 levels adds an extra depth layer to the tree. Each run ends at an OVERFLOW boss, and clearing all five bosses triggers an ending cinematic. A lives system (3 lives, reset every 3 deaths) and a 5-clear purge mechanic add roguelite pressure on top of the persistent progression.

The codebase is split into two files: `game_engine.py` handles all database logic, schema creation, migrations, and game rules; `main.py` handles all UI, input, and rendering. There is no ORM and no external dependencies beyond Python's standard library — just raw `sqlite3`.

---

## Project Structure

```
sqlitemania/
├── README.md
├── CLI new/                  ← active version
│   ├── main.py               ← game loop, menus, all UI
│   ├── game_engine.py        ← all game logic + database layer (single file)
│   ├── ascii_art.py          ← enemy ASCII art
│   ├── weapon_name.json      ← name parts for procedural weapon generation
│   └── armor_name.json       ← game_engine.py API reference
└── CLI old/                  ← original version (kept for reference)
    ├── main.py
    ├── database.py
    ├── ascii_art.py
    ├── weapon_name.json
    ├── armor_name.json
    └── test_game.py
```

> `game_data.db` is generated at runtime and lives in the same directory as `main.py`.

---

## Architecture

```
game_engine.py  ←  all SQL logic, game rules, DB init
main.py         ←  UI, menus, rendering, input handling
```

`game_engine.py` is the single source of truth for all game state. It handles schema creation, migrations, seed data, and every read/write operation. `main.py` imports it as `db` and never touches SQL directly. There is no separate `database.py` in the new version — it was fully merged into `game_engine.py`.

---

## How to Run

```bash
cd "CLI new"
python main.py
```

**Requirements:** Python 3.10+, no external dependencies.

---

## Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile main.py
./dist/main
```

Keep `game_data.db`, `weapon_name.json`, and `armor_name.json` in the same directory as the executable.

---

## Schema

| Table                  | What it stores                                                                   |
| ---------------------- | -------------------------------------------------------------------------------- |
| `players`              | Username, class, equipped gear, level, XP, kills, deaths, lives, clears, run IDs |
| `player_stats`         | HP, hit, crit tracked as base + bonus columns separately, plus bytes (currency)  |
| `class`                | Base stat values for each class                                                  |
| `inventory`            | Items linked to players with stack amounts                                       |
| `weapons`              | All generated weapons with stats, element, and a `found` flag                    |
| `armors`               | All generated armors with stats, element, and a `found` flag                     |
| `enemies`              | Spawned enemies with HP, hit, and XP drop                                        |
| `map`                  | Procedurally generated encounter nodes across 10 level ranges                    |
| `events`               | Global boolean toggles that alter world behavior + encounter counter             |
| `runs`                 | Each adventure: seed, level range, kills, bytes earned, nodes cleared, outcome   |
| `path`                 | Tree of nodes generated per run with parent/depth/branch                         |
| `boss_loot`            | Named items tied to specific OVERFLOW bosses, claimed once                       |
| `visited_shops`        | Tracks which TRANSACTION nodes a player has previously visited                   |
| `shop_stock`           | Persisted shop inventory per path node so revisits show the same items           |
| `starter_gear_sets`    | Three predefined gear sets unlocked through progression                          |
| `player_unlocked_sets` | Which gear sets each player has earned                                           |
| `status_effects`       | Active combat statuses (DEADLOCK, CORRUPTION, SEGFAULT) with remaining duration  |
| `node_flavour`         | Flavour text lines per encounter type, randomly selected on node entry           |
| `meta`                 | Key/value store for flags like `intro_shown`                                     |

---

## Classes

| Class            | HP  | Hit | Crit | Class bonus on matching gear |
| ---------------- | --- | --- | ---- | ---------------------------- |
| **The Executor** | 120 | 15  | 5    | +2× bonus HP                 |
| **The Indexer**  | 70  | 5   | 20   | +2× bonus Crit               |
| **The Trigger**  | 90  | 12  | 10   | +2× bonus Hit + 20 flat      |

> **The Executor** — Runs every query with maximum resource usage. Brute-force, unstoppable, no regard for optimization.
>
> **The Indexer** — Knows where everything is before the fight starts. Precomputed, precise, always one step ahead.
>
> **The Trigger** — Fires automatically on every event. Reacts before you can blink. You didn't call it — it just ran.

Equipping gear that matches your class fires the **class bonus**, applied on top of the item's base stats.

---

## Encounter Types

| ID   | Node type          | Description                                                   |
| ---- | ------------------ | ------------------------------------------------------------- |
| `-1` | `START`            | Entry point, no encounter                                     |
| `0`  | `TRANSACTION`      | A merchant — buy gear and potions, sell items                 |
| `1`  | `QUERY`            | Standard combat — execute or be executed                      |
| `2`  | `STORED_PROCEDURE` | Dungeon — a scripted multi-room sequence with guaranteed loot |
| `3`  | `DEADLOCK`         | Cave — mirror enemy doubles hit damage                        |
| `4`  | `CONSTRAINT`       | Forest — a world event fires before combat begins             |
| `5`  | `OVERFLOW`         | Boss — a massive scaled enemy with unique named loot on kill  |
| `6`  | `REST`             | Checkpoint — heal, change gear, use potions                   |

---

## Branching Runs

Each adventure is a **seeded branching path** generated as a tree of `path` nodes stored in the database. You can enter a custom seed or let the game generate one.

- Depth 1 always starts with a merchant (`TRANSACTION`) on the first branch
- Middle depths are drawn from the `map` pool, weighted by encounter type
- All paths converge at the final depth on a guaranteed **OVERFLOW** boss
- After clearing a node, you choose between branching paths
- You can backtrack to any previously visited shop at any time

### Run length scaling

Run length grows with player level. Every 5 levels adds one extra middle depth layer:

| Level range | Middle depths | Boss depth |
| ----------- | ------------- | ---------- |
| 1–4         | 2             | 4          |
| 5–9         | 3             | 5          |
| 10–14       | 4             | 6          |
| 15–19       | 5             | 7          |
| 20+         | 6             | 8 (capped) |

---

## Dungeon Layout (STORED_PROCEDURE / DEADLOCK)

Multi-room crawls with 3 rooms + a final chamber:

| Room type | Chance | Effect                                                |
| --------- | ------ | ----------------------------------------------------- |
| Combat    | 55%    | Standard fight; DEADLOCK rooms double the enemy's hit |
| Trap      | 25%    | Crit check — high crit halves damage (cap 60%)        |
| Rest      | 20%    | Heals 12% of max HP                                   |
| Final     | Fixed  | Guaranteed combat + guaranteed gear drop on clear     |

---

## Combat

### Attacking

Damage = `base_hit + bonus_hit - rand(0,5)`, minimum 1. Crit chance = `crit * 0.5%`, capped at 60%, deals 2× damage.

Weapons have an **element** (QUERY / LOCK / OVERFLOW / NULL). Hitting an enemy's weakness deals 1.5× damage, shown as `[EFFECTIVE]`.

| Weapon element | Beats enemy element |
| -------------- | ------------------- |
| QUERY          | LOCK                |
| LOCK           | OVERFLOW            |
| OVERFLOW       | NULL                |
| NULL           | QUERY               |

### Combo system

If you take no damage for 3 consecutive turns, a **QUERY CHAIN** fires — a free bonus strike equal to your total hit stat.

### Status effects

Enemies have a 15% chance per hit to inflict a status:

| Status     | Effect                                          |
| ---------- | ----------------------------------------------- |
| DEADLOCK   | Your next turn is skipped entirely              |
| CORRUPTION | Burns 5% of max HP each turn                    |
| SEGFAULT   | Drains 1–5 points of bonus hit or crit randomly |

Statuses last 2–3 turns and clear on combat end.

---

## Potions

Bought from shops or dropped by enemies (35% drop chance). Consumed from inventory during or outside combat.

| Type              | Effect                                   |
| ----------------- | ---------------------------------------- |
| `RESTORE`         | Heals a % of max HP immediately          |
| `SURGE`           | Flat bonus hit for the session           |
| `CLARITY`         | Flat bonus crit for the session          |
| `BARRIER`         | Absorbs incoming damage before HP is hit |
| `RESTORE_SURGE`   | Heal + hit bonus                         |
| `RESTORE_CLARITY` | Heal + crit bonus                        |
| `SURGE_CLARITY`   | Hit + crit bonus                         |

| Potion          | Heal% | Hit | Crit | Barrier | Price |
| --------------- | ----- | --- | ---- | ------- | ----- |
| Minor Restore   | 15%   | —   | —    | —       | 10    |
| Restore         | 30%   | —   | —    | —       | 20    |
| Major Restore   | 60%   | —   | —    | —       | 40    |
| Minor Surge     | —     | +8  | —    | —       | 15    |
| Surge           | —     | +18 | —    | —       | 30    |
| Major Surge     | —     | +35 | —    | —       | 55    |
| Minor Clarity   | —     | —   | +8   | —       | 15    |
| Clarity         | —     | —   | +18  | —       | 30    |
| Major Clarity   | —     | —   | +35  | —       | 55    |
| Minor Barrier   | —     | —   | —    | 200     | 15    |
| Barrier         | —     | —   | —    | 460     | 30    |
| Major Barrier   | —     | —   | —    | 960     | 55    |
| Mending Surge   | 20%   | +12 | —    | —       | 35    |
| Vital Surge     | 40%   | +25 | —    | —       | 65    |
| Mending Clarity | 20%   | —   | +12  | —       | 35    |
| Vital Clarity   | 40%   | —   | +25  | —       | 65    |
| Mind and Blade  | —     | +15 | +15  | —       | 50    |
| Grand Elixir    | —     | +30 | +30  | —       | 90    |

Each shop stocks potions once — buying a potion removes it from that shop permanently.

---

## World Events

Fire at `CONSTRAINT` nodes. Multiple events can be active simultaneously. All events expire after **10 combat encounters**.

| Event              | Effect                                                             |
| ------------------ | ------------------------------------------------------------------ |
| **Blood Moon**     | All enemies `base_hit × 2` at spawn                                |
| **Solar Eclipse**  | The Indexer's `bonus_crit` is doubled for the run                  |
| **Flood of Omnya** | CONSTRAINT nodes become impassable                                 |
| **Monster Rush**   | Each enemy fires a second strike (50% base hit) every round        |
| **Fateful Day**    | Shop stock is weighted toward high-stat gear and expensive potions |

---

## Bosses and Unique Loot

Each **OVERFLOW** boss drops two unique named items (one weapon, one armor) on first kill. Seeded in `boss_loot` at startup, marked `claimed = 1` once dropped.

| Boss         | Weapon                 | Armor                       |
| ------------ | ---------------------- | --------------------------- |
| The Warlord  | Warlord's Cleave       | Siege Plate                 |
| The Tyrant   | Tyrant's Decree        | Nullchain Cowl              |
| The Behemoth | Behemoth Crasher       | Plated Colossus Shell       |
| The Archmage | Staff of Final Queries | Archmage's Inscription Robe |
| The Overseer | Overseer's Verdict     | All-Seeing Carapace         |

---

## Progression

### Lives system

Each player has **3 lives**. Every death costs one life. When you reach 0 lives (3 deaths), a full stat reset triggers:

- Inventory wiped
- Gear unequipped
- Stats reset to base
- Bytes reset to 50
- Lives restored to 3

The current life count is shown in the camp menu and in stats.

### Clears and the 5-clear purge

Every completed run increments `total_clears`. At every **5th clear**, the system runs a full wipe — the same as a life reset — and plays the purge cinematic before returning to camp.

### Starter gear sets

Three gear sets are unlocked through progression and accessible from the camp menu:

| Clear | Set unlocked     | Weapon                  | Armor                   |
| ----- | ---------------- | ----------------------- | ----------------------- |
| 5     | Iron Protocol    | Standard Executor Blade | Standard Executor Plate |
| 10    | Shadow Index     | Standard Indexer Needle | Standard Indexer Cowl   |
| 15    | Balanced Trigger | Standard Trigger Edge   | Standard Trigger Weave  |

Selecting a gear set equips both pieces immediately. Locked sets show their unlock condition.

### Ending

Clearing all 5 OVERFLOW bosses in a run triggers the ending cinematic. The full cinematic only plays every **5th** full clear of all bosses — other completions show a short message.

---

## Cheat Codes

Type at the camp `>` prompt. Wrong inputs are silently ignored.

| Code                          | Reward                                         |
| ----------------------------- | ---------------------------------------------- |
| `import antigravity`          | 3× Major Restore                               |
| `print('hello world')`        | +500 bytes                                     |
| `pip install everything`      | +50 bytes + pile of minor potions              |
| `undefined is not a function` | 2× Clarity + Grand Elixir                      |
| `npm install`                 | +999 bytes                                     |
| `nan === nan`                 | 3× Major Surge                                 |
| `segfault`                    | Full HP restore                                |
| `malloc`                      | +750 bytes                                     |
| `undefined behavior`          | Full HP + Vital Surge + Major Barrier          |
| `java -jar`                   | +500 XP                                        |
| `nullpointerexception`        | 5× Major Restore                               |
| `drop table`                  | +1000 bytes + full HP + 1000 XP                |
| `select *`                    | +300 bytes + full HP + loot                    |
| `commit`                      | +200 bytes + full HP                           |
| `borrow checker`              | 3× Major Surge + 3× Major Clarity              |
| `rewrite it in rust`          | +1500 bytes                                    |
| `<?php`                       | +999 bytes (hazard pay)                        |
| `if err != nil`               | Full HP + 3× Vital Clarity                     |
| `D-melan`                     | +2000 bytes + full HP + 999 XP + big loot pile |
| `cs50`                        | +500 bytes + 500 XP + week of potions          |

---

## `game_engine.py` API Reference

`game_engine.py` is the single-file backend. `main.py` imports it as `ge` and calls functions from it for all game logic. Frontends never touch SQL directly.

### Constants

| Name                      | Value              | Purpose                                       |
| ------------------------- | ------------------ | --------------------------------------------- |
| `SHOP_STOCK_SIZE`         | `3`                | Slots per shop                                |
| `TRAP_DAMAGE_PERCENT`     | `random 0.10–0.30` | Damage fraction for traps                     |
| `DUNGEON_ROOM_COUNT`      | `3`                | Non-boss rooms before final chamber           |
| `OVERFLOW_BOSSES_TOTAL`   | `5`                | Total bosses to clear for ending              |
| `EVENT_EXPIRY_ENCOUNTERS` | `10`               | Encounters before all events expire           |
| `ENCOUNTER_NAME`          | dict               | Maps encounter type integers to label strings |
| `BRANCH_LABEL`            | list               | Branch directions: `←`, `↑`, `→`              |
| `EVENT_LABELS`            | dict               | Maps event keys to descriptions               |
| `INTRO_LINES`             | list               | Lore lines displayed on first launch          |

---

### Initialisation

#### `initialise_game()`

Runs all DB init. Safe to call on every launch. Calls `init_db`, `init_classes`, `loot_init`, `init_map`, `init_node_flavour`.

#### `init_db()`

Creates all tables and runs `_migrate()` for older databases. Drops old `weapon_limit` trigger.

#### `is_first_launch() -> bool`

Returns `True` if the intro has not been shown yet.

#### `mark_intro_shown()`

Writes `intro_shown` to the `meta` table.

#### `reset_database()`

Deletes `game_data.db` and rebuilds everything from scratch.

---

### Player Management

#### `create_player(username, class_name) -> dict`

Creates a new player. Returns `{'ok': True, 'player_id': int}` or `{'ok': False, 'error': str}`.

#### `load_player(player_id) -> dict`

Checks player exists. Returns same format.

#### `list_players() -> list[dict]`

Returns all players as `[{id, username}]` ordered by ID.

#### `get_player_stats(player_id) -> dict`

Returns a flat dict combining `players` and `player_stats`:

```python
{
  "username", "level", "experience", "xp_needed",
  "deaths", "kills", "equipped_weapon", "equipped_armor",
  "base_hp", "bonus_hp", "max_hp", "current_hp", "bytes",
  "base_hit", "bonus_hit", "base_crit", "bonus_crit",
  "total_hit", "total_crit"
}
```

#### `experience_needed_for_next_level(level) -> int`

Formula: `100 × 1.4^(level-1)`.

#### `level_up(player_id)`

Deducts XP, increments level, raises base stats (+20 HP, +5 hit, +3 crit).

---

### Progression

#### `get_lives(player_id) -> int`

Returns current lives (0–3).

#### `get_total_clears(player_id) -> int`

Returns total completed runs.

#### `increment_clears(player_id) -> int`

Increments `total_clears` by 1. Returns new total.

#### `record_death_and_check_reset(player_id) -> tuple[int, bool]`

Decrements lives, increments `deaths_since_reset`. On 3rd death, calls `_hard_reset_player`.
Returns `(deaths_since_reset, did_reset)`.

#### `clear_user(player_id)`

Full wipe: inventory, gear, stats, bytes. Used by the every-5-clears purge.

#### `unlock_gear_set(player_id, set_id)`

Unlocks a starter gear set for a player. No-op if already unlocked.

#### `get_unlocked_gear_sets(player_id) -> list`

Returns unlocked set rows joined with `starter_gear_sets`.

#### `get_all_gear_sets() -> list`

Returns all three starter gear set definitions.

#### `ensure_starter_gear_in_db(gear_set)`

Inserts weapon/armor rows for a starter set if they don't already exist.

---

### Inventory

#### `get_inventory(player_id) -> list[dict]`

Returns all inventory items:

```python
{"rowid", "item", "amount", "equipped", "kind", "data"}
```

#### `equip_item(player_id, item_name) -> dict`

Equips weapon or armor. Returns `{'ok': True, 'kind', 'replaced'}`.

#### `unequip_item(player_id, item_name) -> dict`

Unequips an item and rebuilds stats.

#### `discard_item(player_id, rowid) -> dict`

Deletes item, unequips if needed, cleans gear table if last copy.

#### `use_potion(player_id, rowid) -> dict`

Applies potion, decrements stack or deletes. Returns effect keys.

#### `remove_gear_item_by_rowid(player_id, rowid, item_name)`

Deletes inventory row and cleans up the weapons/armors table if no player holds the item anymore.

---

### Gear & Pricing

#### `gear_buy_price(item) -> int`

`max(10, bonus_hp + bonus_hit + bonus_crit×2 + hit_mult×3)`

#### `gear_sell_price(item) -> int`

40% of buy price, minimum 1.

#### `get_equipped(player_id) -> tuple[str|None, str|None]`

Returns `(weapon_name, armor_name)`.

#### `get_item_data(item_name) -> dict | None`

Looks up weapons then armors. Returns dict with `"kind"` key, or `None`.

#### `rebuild_stats(player_id)`

Resets bonuses to 0, reapplies weapon + armor bonuses, recalculates max HP.

#### `generate_gear(player_level, gear_type) -> tuple[int, str, str]`

Generates and inserts a scaled weapon or armor. Returns `(rowid, name, type)`.

#### `drop_boss_loot(player_id, boss_type) -> list`

Claims unclaimed boss loot, adds to inventory. Returns list of `(item_name, item_type)`.

---

### Shop

#### `roll_shop_stock(player_id, path_id, run_seed, fateful_day) -> dict`

Returns `{'gear_stock', 'potion_stock', 'weapon_ids'}`. Deterministic by `run_seed XOR path_id`. Persists to `shop_stock` on first roll.

#### `buy_gear(player_id, item) -> dict`

Deducts bytes, adds item, marks found.

#### `buy_potion(player_id, pot) -> dict`

Deducts bytes, adds potion.

#### `sell_item(player_id, rowid) -> dict`

Sells item, unequips if needed, cleans up gear row if last copy. Returns `{'ok', 'item', 'value'}`.

#### `remove_shop_stock_item(path_id, item_name)`

Removes a purchased potion from the shop's persisted stock.

#### `register_shop_visit(player_id, path_id)`

Records a shop visit so the player can return to it.

#### `get_visited_shops(player_id) -> list`

Returns shop nodes visited this run.

---

### Potions

#### `get_potion_pool() -> list`

Returns hardcoded list of all 18 potion definitions as tuples.

#### `apply_potion(player_id, potion_name) -> dict`

Applies heal, hit, crit, or defense. Returns dict of applied effects.

#### `enemy_drop_potion(player_id)`

35% chance to drop a random potion. Adds to inventory.

---

### Enemies

#### `generate_enemy(player_id, is_boss) -> int`

Generates and inserts an enemy scaled to player level. Returns `enemy_id`.

#### `apply_event_combat_modifiers(enemy_id, events)`

Doubles enemy hit if Blood Moon is active.

#### `apply_status(player_id, effect, duration)`

Inserts a status effect row.

#### `get_statuses(player_id) -> list`

Returns active status effects.

#### `tick_statuses(player_id) -> list[str]`

Ticks all statuses, applies DoTs, returns log lines.

#### `record_overflow_kill(player_id) -> int`

Increments overflow kill count. Returns new total.

---

### Combat Actions

#### `spawn_enemy(player_id, is_boss, events) -> dict`

Generates enemy and applies event modifiers. Returns `{'enemy_id', 'type', 'hp', 'max_hp', 'base_hit'}`.

#### `get_enemy_state(enemy_id) -> dict`

Returns live enemy: `{'type', 'hp', 'max_hp'}`.

#### `get_combat_potions(player_id) -> list[dict]`

Filters inventory for usable combat potions.

#### `do_attack(player_id, enemy_id) -> dict`

Executes one attack with crit and element checks.
Returns `{'dmg', 'is_crit', 'element_bonus', 'enemy_hp', 'enemy_dead'}`.

#### `do_enemy_turn(player_id, enemy_id, events, active_defense) -> dict`

Enemy attack phase: barrier, Monster Rush, 15% status chance.
Returns `{'dmg', 'active_defense', 'player_hp', 'player_dead', 'status_inflicted', 'log'}`.

#### `do_flee(player_id, enemy_id) -> dict`

Player flees, takes partial damage, clears statuses. Returns `{'flee_dmg'}`.

#### `do_combo_strike(player_id, enemy_id) -> dict`

Bonus strike after 3 clean turns. Returns `{'dmg', 'enemy_hp', 'enemy_dead'}`.

#### `on_enemy_defeated(player_id, enemy_id, run_id) -> dict`

XP, bytes, potion drop, kill counter, level-up check.
Returns `{'xp', 'bytes', 'drop', 'leveled_up'}`.

#### `on_player_defeated(player_id) -> dict`

Increments death count, restores HP, clears statuses. Returns `{'deaths': 1}`.

#### `on_boss_defeated(player_id, enemy_id) -> dict`

Claims boss loot, increments overflow kills, checks completion.
Returns `{'drops', 'overflow_kills', 'game_complete'}`.

---

### Dungeon

#### `roll_room_type(is_final) -> str`

Returns `'combat'`, `'trap'`, or `'rest'`. Final room always returns `'combat'`.

#### `do_trap(player_id) -> dict`

Deals `max_hp × TRAP_DAMAGE_PERCENT`. Crit check halves damage (0.5%/point, cap 60%). HP ≥ 1.
Returns `{'dmg', 'dodged', 'barely_alive'}`.

#### `do_dungeon_rest(player_id) -> dict`

Heals 12% max HP, minimum 5. Returns `{'healed'}`.

#### `dungeon_final_loot(player_id) -> dict`

Generates and adds one gear piece. Returns `{'item', 'kind'}`.

---

### Rest Node

#### `rest_heal(player_id) -> dict`

Heals 50–100% of missing HP. Returns `{'healed'}`.

---

### Runs & Paths

#### `start_run(player_id, custom_seed) -> dict`

Initialises run with path tree and applies solar eclipse buff.
Returns `{'run_id', 'root_id', 'seed', 'events'}`.

#### `init_run(player_id, custom_seed) -> tuple[int, int, int]`

Lower-level run init. Returns `(run_id, root_id, seed)`.

#### `get_node(path_id) -> dict` / `get_path_node(path_id)`

Returns a single path node.

#### `get_children(path_id) -> list` / `get_path_children(path_id)`

Returns child nodes ordered by branch index.

#### `move_to_node(player_id, path_id)`

Updates player's current path ID.

#### `finish_node(path_id)`

Marks node finished.

#### `finish_run(run_id, outcome)`

Records outcome and timestamp.

#### `finish_run_full(run_id, player_id, outcome) -> dict`

Ends run, removes solar eclipse buff, rebuilds stats, returns run stats.

#### `get_run_stats(run_id) -> dict`

Returns run row: seed, kills, bytes, nodes cleared, outcome.

#### `fetch_runs_stats(player_id) -> list`

Returns all runs for a player ordered by creation time.

#### `record_run_kill / record_run_bytes / record_run_node`

Increment individual run counters.

---

### Events

#### `load_events() -> dict`

Reads all event flags from DB. Returns defaults if missing.

#### `trigger_constraint_event(player_id, events) -> dict`

Fires a random inactive event. Returns `{'fired', 'key', 'name', 'desc', 'events'}`.

#### `tick_event_counter() -> dict`

Increments encounter counter. Resets all events after 10. Returns `{'reset', 'events'}`.

---

### NPC / Archivist

#### `get_archivist_line(player_id, events) -> str`

Returns a single line of Archivist dialogue based on active events or kill/death ratio.

---

### Return value conventions

- Functions that can fail return `{'ok': bool, 'error': str}`.
- Functions that succeed return relevant keys directly.
- Fire-and-forget writes return `None`.
