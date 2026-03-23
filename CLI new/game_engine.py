# game_engine.py — single-file game logic + database layer
# main.py imports this instead of database.py

import sqlite3 as sql
import json
import os
import random
import time
from enum import Enum

# ------------------------------------------------------------------ #
#  DATABASE CONNECTION                                               #
# ------------------------------------------------------------------ #

DB_PATH = "game_data.db"

conn = sql.connect(DB_PATH)
conn.row_factory = sql.Row
c = conn.cursor()


def reconnect():
    global conn, c
    conn.close()
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    c = conn.cursor()


class BonusType(Enum):
    WEAPON = "weapon"
    ARMOR  = "armor"
    POTION = "potion"
    ENV    = "env"


# ------------------------------------------------------------------ #
#  SCHEMA INIT                                                       #
# ------------------------------------------------------------------ #

def init_db():
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            blood_moon              INTEGER DEFAULT 0,
            solar_eclipse           INTEGER DEFAULT 0,
            flood_omnya             INTEGER DEFAULT 0,
            monster_rush            INTEGER DEFAULT 0,
            fateful_day             INTEGER DEFAULT 0,
            encounters_since_reset  INTEGER DEFAULT 0
        )
    """)
    try:
        c.execute("ALTER TABLE events ADD COLUMN encounters_since_reset INTEGER DEFAULT 0")
    except sql.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS class (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            base_hp    INTEGER NOT NULL,
            base_hit   INTEGER NOT NULL,
            base_crit  INTEGER NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS status_effects (
            player_id  INTEGER NOT NULL,
            effect     TEXT NOT NULL,
            duration   INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            username           TEXT NOT NULL UNIQUE,
            class_id           INTEGER NOT NULL,
            equipped_armor     TEXT,
            equipped_weapon    TEXT,
            level              INTEGER DEFAULT 1,
            experience         INTEGER DEFAULT 0,
            deaths             INTEGER DEFAULT 0,
            kills              INTEGER DEFAULT 0,
            overflow_kills     INTEGER DEFAULT 0,
            total_clears       INTEGER DEFAULT 0,
            lives              INTEGER DEFAULT 3,
            deaths_since_reset INTEGER DEFAULT 0,
            current_run_id     INTEGER REFERENCES runs(id),
            current_path_id    INTEGER REFERENCES path(id),
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES class(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id         INTEGER PRIMARY KEY,
            original_base_hit INTEGER,
            base_hp           INTEGER NOT NULL,
            bonus_hp          INTEGER DEFAULT 0,
            max_hp            INTEGER NOT NULL,
            current_hp        INTEGER NOT NULL,
            bytes             INTEGER DEFAULT 50,
            base_hit          INTEGER NOT NULL,
            bonus_hit         INTEGER DEFAULT 0,
            base_crit         INTEGER NOT NULL,
            bonus_crit        INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            player_id INTEGER,
            item      TEXT NOT NULL,
            amount    INTEGER DEFAULT 1,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS potions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            potion_type  TEXT NOT NULL,
            heal_amount  INTEGER DEFAULT 0,
            bonus_hit    INTEGER DEFAULT 0,
            bonus_crit   INTEGER DEFAULT 0,
            defense_flat INTEGER DEFAULT 0,
            duration     INTEGER DEFAULT 1,
            price        INTEGER DEFAULT 15
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS node_flavour (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            encounter_type INTEGER NOT NULL,
            line           TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS enemies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            type            TEXT NOT NULL,
            base_hp         INTEGER DEFAULT 80,
            max_hp          INTEGER DEFAULT 80,
            base_hit        INTEGER DEFAULT 10,
            weapon          TEXT,
            experience_drop INTEGER,
            is_dead         BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weapons (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            class_type TEXT NOT NULL,
            hit_mult   INTEGER NOT NULL,
            bonus_hp   INTEGER DEFAULT 0,
            bonus_hit  INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            element    TEXT DEFAULT 'QUERY',
            found      BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS armors (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            class_type TEXT NOT NULL,
            bonus_hp   INTEGER DEFAULT 0,
            bonus_hit  INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            element    TEXT DEFAULT 'QUERY',
            found      BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS boss_loot (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            boss_name  TEXT NOT NULL,
            item_name  TEXT NOT NULL,
            item_type  TEXT NOT NULL,
            class_type TEXT NOT NULL,
            hit_mult   INTEGER DEFAULT 20,
            bonus_hp   INTEGER DEFAULT 0,
            bonus_hit  INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            claimed    BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id     INTEGER NOT NULL,
            seed          INTEGER NOT NULL,
            level_range   INTEGER NOT NULL,
            kills         INTEGER DEFAULT 0,
            bytes_earned  INTEGER DEFAULT 0,
            nodes_cleared INTEGER DEFAULT 0,
            outcome       TEXT,
            ended_at      TIMESTAMP,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS path (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id         INTEGER NOT NULL,
            parent_id      INTEGER,
            depth          INTEGER NOT NULL,
            branch         INTEGER NOT NULL,
            name           TEXT NOT NULL,
            description    TEXT,
            encounter_type INTEGER NOT NULL,
            level_range    INTEGER NOT NULL,
            finished       BOOLEAN DEFAULT 0,
            FOREIGN KEY (run_id)    REFERENCES runs(id),
            FOREIGN KEY (parent_id) REFERENCES path(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS visited_shops (
            player_id INTEGER NOT NULL,
            path_id   INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (path_id)   REFERENCES path(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_stock (
            path_id   INTEGER NOT NULL,
            slot      INTEGER NOT NULL,
            item_type TEXT    NOT NULL,
            item_name TEXT    NOT NULL,
            PRIMARY KEY (path_id, slot),
            FOREIGN KEY (path_id) REFERENCES path(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS map (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            description    TEXT,
            encounter_type INTEGER NOT NULL,
            level_range    INTEGER NOT NULL,
            finished       BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS starter_gear_sets (
            id           INTEGER PRIMARY KEY,
            set_name     TEXT NOT NULL,
            weapon_name  TEXT NOT NULL,
            armor_name   TEXT NOT NULL,
            w_class      TEXT NOT NULL,
            w_hit_mult   INTEGER NOT NULL,
            w_bonus_hp   INTEGER NOT NULL,
            w_bonus_hit  INTEGER NOT NULL,
            w_bonus_crit INTEGER NOT NULL,
            a_class      TEXT NOT NULL,
            a_bonus_hp   INTEGER NOT NULL,
            a_bonus_hit  INTEGER NOT NULL,
            a_bonus_crit INTEGER NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_unlocked_sets (
            player_id INTEGER NOT NULL,
            set_id    INTEGER NOT NULL,
            PRIMARY KEY (player_id, set_id),
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (set_id)    REFERENCES starter_gear_sets(id)
        )
    """)

    _migrate()
    c.execute("DROP TRIGGER IF EXISTS weapon_limit")

    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO events DEFAULT VALUES")

    conn.commit()
    _init_boss_loot()
    _init_starter_gear_sets()


def _migrate():
    """Safe ALTER TABLE migrations for players upgrading from older DB versions."""
    migrations = [
        ("players", "overflow_kills",       "INTEGER DEFAULT 0"),
        ("players", "total_clears",         "INTEGER DEFAULT 0"),
        ("players", "lives",                "INTEGER DEFAULT 3"),
        ("players", "deaths_since_reset",   "INTEGER DEFAULT 0"),
        ("players", "current_run_id",       "INTEGER"),
        ("players", "current_path_id",      "INTEGER"),
        ("weapons", "element",              "TEXT DEFAULT 'QUERY'"),
        ("armors",  "element",              "TEXT DEFAULT 'QUERY'"),
    ]
    for table, col, col_def in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sql.OperationalError:
            pass

    for col, col_def in [("kills", "INTEGER DEFAULT 0"), ("bytes_earned", "INTEGER DEFAULT 0"),
                         ("nodes_cleared", "INTEGER DEFAULT 0"), ("outcome", "TEXT"),
                         ("ended_at", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE runs ADD COLUMN {col} {col_def}")
        except sql.OperationalError:
            pass

    conn.commit()


# ------------------------------------------------------------------ #
#  SEED DATA                                                         #
# ------------------------------------------------------------------ #

def _init_boss_loot():
    c.execute("SELECT COUNT(*) FROM boss_loot")
    if c.fetchone()[0] > 0:
        return
    loot = [
        ("The Warlord",  "Warlord's Cleave",            "weapon", "The Executor", 5,    120, 25,  0),
        ("The Warlord",  "Siege Plate",                  "armor",  "The Executor", None, 150, 20,  0),
        ("The Tyrant",   "Tyrant's Decree",              "weapon", "The Indexer",  4,    40,  15,  35),
        ("The Tyrant",   "Nullchain Cowl",               "armor",  "The Trigger",  None, 90,  25,  20),
        ("The Behemoth", "Behemoth Crasher",             "weapon", "The Executor", 5,    160, 30,  0),
        ("The Behemoth", "Plated Colossus Shell",        "armor",  "The Executor", None, 180, 25,  0),
        ("The Archmage", "Staff of Final Queries",       "weapon", "The Indexer",  5,    30,  10,  50),
        ("The Archmage", "Archmage's Inscription Robe",  "armor",  "The Indexer",  None, 60,  10,  45),
        ("The Overseer", "Overseer's Verdict",           "weapon", "The Trigger",  3,    100, 35,  25),
        ("The Overseer", "All-Seeing Carapace",          "armor",  "The Trigger",  None, 120, 30,  30),
    ]
    c.executemany("""
        INSERT INTO boss_loot
            (boss_name, item_name, item_type, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, loot)
    conn.commit()


def _init_starter_gear_sets():
    c.execute("SELECT COUNT(*) FROM starter_gear_sets")
    if c.fetchone()[0] > 0:
        return
    sets = [
        (1, "Iron Protocol",
         "Standard Executor Blade", "Standard Executor Plate",
         "The Executor", 2, 30, 8, 0,
         "The Executor", 40, 5, 0),
        (2, "Shadow Index",
         "Standard Indexer Needle", "Standard Indexer Cowl",
         "The Indexer", 2, 10, 5, 20,
         "The Indexer", 15, 5, 18),
        (3, "Balanced Trigger",
         "Standard Trigger Edge", "Standard Trigger Weave",
         "The Trigger", 2, 20, 12, 8,
         "The Trigger", 25, 10, 8),
    ]
    c.executemany("""
        INSERT INTO starter_gear_sets
            (id, set_name, weapon_name, armor_name,
             w_class, w_hit_mult, w_bonus_hp, w_bonus_hit, w_bonus_crit,
             a_class, a_bonus_hp, a_bonus_hit, a_bonus_crit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sets)
    conn.commit()


def init_classes():
    classes = [
        ("The Executor", 120, 15, 5),
        ("The Indexer",  70,   5, 20),
        ("The Trigger",  90,  12, 10),
    ]
    c.executemany("""
        INSERT OR IGNORE INTO class (name, base_hp, base_hit, base_crit) VALUES (?, ?, ?, ?)
    """, classes)
    conn.commit()


def loot_init():
    c.execute("SELECT COUNT(*) FROM weapons")
    if c.fetchone()[0] == 0:
        for _ in range(20):
            generate_gear(player_level=1, gear_type="weapon")
    c.execute("SELECT COUNT(*) FROM armors")
    if c.fetchone()[0] == 0:
        for _ in range(20):
            generate_gear(player_level=1, gear_type="armor")


def init_map():
    DISTRIBUTION = {0: 5, 1: 30, 2: 5, 3: 5, 4: 3, 5: 2, 6: 4}
    LOW_ADJ      = ["Cached", "Indexed", "Idle", "Dormant", "Deprecated"]
    MID_ADJ      = ["Corrupted", "Fragmented", "Recursive", "Locked", "Overloaded"]
    HIGH_ADJ     = ["Null", "Truncated", "Cascading", "Unhandled", "Catastrophic"]
    CREATURES    = ["Processes", "Daemons", "Threads", "Queries", "Triggers", "Cursors"]
    BOSSES       = ["Warlord", "Overseer", "Tyrant", "Behemoth", "Archmage"]
    PLACES       = ["Schema", "Warehouse", "Cluster", "Replica", "Shard"]
    CAVE_TYPES   = ["Deadlock Chamber", "Rollback Depths", "Isolation Vault", "Constraint Hollow"]
    FOREST_TYPES = ["Cascade Wilds", "Foreign Key Tangle", "Trigger Thicket", "Index Sprawl"]
    REST_TYPES   = ["Checkpoint Node", "Savepoint Alcove", "Commit Cache", "Buffer Clearing"]

    def adj(lr):
        if lr <= 2: return LOW_ADJ
        if lr <= 6: return MID_ADJ
        return HIGH_ADJ

    def gen_name(et, lr):
        a = random.choice(adj(lr))
        if et == 0: return f"{a} Traveling Merchant"
        if et == 1: return f"{a} {random.choice(CREATURES)}"
        if et == 2: return f"{a} {random.choice(PLACES)}"
        if et == 3: return f"{a} {random.choice(CAVE_TYPES)}"
        if et == 4: return f"{a} {random.choice(FOREST_TYPES)}"
        if et == 5: return f"{a} {random.choice(BOSSES)}"
        if et == 6: return f"{a} {random.choice(REST_TYPES)}"

    def gen_desc(et, lr):
        mn, mx = lr * 10 + 1, (lr + 1) * 10
        if et == 0: return f"A TRANSACTION node. A merchant offering gear for adventurers level {mn}-{mx}."
        if et == 1: return f"A QUERY node. Hostile enemies scaled for fighters level {mn}-{mx}."
        if et == 2: return f"A STORED_PROCEDURE node. A dungeon with scripted traps and enemies level {mn}-{mx}."
        if et == 3: return f"A DEADLOCK node. A dark cave where two forces collide around level {mn}-{mx}."
        if et == 4: return f"A CONSTRAINT node. A forest where the world pushes back, level {mn}-{mx}."
        if et == 5: return f"An OVERFLOW node. A boss encounter for heroes level {mn}-{mx}."
        if et == 6: return f"A REST node. A quiet place to recover, level {mn}-{mx}."

    rows = []
    for lr in range(10):
        for et, amount in DISTRIBUTION.items():
            for _ in range(amount):
                rows.append((gen_name(et, lr), gen_desc(et, lr), et, lr, 0))
    c.executemany("""
        INSERT INTO map (name, description, encounter_type, level_range, finished)
        VALUES (?, ?, ?, ?, ?)
    """, rows)
    conn.commit()


def init_node_flavour():
    c.execute("SELECT COUNT(*) FROM node_flavour")
    if c.fetchone()[0] > 0:
        return
    lines = [
        (0, "the merchant's eyes flicker like a cursor awaiting input."),
        (0, "goods change hands. the economy persists."),
        (0, "a traveling vendor. their wares update each visit."),
        (1, "something has detected your process. it does not yield."),
        (1, "hostile threads converge. execution is contested."),
        (1, "a query fires. the answer is violence."),
        (2, "the dungeon runs a fixed routine. each room, scripted."),
        (2, "these walls remember every traveler. none have changed them."),
        (2, "a procedure locked in place long before you arrived."),
        (3, "two forces hold each other in permanent contention."),
        (3, "neither will release. neither can advance. you are the variable."),
        (3, "a stalemate older than the current schema."),
        (4, "the world enforces its rules here. violation is painful."),
        (4, "a foreign key tangle. the paths resist traversal."),
        (4, "something fundamental shifts as you enter."),
        (5, "the air thickens. the logs show something massive."),
        (5, "an OVERFLOW event. the stack cannot contain what lives here."),
        (5, "this is where corrupted processes come to grow beyond bounds."),
        (6, "a savepoint. the system breathes."),
        (6, "rollback is possible here, if only for a moment."),
        (6, "the noise fades. your process stabilizes."),
    ]
    c.executemany("INSERT INTO node_flavour (encounter_type, line) VALUES (?, ?)", lines)
    conn.commit()


def get_node_flavour(encounter_type: int) -> str:
    c.execute("""
        SELECT line FROM node_flavour WHERE encounter_type = ? ORDER BY RANDOM() LIMIT 1
    """, (encounter_type,))
    row = c.fetchone()
    return row["line"] if row else ""


# ------------------------------------------------------------------ #
#  META / LAUNCH                                                     #
# ------------------------------------------------------------------ #

def is_first_launch() -> bool:
    c.execute("SELECT value FROM meta WHERE key = 'intro_shown'")
    return c.fetchone() is None


def mark_intro_shown():
    c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('intro_shown', '1')")
    conn.commit()


def reset_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    reconnect()
    initialise_game()


def initialise_game():
    """Run all DB init. Safe to call on every launch."""
    init_db()
    init_classes()
    loot_init()
    init_map()
    init_node_flavour()


# ------------------------------------------------------------------ #
#  PLAYER                                                            #
# ------------------------------------------------------------------ #

def init_player(username: str, class_name: str) -> int:
    c.execute("SELECT id, base_hp, base_hit, base_crit FROM class WHERE name = ?", (class_name,))
    cls = c.fetchone()
    if not cls:
        raise ValueError(f"Class '{class_name}' does not exist")
    class_id, hp, hit, crit = cls
    c.execute("INSERT INTO players (username, class_id) VALUES (?, ?)", (username, class_id))
    player_id = c.lastrowid
    c.execute("""
        INSERT INTO player_stats
            (player_id, base_hp, max_hp, current_hp, original_base_hit, base_hit, base_crit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (player_id, hp, hp, hp, hit, hit, crit))
    conn.commit()
    return player_id


def list_players() -> list:
    c.execute("SELECT id, username FROM players ORDER BY id")
    return [dict(r) for r in c.fetchall()]


def load_player(player_id: int) -> dict:
    c.execute("SELECT id FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    if not row:
        return {"ok": False, "error": "Player not found."}
    return {"ok": True, "player_id": player_id}


def create_player(username: str, class_name: str) -> dict:
    try:
        pid = init_player(username, class_name)
        return {"ok": True, "player_id": pid}
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return {"ok": False, "error": f"Username '{username}' is already taken."}
        return {"ok": False, "error": str(e)}


def get_player_stats(player_id: int) -> dict:
    c.execute("""
        SELECT username, level, experience, deaths, kills, equipped_weapon, equipped_armor
        FROM players WHERE id = ?
    """, (player_id,))
    p = c.fetchone()
    c.execute("""
        SELECT base_hp, bonus_hp, max_hp, current_hp, bytes,
               base_hit, bonus_hit, base_crit, bonus_crit
        FROM player_stats WHERE player_id = ?
    """, (player_id,))
    s = c.fetchone()
    return {
        "username":        p["username"],
        "level":           p["level"],
        "experience":      p["experience"],
        "xp_needed":       experience_needed_for_next_level(p["level"]),
        "deaths":          p["deaths"],
        "kills":           p["kills"],
        "equipped_weapon": p["equipped_weapon"],
        "equipped_armor":  p["equipped_armor"],
        "base_hp":         s["base_hp"],
        "bonus_hp":        s["bonus_hp"],
        "max_hp":          s["max_hp"],
        "current_hp":      s["current_hp"],
        "bytes":           s["bytes"],
        "base_hit":        s["base_hit"],
        "bonus_hit":       s["bonus_hit"],
        "base_crit":       s["base_crit"],
        "bonus_crit":      s["bonus_crit"],
        "total_hit":       s["base_hit"] + s["bonus_hit"],
        "total_crit":      s["base_crit"] + s["bonus_crit"],
    }


def experience_needed_for_next_level(current_level: int) -> int:
    if current_level < 1:
        return 100
    return int(100 * (1.4 ** (current_level - 1)))


def level_up(player_id: int):
    c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    lvl, xp = row[0], row[1]
    needed  = experience_needed_for_next_level(lvl)
    if xp < needed:
        raise ValueError("Not enough experience to level up")
    c.execute("UPDATE players SET experience = experience - ?, level = level + 1 WHERE id = ?",
              (needed, player_id))
    c.execute("""
        UPDATE player_stats
        SET base_hp           = base_hp  + 20,
            max_hp            = max_hp   + 20,
            current_hp        = MAX(current_hp + 20, max_hp + 20),
            original_base_hit = original_base_hit + 5,
            base_hit          = base_hit  + 5,
            base_crit         = base_crit + 3
        WHERE player_id = ?
    """, (player_id,))
    conn.commit()
    print(f"\nlevel up! ({lvl} -> {lvl + 1})")


# ------------------------------------------------------------------ #
#  PROGRESSION — lives, clears, wipe                                 #
# ------------------------------------------------------------------ #

def get_lives(player_id: int) -> int:
    c.execute("SELECT lives FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    return row["lives"] if row and row["lives"] is not None else 3


def get_total_clears(player_id: int) -> int:
    c.execute("SELECT total_clears FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    return row["total_clears"] if row and row["total_clears"] is not None else 0


def increment_clears(player_id: int) -> int:
    c.execute(
        "UPDATE players SET total_clears = COALESCE(total_clears, 0) + 1 WHERE id = ?",
        (player_id,)
    )
    conn.commit()
    return get_total_clears(player_id)


def record_death_and_check_reset(player_id: int) -> tuple:
    """Decrement lives, increment deaths_since_reset.
    On 3rd death: wipe stats/inventory/gear/bytes, restore lives to 3.
    Returns (deaths_since_reset, did_reset).
    """
    c.execute("""
        UPDATE players
        SET deaths_since_reset = COALESCE(deaths_since_reset, 0) + 1,
            lives = MAX(0, COALESCE(lives, 3) - 1)
        WHERE id = ?
    """, (player_id,))
    conn.commit()

    c.execute("SELECT deaths_since_reset FROM players WHERE id = ?", (player_id,))
    dsr = c.fetchone()["deaths_since_reset"]

    if dsr >= 3:
        _hard_reset_player(player_id)
        return 0, True

    conn.commit()
    return dsr, False


def _hard_reset_player(player_id: int):
    """Wipe inventory, gear, stats, bytes. Keep level/xp/kills/deaths totals."""
    c.execute("SELECT item FROM inventory WHERE player_id = ?", (player_id,))
    items_held = [r[0] for r in c.fetchall()]
    c.execute("DELETE FROM inventory WHERE player_id = ?", (player_id,))
    for item_name in items_held:
        _cleanup_gear_row(item_name)

    c.execute("""
        UPDATE players
        SET equipped_weapon    = NULL,
            equipped_armor     = NULL,
            deaths_since_reset = 0,
            lives              = 3
        WHERE id = ?
    """, (player_id,))
    c.execute("""
        UPDATE player_stats
        SET bonus_hp   = 0,
            bonus_hit  = 0,
            bonus_crit = 0,
            base_hit   = original_base_hit,
            current_hp = base_hp,
            max_hp     = base_hp,
            bytes      = 50
        WHERE player_id = ?
    """, (player_id,))
    c.execute("DELETE FROM visited_shops WHERE player_id = ?", (player_id,))
    conn.commit()


def clear_user(player_id: int):
    """Full wipe used by the every-5-clears purge."""
    _hard_reset_player(player_id)


# ------------------------------------------------------------------ #
#  STARTER GEAR SETS                                                 #
# ------------------------------------------------------------------ #

def unlock_gear_set(player_id: int, set_id: int):
    c.execute("""
        INSERT OR IGNORE INTO player_unlocked_sets (player_id, set_id) VALUES (?, ?)
    """, (player_id, set_id))
    conn.commit()


def get_unlocked_gear_sets(player_id: int) -> list:
    c.execute("""
        SELECT s.* FROM starter_gear_sets s
        JOIN player_unlocked_sets u ON u.set_id = s.id
        WHERE u.player_id = ?
        ORDER BY s.id
    """, (player_id,))
    return c.fetchall()


def get_all_gear_sets() -> list:
    c.execute("SELECT * FROM starter_gear_sets ORDER BY id")
    return c.fetchall()


def ensure_starter_gear_in_db(gear_set):
    c.execute("SELECT COUNT(*) FROM weapons WHERE name = ?", (gear_set["weapon_name"],))
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO weapons
                (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, element, found)
            VALUES (?, ?, ?, ?, ?, ?, 'QUERY', 1)
        """, (gear_set["weapon_name"], gear_set["w_class"], gear_set["w_hit_mult"],
              gear_set["w_bonus_hp"], gear_set["w_bonus_hit"], gear_set["w_bonus_crit"]))

    c.execute("SELECT COUNT(*) FROM armors WHERE name = ?", (gear_set["armor_name"],))
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO armors
                (name, class_type, bonus_hp, bonus_hit, bonus_crit, element, found)
            VALUES (?, ?, ?, ?, ?, 'QUERY', 1)
        """, (gear_set["armor_name"], gear_set["a_class"],
              gear_set["a_bonus_hp"], gear_set["a_bonus_hit"], gear_set["a_bonus_crit"]))
    conn.commit()


# ------------------------------------------------------------------ #
#  INVENTORY                                                         #
# ------------------------------------------------------------------ #

def add_item(player_id: int, item: str, amount: int = 1):
    c.execute("INSERT INTO inventory (player_id, item, amount) VALUES (?, ?, ?)",
              (player_id, item, amount))


def remove_item(player_id: int, item: str):
    c.execute("DELETE FROM inventory WHERE player_id = ? AND item = ?", (player_id, item))


def _cleanup_gear_row(item_name: str):
    """Delete weapon/armor row if no player holds this item anymore."""
    c.execute("SELECT COUNT(*) FROM inventory WHERE item = ?", (item_name,))
    if c.fetchone()[0] == 0:
        c.execute("DELETE FROM weapons WHERE name = ?", (item_name,))
        c.execute("DELETE FROM armors  WHERE name = ?", (item_name,))


def remove_gear_item(player_id: int, item_name: str):
    c.execute("DELETE FROM inventory WHERE player_id = ? AND item = ?", (player_id, item_name))
    _cleanup_gear_row(item_name)
    conn.commit()


def remove_gear_item_by_rowid(player_id: int, rowid: int, item_name: str):
    c.execute("DELETE FROM inventory WHERE rowid = ?", (rowid,))
    _cleanup_gear_row(item_name)
    conn.commit()


def get_inventory(player_id: int) -> list:
    c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
    ew, ea = get_equipped(player_id)
    rows   = []
    for r in c.fetchall():
        item_data = get_item_data(r["item"])
        rows.append({
            "rowid":    r["rowid"],
            "item":     r["item"],
            "amount":   r["amount"],
            "equipped": r["item"] in (ew, ea),
            "kind":     item_data["kind"] if item_data else "potion",
            "data":     item_data,
        })
    return rows


# ------------------------------------------------------------------ #
#  GEAR                                                              #
# ------------------------------------------------------------------ #

def get_equipped(player_id: int) -> tuple:
    c.execute("SELECT equipped_weapon, equipped_armor FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    if not row:
        return None, None
    return row["equipped_weapon"], row["equipped_armor"]


def get_item_data(item_name: str):
    c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
    row = c.fetchone()
    if row:
        return dict(row) | {"kind": "weapon"}
    c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
    row = c.fetchone()
    if row:
        return dict(row) | {"kind": "armor"}
    return None


def equip_item(player_id: int, item_name: str) -> dict:
    item_data = get_item_data(item_name)
    if not item_data:
        return {"ok": False, "error": "Not a gear item."}
    ew, ea = get_equipped(player_id)
    kind   = item_data["kind"]
    if kind == "weapon":
        replaced = ew
        c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (item_name, player_id))
    else:
        replaced = ea
        c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (item_name, player_id))
    conn.commit()
    rebuild_stats(player_id)
    return {"ok": True, "kind": kind, "replaced": replaced}


def unequip_item(player_id: int, item_name: str) -> dict:
    item_data = get_item_data(item_name)
    if not item_data:
        return {"ok": False, "error": "Not a gear item."}
    kind = item_data["kind"]
    if kind == "weapon":
        c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
    else:
        c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
    conn.commit()
    rebuild_stats(player_id)
    return {"ok": True, "kind": kind}


def discard_item(player_id: int, rowid: int) -> dict:
    c.execute("SELECT item FROM inventory WHERE rowid = ?", (rowid,))
    row = c.fetchone()
    if not row:
        return {"ok": False, "error": "Item not found."}
    item_name = row["item"]
    ew, ea    = get_equipped(player_id)
    if item_name == ew:
        c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
    elif item_name == ea:
        c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
    remove_gear_item_by_rowid(player_id, rowid, item_name)
    rebuild_stats(player_id)
    return {"ok": True, "item": item_name}


def use_potion(player_id: int, rowid: int) -> dict:
    c.execute("SELECT item, amount FROM inventory WHERE rowid = ?", (rowid,))
    row = c.fetchone()
    if not row:
        return {"ok": False, "error": "Item not found."}
    result = apply_potion(player_id, row["item"])
    if not result:
        return {"ok": False, "error": "Not a usable potion."}
    if row["amount"] <= 1:
        c.execute("DELETE FROM inventory WHERE rowid = ?", (rowid,))
    else:
        c.execute("UPDATE inventory SET amount = amount - 1 WHERE rowid = ?", (rowid,))
    conn.commit()
    return {"ok": True} | result


def gear_buy_price(item: dict) -> int:
    is_weapon = "hit_mult" in item.keys()
    hm = item["hit_mult"] if is_weapon else 0
    return max(10, item["bonus_hp"] + item["bonus_hit"] + item["bonus_crit"] * 2 + hm * 3)


def gear_sell_price(item: dict) -> int:
    return max(1, int(gear_buy_price(item) * 0.4))


def bonus_calc(bonus_type: BonusType, player_id: int):
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    user_class = c.fetchone()[0]

    if bonus_type is BonusType.WEAPON:
        c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
        item = c.fetchone()[0]
        if item is None:
            return
        c.execute("SELECT * FROM weapons WHERE name = ?", (item,))
    elif bonus_type is BonusType.ARMOR:
        c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
        item = c.fetchone()[0]
        if item is None:
            return
        c.execute("SELECT * FROM armors WHERE name = ?", (item,))
    else:
        return

    data = c.fetchone()
    if data is None:
        return

    hit_mult   = data["hit_mult"] if bonus_type is BonusType.WEAPON else None
    bonus_hp   = data["bonus_hp"]
    bonus_hit  = data["bonus_hit"]
    bonus_crit = data["bonus_crit"]

    if data["class_type"] == user_class:
        if user_class == "The Executor":
            bonus_hp *= 2
        elif user_class == "The Indexer":
            bonus_crit *= 2
        elif user_class == "The Trigger":
            bonus_hit = bonus_hit * 2 + 20

    c.execute("""
        UPDATE player_stats
        SET bonus_hp   = bonus_hp   + ?,
            bonus_hit  = bonus_hit  + ?,
            bonus_crit = bonus_crit + ?
        WHERE player_id = ?
    """, (bonus_hp, bonus_hit, bonus_crit, player_id))

    if hit_mult is not None:
        c.execute("""
            UPDATE player_stats SET base_hit = original_base_hit * ? WHERE player_id = ?
        """, (hit_mult, player_id))


def rebuild_stats(player_id: int):
    c.execute("""
        UPDATE player_stats
        SET bonus_hp = 0, bonus_hit = 0, bonus_crit = 0, base_hit = original_base_hit
        WHERE player_id = ?
    """, (player_id,))
    bonus_calc(BonusType.WEAPON, player_id)
    bonus_calc(BonusType.ARMOR,  player_id)
    c.execute("""
        UPDATE player_stats SET max_hp = base_hp + bonus_hp WHERE player_id = ?
    """, (player_id,))
    conn.commit()


# ------------------------------------------------------------------ #
#  GEAR GENERATION                                                   #
# ------------------------------------------------------------------ #

def generate_gear(player_level: int, gear_type: str = "random") -> tuple:
    if gear_type == "random":
        gear_type = random.choice(["weapon", "armor"])

    lb = player_level - 1

    fname = "weapon_name.json" if gear_type == "weapon" else "armor_name.json"
    with open(fname, "r") as f:
        data = json.load(f)

    if gear_type == "weapon":
        name = f"{random.choice(data['first_name'])} {random.choice(data['second_name'])}"
    else:
        name = random.choice(data)

    class_type = random.choice(["The Executor", "The Trigger", "The Indexer"])
    element    = random.choice(["QUERY", "LOCK", "OVERFLOW", "NULL"])

    if class_type == "The Executor":
        bonus_hp   = min(100, random.randint(20, 50)  + lb * 20)
        bonus_hit  = min(100, random.randint(5,  20)  + lb * 3)
        bonus_crit = min(100, random.randint(0,  4)   + lb)
        hit_mult   = random.randint(1, 5)
    elif class_type == "The Trigger":
        bonus_hp   = min(100, random.randint(5,  25)  + lb * 12)
        bonus_hit  = min(100, random.randint(10, 30)  + lb * 4)
        bonus_crit = min(100, random.randint(5,  15)  + lb * 2)
        hit_mult   = random.randint(1, 5)
    else:
        bonus_hp   = min(100, random.randint(20, 100) + lb * 5)
        bonus_hit  = min(100, random.randint(5,  20)  + lb * 2)
        bonus_crit = min(100, random.randint(10, 30)  + lb * 4)
        hit_mult   = random.randint(1, 5)

    if gear_type == "weapon":
        c.execute("""
            INSERT INTO weapons
                (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, element, found)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, element))
    else:
        c.execute("""
            INSERT INTO armors
                (name, class_type, bonus_hp, bonus_hit, bonus_crit, element, found)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (name, class_type, bonus_hp, bonus_hit, bonus_crit, element))

    conn.commit()
    return c.lastrowid, name, gear_type


def drop_boss_loot(player_id: int, boss_type: str) -> list:
    boss_name = boss_type.replace("OVERFLOW — ", "").strip()
    c.execute("""
        SELECT id, item_name, item_type, class_type, hit_mult,
               bonus_hp, bonus_hit, bonus_crit
        FROM boss_loot WHERE boss_name = ? AND claimed = 0
    """, (boss_name,))
    rows    = c.fetchall()
    dropped = []
    for row in rows:
        if row["item_type"] == "weapon":
            c.execute("""
                INSERT OR IGNORE INTO weapons
                    (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, found)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (row["item_name"], row["class_type"], row["hit_mult"],
                  row["bonus_hp"], row["bonus_hit"], row["bonus_crit"]))
        else:
            c.execute("""
                INSERT OR IGNORE INTO armors
                    (name, class_type, bonus_hp, bonus_hit, bonus_crit, found)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (row["item_name"], row["class_type"],
                  row["bonus_hp"], row["bonus_hit"], row["bonus_crit"]))
        add_item(player_id, row["item_name"], 1)
        c.execute("UPDATE boss_loot SET claimed = 1 WHERE id = ?", (row["id"],))
        dropped.append((row["item_name"], row["item_type"]))
    conn.commit()
    return dropped


# ------------------------------------------------------------------ #
#  SHOP                                                              #
# ------------------------------------------------------------------ #

SHOP_STOCK_SIZE = 3


def roll_shop_stock(player_id: int, path_id, run_seed: int, fateful_day: bool) -> dict:
    saved           = load_shop_stock(path_id) if path_id else None
    potion_pool_map = {p[0]: p for p in get_potion_pool()}

    if saved:
        gear_stock   = []
        potion_stock = []
        weapon_ids   = set()
        for row in saved:
            item_type, item_name = row["item_type"], row["item_name"]
            if item_type == "weapon":
                c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
                r = c.fetchone()
                if r:
                    gear_stock.append(dict(r) | {"kind": "weapon"})
                    weapon_ids.add(r["id"])
            elif item_type == "armor":
                c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
                r = c.fetchone()
                if r:
                    gear_stock.append(dict(r) | {"kind": "armor"})
            elif item_type == "potion" and item_name in potion_pool_map:
                potion_stock.append(potion_pool_map[item_name])
        return {"gear_stock": gear_stock, "potion_stock": potion_stock, "weapon_ids": weapon_ids}

    shop_rng = random.Random((run_seed or 0) ^ (path_id or 0))
    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()["level"]

    weapon_pool = []
    armor_pool  = []
    weapon_ids  = set()

    for _ in range(SHOP_STOCK_SIZE * 2):
        _, name, _ = generate_gear(player_level, "weapon")
        c.execute("SELECT * FROM weapons WHERE name = ?", (name,))
        r = c.fetchone()
        if r:
            weapon_pool.append(dict(r) | {"kind": "weapon"})
            weapon_ids.add(r["id"])

    for _ in range(SHOP_STOCK_SIZE * 2):
        _, name, _ = generate_gear(player_level, "armor")
        c.execute("SELECT * FROM armors WHERE name = ?", (name,))
        r = c.fetchone()
        if r:
            armor_pool.append(dict(r) | {"kind": "armor"})

    if not weapon_pool:
        c.execute("SELECT * FROM weapons ORDER BY RANDOM() LIMIT ?", (SHOP_STOCK_SIZE * 2,))
        weapon_pool = [dict(r) | {"kind": "weapon"} for r in c.fetchall()]
    if not armor_pool:
        c.execute("SELECT * FROM armors ORDER BY RANDOM() LIMIT ?", (SHOP_STOCK_SIZE * 2,))
        armor_pool = [dict(r) | {"kind": "armor"} for r in c.fetchall()]

    combined = weapon_pool + armor_pool
    if fateful_day:
        scores     = [i["bonus_hp"] + i["bonus_hit"] + i["bonus_crit"] + 1 for i in combined]
        gear_stock = shop_rng.choices(combined, weights=scores, k=min(SHOP_STOCK_SIZE, len(combined)))
    else:
        gear_stock = shop_rng.sample(combined, min(SHOP_STOCK_SIZE, len(combined)))

    all_potions  = get_potion_pool()
    pw           = [p[7] for p in all_potions] if fateful_day else [1 / (p[7] + 1) * 100 for p in all_potions]
    potion_stock = shop_rng.choices(all_potions, weights=pw, k=SHOP_STOCK_SIZE)

    if path_id:
        to_save = [(item["kind"], item["name"]) for item in gear_stock]
        to_save += [("potion", pot[0]) for pot in potion_stock]
        save_shop_stock(path_id, to_save)

    return {"gear_stock": gear_stock, "potion_stock": potion_stock, "weapon_ids": weapon_ids}


def buy_gear(player_id: int, item: dict) -> dict:
    c.execute("SELECT bytes FROM player_stats WHERE player_id = ?", (player_id,))
    bytes_have = c.fetchone()["bytes"]
    price      = gear_buy_price(item)
    if bytes_have < price:
        return {"ok": False, "error": "Not enough bytes."}
    c.execute("UPDATE player_stats SET bytes = bytes - ? WHERE player_id = ?", (price, player_id))
    add_item(player_id, item["name"], 1)
    if item.get("kind") == "weapon":
        c.execute("UPDATE weapons SET found = 1 WHERE id = ?", (item["id"],))
    else:
        c.execute("UPDATE armors SET found = 1 WHERE id = ?", (item["id"],))
    conn.commit()
    return {"ok": True, "item": item["name"], "price": price}


def buy_potion(player_id: int, pot: tuple) -> dict:
    pname, _, _, _, _, _, _, pprice = pot
    c.execute("SELECT bytes FROM player_stats WHERE player_id = ?", (player_id,))
    bytes_have = c.fetchone()["bytes"]
    if bytes_have < pprice:
        return {"ok": False, "error": "Not enough bytes."}
    c.execute("UPDATE player_stats SET bytes = bytes - ? WHERE player_id = ?", (pprice, player_id))
    add_item(player_id, pname, 1)
    conn.commit()
    return {"ok": True, "item": pname, "price": pprice}


def sell_item(player_id: int, rowid: int) -> dict:
    c.execute("SELECT item, amount FROM inventory WHERE rowid = ?", (rowid,))
    row = c.fetchone()
    if not row:
        return {"ok": False, "error": "Item not found."}
    item_name = row["item"]
    item_data = get_item_data(item_name)
    sv        = gear_sell_price(item_data) if item_data else 5
    ew, ea    = get_equipped(player_id)
    if item_name == ew:
        c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
    elif item_name == ea:
        c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
    if row["amount"] <= 1:
        remove_gear_item_by_rowid(player_id, rowid, item_name)
    else:
        c.execute("UPDATE inventory SET amount = amount - 1 WHERE rowid = ?", (rowid,))
        conn.commit()
    c.execute("UPDATE player_stats SET bytes = bytes + ? WHERE player_id = ?", (sv, player_id))
    conn.commit()
    rebuild_stats(player_id)
    return {"ok": True, "item": item_name, "value": sv}


def register_shop_visit(player_id: int, path_id: int):
    c.execute("SELECT 1 FROM visited_shops WHERE player_id = ? AND path_id = ?",
              (player_id, path_id))
    if not c.fetchone():
        c.execute("DELETE FROM visited_shops")
        c.execute("INSERT INTO visited_shops (player_id, path_id) VALUES (?, ?)",
                  (player_id, path_id))
        conn.commit()


def get_visited_shops(player_id: int) -> list:
    c.execute("""
        SELECT p.* FROM path p
        JOIN visited_shops v ON v.path_id = p.id
        WHERE v.player_id = ?
    """, (player_id,))
    return c.fetchall()


def save_shop_stock(path_id: int, stock: list):
    c.execute("SELECT COUNT(*) FROM shop_stock WHERE path_id = ?", (path_id,))
    if c.fetchone()[0] > 0:
        return
    rows = [(path_id, i, t, n) for i, (t, n) in enumerate(stock)]
    c.executemany("""
        INSERT OR IGNORE INTO shop_stock (path_id, slot, item_type, item_name)
        VALUES (?, ?, ?, ?)
    """, rows)
    conn.commit()


def load_shop_stock(path_id: int):
    c.execute("""
        SELECT item_type, item_name FROM shop_stock WHERE path_id = ? ORDER BY slot ASC
    """, (path_id,))
    rows = c.fetchall()
    return rows if rows else None


def remove_shop_stock_item(path_id: int, item_name: str):
    c.execute("DELETE FROM shop_stock WHERE path_id = ? AND item_name = ?", (path_id, item_name))
    conn.commit()


# ------------------------------------------------------------------ #
#  POTIONS                                                           #
# ------------------------------------------------------------------ #

def get_potion_pool() -> list:
    return [
        # name                  type              heal%  hit  crit  def  dur  price
        ("Minor Restore",      "RESTORE",          15,    0,   0,   0,   1,   10),
        ("Restore",            "RESTORE",          30,    0,   0,   0,   1,   20),
        ("Major Restore",      "RESTORE",          60,    0,   0,   0,   1,   40),
        ("Minor Surge",        "SURGE",             0,    8,   0,   0,   3,   15),
        ("Surge",              "SURGE",             0,   18,   0,   0,   3,   30),
        ("Major Surge",        "SURGE",             0,   35,   0,   0,   5,   55),
        ("Minor Clarity",      "CLARITY",           0,    0,   8,   0,   3,   15),
        ("Clarity",            "CLARITY",           0,    0,  18,   0,   3,   30),
        ("Major Clarity",      "CLARITY",           0,    0,  35,   0,   5,   55),
        ("Minor Barrier",      "BARRIER",           0,    0,   0,  200,  3,   15),
        ("Barrier",            "BARRIER",           0,    0,   0,  460,  3,   30),
        ("Major Barrier",      "BARRIER",           0,    0,   0,  960,  5,   55),
        ("Mending Surge",      "RESTORE_SURGE",    20,   12,   0,   0,   3,   35),
        ("Vital Surge",        "RESTORE_SURGE",    40,   25,   0,   0,   3,   65),
        ("Mending Clarity",    "RESTORE_CLARITY",  20,    0,  12,   0,   3,   35),
        ("Vital Clarity",      "RESTORE_CLARITY",  40,    0,  25,   0,   3,   65),
        ("Mind and Blade",     "SURGE_CLARITY",     0,   15,  15,   0,   3,   50),
        ("Grand Elixir",       "SURGE_CLARITY",     0,   30,  30,   0,   5,   90),
    ]


def apply_potion(player_id: int, potion_name: str) -> dict:
    pool = {p[0]: p for p in get_potion_pool()}
    if potion_name not in pool:
        return {}

    _, ptype, heal_pct, bhit, bcrit, bdef, dur, _ = pool[potion_name]
    result = {}

    if heal_pct > 0:
        c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
        max_hp = c.fetchone()["max_hp"]
        heal   = max(1, int(max_hp * heal_pct / 100))
        c.execute("""
            UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?
        """, (heal, player_id))
        result["heal"] = heal

    if bhit > 0:
        c.execute("UPDATE player_stats SET bonus_hit = bonus_hit + ? WHERE player_id = ?",
                  (bhit, player_id))
        result["bonus_hit"] = bhit

    if bcrit > 0:
        c.execute("UPDATE player_stats SET bonus_crit = bonus_crit + ? WHERE player_id = ?",
                  (bcrit, player_id))
        result["bonus_crit"] = bcrit

    if bdef > 0:
        result["defense"] = bdef

    conn.commit()
    return result


def enemy_drop_potion(player_id: int):
    if random.random() > 0.35:
        return None
    pool    = get_potion_pool()
    weights = [1 / (p[7] + 1) * 100 for p in pool]
    chosen  = random.choices(pool, weights=weights, k=1)[0]
    add_item(player_id, chosen[0], 1)
    return chosen[0]


# ------------------------------------------------------------------ #
#  ENEMIES                                                           #
# ------------------------------------------------------------------ #

ENEMY_ELEMENT = {
    "Corrupted Index": "LOCK",
    "Null Pointer":    "NULL",
    "Stack Overflow":  "OVERFLOW",
    "Deadlock Wraith": "LOCK",
    "Zombie Process":  "NULL",
}

ELEMENT_WEAKNESS = {
    "QUERY":    "LOCK",
    "LOCK":     "OVERFLOW",
    "OVERFLOW": "NULL",
    "NULL":     "QUERY",
}

ENEMY_PROFILES = {
    "Corrupted Index": {"hp_mult": 1.3, "hit_mult": 0.8, "xp_mult": 1.0},
    "Null Pointer":    {"hp_mult": 0.8, "hit_mult": 1.4, "xp_mult": 1.1},
    "Stack Overflow":  {"hp_mult": 1.1, "hit_mult": 1.2, "xp_mult": 1.2},
    "Deadlock Wraith": {"hp_mult": 1.0, "hit_mult": 0.9, "xp_mult": 0.9},
    "Zombie Process":  {"hp_mult": 1.6, "hit_mult": 0.6, "xp_mult": 0.8},
}

BASE_ENEMY_HP         = 80
BASE_ENEMY_HIT        = 10
HP_PER_LEVEL          = 25
HIT_PER_LEVEL         = 3
OVERFLOW_BOSSES_TOTAL = 5

CONSTRAINT_EVENTS = [
    ("blood_moon",    "BLOOD MOON",     "All enemies strike with doubled force."),
    ("solar_eclipse", "SOLAR ECLIPSE",  "The Indexer's crit surges to new heights."),
    ("flood_omnya",   "FLOOD OF OMNYA", "Certain paths are swallowed by rising waters."),
    ("monster_rush",  "MONSTER RUSH",   "Each enemy strikes an additional time."),
    ("fateful_day",   "FATEFUL DAY",    "Rare treasures surface in every market."),
]
EVENT_EXPIRY_ENCOUNTERS = 10


def generate_enemy(player_id: int, is_boss: bool = False) -> int:
    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()["level"]

    enemy_type = random.choice(list(ENEMY_PROFILES.keys()))
    profile    = ENEMY_PROFILES[enemy_type]

    hp_var  = random.uniform(0.88, 1.12)
    hit_var = random.uniform(0.88, 1.12)

    base_hp  = max(40, int((BASE_ENEMY_HP  + HP_PER_LEVEL  * (player_level - 1)) * profile["hp_mult"]  * hp_var))
    base_hit = max(8,  int((BASE_ENEMY_HIT + HIT_PER_LEVEL * (player_level - 1)) * profile["hit_mult"] * hit_var))
    xp_drop  = int((20 + player_level * 5 + random.randint(-5, 5)) * profile["xp_mult"])

    if is_boss:
        base_hp    = int(base_hp  * 3.5)
        base_hit   = int(base_hit * 1.8)
        xp_drop   *= 5
        enemy_type = "OVERFLOW — " + random.choice(
            ["The Warlord", "The Tyrant", "The Behemoth", "The Archmage", "The Overseer"]
        )

    c.execute("""
        INSERT INTO enemies (type, base_hp, max_hp, base_hit, experience_drop)
        VALUES (?, ?, ?, ?, ?)
    """, (enemy_type, base_hp, base_hp, base_hit, xp_drop))
    conn.commit()
    return c.lastrowid


def apply_event_combat_modifiers(enemy_id: int, events: dict):
    if events.get("blood_moon"):
        c.execute("UPDATE enemies SET base_hit = base_hit * 2 WHERE id = ?", (enemy_id,))
        conn.commit()


def apply_status(player_id: int, effect: str, duration: int):
    c.execute("INSERT INTO status_effects (player_id, effect, duration) VALUES (?, ?, ?)",
              (player_id, effect, duration))
    conn.commit()


def get_statuses(player_id: int) -> list:
    c.execute("SELECT effect, duration FROM status_effects WHERE player_id = ?", (player_id,))
    return c.fetchall()


def tick_statuses(player_id: int) -> list:
    c.execute("SELECT rowid, effect, duration FROM status_effects WHERE player_id = ?", (player_id,))
    rows = c.fetchall()
    log  = []
    for row in rows:
        if row["effect"] == "CORRUPTION":
            c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
            max_hp = c.fetchone()["max_hp"]
            dot    = max(1, int(max_hp * 0.05))
            c.execute("UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
                      (dot, player_id))
            log.append(f"CORRUPTION burns you for {dot} damage.")
        if row["effect"] == "SEGFAULT":
            stat  = random.choice(["bonus_hit", "bonus_crit"])
            drain = random.randint(1, 5)
            c.execute(f"UPDATE player_stats SET {stat} = MAX(0, {stat} - ?) WHERE player_id = ?",
                      (drain, player_id))
            log.append(f"SEGFAULT drains {drain} {stat.replace('bonus_', '')}.")
        new_dur = row["duration"] - 1
        if new_dur <= 0:
            c.execute("DELETE FROM status_effects WHERE rowid = ?", (row["rowid"],))
            log.append(f"{row['effect']} fades.")
        else:
            c.execute("UPDATE status_effects SET duration = ? WHERE rowid = ?", (new_dur, row["rowid"]))
    conn.commit()
    return log


def record_overflow_kill(player_id: int) -> int:
    c.execute("UPDATE players SET overflow_kills = overflow_kills + 1 WHERE id = ?", (player_id,))
    conn.commit()
    c.execute("SELECT overflow_kills FROM players WHERE id = ?", (player_id,))
    return c.fetchone()["overflow_kills"]


# ------------------------------------------------------------------ #
#  COMBAT ACTIONS                                                    #
# ------------------------------------------------------------------ #

TRAP_DAMAGE_PERCENT = random.uniform(0.10, 0.30)
DUNGEON_ROOM_COUNT  = 3


def spawn_enemy(player_id: int, is_boss: bool = False, events: dict | None = None) -> dict:
    enemy_id = generate_enemy(player_id, is_boss=is_boss)
    if events:
        apply_event_combat_modifiers(enemy_id, events)
    c.execute("SELECT type, base_hp, max_hp, base_hit FROM enemies WHERE id = ?", (enemy_id,))
    row = c.fetchone()
    return {"enemy_id": enemy_id, "type": row["type"], "hp": row["base_hp"],
            "max_hp": row["max_hp"], "base_hit": row["base_hit"]}


def get_enemy_state(enemy_id: int) -> dict:
    c.execute("SELECT type, base_hp, max_hp FROM enemies WHERE id = ?", (enemy_id,))
    row = c.fetchone()
    return {"type": row["type"], "hp": row["base_hp"], "max_hp": row["max_hp"]}


def get_combat_potions(player_id: int) -> list:
    potion_names = {p[0] for p in get_potion_pool()}
    c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
    return [dict(r) for r in c.fetchall() if r["item"] in potion_names]


def do_attack(player_id: int, enemy_id: int) -> dict:
    c.execute("""
        SELECT base_hit, bonus_hit, base_crit, bonus_crit
        FROM player_stats WHERE player_id = ?
    """, (player_id,))
    ps = c.fetchone()

    dmg         = max(1, ps["base_hit"] + ps["bonus_hit"] - random.randint(0, 5))
    crit_chance = min(0.60, (ps["base_crit"] + ps["bonus_crit"]) * 0.005)
    is_crit     = random.random() < crit_chance
    if is_crit:
        dmg *= 2

    c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (dmg, enemy_id))
    conn.commit()

    element_bonus = False
    c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    weapon_name = c.fetchone()["equipped_weapon"]
    if weapon_name:
        c.execute("SELECT element FROM weapons WHERE name = ?", (weapon_name,))
        w_row = c.fetchone()
        c.execute("SELECT type FROM enemies WHERE id = ?", (enemy_id,))
        enemy_type    = c.fetchone()["type"]
        base_type     = enemy_type.replace("OVERFLOW — ", "").strip()
        enemy_element  = ENEMY_ELEMENT.get(base_type)
        weapon_element = w_row["element"] if w_row else None
        if weapon_element and enemy_element and ELEMENT_WEAKNESS.get(weapon_element) == enemy_element:
            bonus = int(dmg * 0.5)
            c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (bonus, enemy_id))
            dmg  += bonus
            conn.commit()
            element_bonus = True

    c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hp = c.fetchone()[0]
    return {"dmg": dmg, "is_crit": is_crit, "element_bonus": element_bonus,
            "enemy_hp": enemy_hp, "enemy_dead": enemy_hp <= 0}


def do_enemy_turn(player_id: int, enemy_id: int, events: dict, active_defense: int) -> dict:
    c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    ehit = c.fetchone()[0]
    log  = []

    dmg = max(0, ehit - random.randint(0, 5))

    if active_defense > 0:
        absorbed       = min(active_defense, dmg)
        dmg           -= absorbed
        active_defense -= absorbed
        if absorbed:
            log.append(f"barrier absorbs {absorbed} damage.")

    if dmg > 0:
        c.execute("UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
                  (dmg, player_id))
        log.append(f"enemy hits you for {dmg} damage.")
    else:
        log.append("enemy attacks — barrier holds!")

    if events.get("monster_rush"):
        extra = max(0, int(ehit * 0.5) + random.randint(0, 3))
        c.execute("UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
                  (extra, player_id))
        log.append(f"monster rush second strike: -{extra} hp.")

    status_inflicted = None
    if random.random() < 0.15:
        effect   = random.choice(["DEADLOCK", "CORRUPTION", "SEGFAULT"])
        duration = random.randint(2, 3)
        apply_status(player_id, effect, duration)
        log.append(f"you are afflicted with {effect} for {duration} turns!")
        status_inflicted = effect

    conn.commit()
    c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    player_hp = c.fetchone()[0]

    return {
        "dmg": dmg, "active_defense": active_defense,
        "player_hp": player_hp, "player_dead": player_hp <= 0,
        "status_inflicted": status_inflicted, "log": log,
    }


def do_flee(player_id: int, enemy_id: int) -> dict:
    c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    ehit     = c.fetchone()[0]
    flee_dmg = max(0, ehit // 2 - random.randint(0, 3))
    c.execute("UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
              (flee_dmg, player_id))
    c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
    conn.commit()
    return {"flee_dmg": flee_dmg}


def do_combo_strike(player_id: int, enemy_id: int) -> dict:
    c.execute("SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,))
    ps  = c.fetchone()
    dmg = max(1, ps["base_hit"] + ps["bonus_hit"])
    c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (dmg, enemy_id))
    conn.commit()
    c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hp = c.fetchone()[0]
    return {"dmg": dmg, "enemy_hp": enemy_hp, "enemy_dead": enemy_hp <= 0}


def on_enemy_defeated(player_id: int, enemy_id: int, run_id) -> dict:
    c.execute("SELECT experience_drop FROM enemies WHERE id = ?", (enemy_id,))
    xp         = c.fetchone()[0]
    bytes_drop = random.randint(8, 30)

    c.execute("UPDATE players SET experience = experience + ?, kills = kills + 1 WHERE id = ?",
              (xp, player_id))
    c.execute("UPDATE player_stats SET bytes = bytes + ? WHERE player_id = ?",
              (bytes_drop, player_id))
    conn.commit()

    if run_id:
        record_run_kill(run_id)
        record_run_bytes(run_id, bytes_drop)

    c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
    conn.commit()

    drop      = enemy_drop_potion(player_id)
    leveled_up = False
    c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    if row["experience"] >= experience_needed_for_next_level(row["level"]):
        level_up(player_id)
        leveled_up = True

    return {"xp": xp, "bytes": bytes_drop, "drop": drop, "leveled_up": leveled_up}


def on_player_defeated(player_id: int) -> dict:
    c.execute("UPDATE players SET deaths = deaths + 1 WHERE id = ?", (player_id,))
    c.execute("UPDATE player_stats SET current_hp = max_hp WHERE player_id = ?", (player_id,))
    c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
    conn.commit()
    return {"deaths": 1}


def on_boss_defeated(player_id: int, enemy_id: int) -> dict:
    c.execute("SELECT type FROM enemies WHERE id = ?", (enemy_id,))
    boss_type      = c.fetchone()["type"]
    drops          = drop_boss_loot(player_id, boss_type)
    overflow_kills = record_overflow_kill(player_id)
    return {
        "drops":          drops,
        "overflow_kills": overflow_kills,
        "game_complete":  overflow_kills >= OVERFLOW_BOSSES_TOTAL,
    }


# ------------------------------------------------------------------ #
#  DUNGEON                                                           #
# ------------------------------------------------------------------ #

def roll_room_type(is_final: bool) -> str:
    if is_final:
        return "combat"
    roll = random.random()
    if roll < 0.55:
        return "combat"
    elif roll < 0.80:
        return "trap"
    return "rest"


def do_trap(player_id: int) -> dict:
    c.execute("SELECT base_crit + bonus_crit AS crit FROM player_stats WHERE player_id = ?",
              (player_id,))
    crit   = c.fetchone()["crit"]
    c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
    max_hp = c.fetchone()["max_hp"]

    trap_dmg_full = max(5, int(max_hp * TRAP_DAMAGE_PERCENT))
    dodge_chance  = min(0.60, crit * 0.005)
    dodged        = random.random() < dodge_chance
    trap_dmg      = trap_dmg_full // 2 if dodged else trap_dmg_full

    c.execute("UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
              (trap_dmg, player_id))
    conn.commit()
    c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    remaining_hp = c.fetchone()["current_hp"]
    return {"dmg": trap_dmg, "dodged": dodged, "barely_alive": remaining_hp <= 1}


def do_dungeon_rest(player_id: int) -> dict:
    c.execute("SELECT max_hp, current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    row      = c.fetchone()
    heal_amt = max(5, int(row["max_hp"] * 0.12))
    c.execute("UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?",
              (heal_amt, player_id))
    conn.commit()
    return {"healed": heal_amt}


def dungeon_final_loot(player_id: int) -> dict:
    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()["level"]
    _, loot_name, loot_type = generate_gear(player_level)
    add_item(player_id, loot_name, 1)
    conn.commit()
    return {"item": loot_name, "kind": loot_type}


# ------------------------------------------------------------------ #
#  REST NODE                                                         #
# ------------------------------------------------------------------ #

def rest_heal(player_id: int) -> dict:
    c.execute("SELECT max_hp, current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    row      = c.fetchone()
    missing  = row["max_hp"] - row["current_hp"]
    heal_pct = random.uniform(0.5, 1.0)
    heal_amt = max(1, int(missing * heal_pct))
    c.execute("UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?",
              (heal_amt, player_id))
    conn.commit()
    return {"healed": heal_amt}


# ------------------------------------------------------------------ #
#  RUNS & PATHS                                                      #
# ------------------------------------------------------------------ #

def init_run(player_id: int, custom_seed: int = None) -> tuple:
    seed = custom_seed if custom_seed is not None else int(time.time() * 1000) % (2**31)

    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()[0]
    level_range  = min((player_level - 1) // 10, 9)

    c.execute("INSERT INTO runs (player_id, seed, level_range) VALUES (?, ?, ?)",
              (player_id, seed, level_range))
    run_id = c.lastrowid
    conn.commit()

    c.execute("UPDATE players SET current_run_id = ? WHERE id = ?", (run_id, player_id))
    conn.commit()

    root_id = _generate_path(run_id, level_range, seed, player_level)

    recommended_min = level_range * 10 + 1
    if player_level < recommended_min:
        print(f"  WARNING: this run is tuned for level {recommended_min}+.")
        print(f"  you are level {player_level}. proceed with caution.")
        print()

    return run_id, root_id, seed


def _generate_path(run_id: int, level_range: int, seed: int, player_level: int = 1) -> int:
    rng = random.Random(seed)

    c.execute("""
        SELECT name, description, encounter_type FROM map
        WHERE level_range = ? AND encounter_type != 5
    """, (level_range,))
    pool = c.fetchall() or [("Unknown Path", "A mysterious encounter.", 1)]

    c.execute("""
        SELECT name, description, encounter_type FROM map
        WHERE level_range = ? AND encounter_type = 5
    """, (level_range,))
    boss_pool = c.fetchall() or [("Ancient Overflow", "An OVERFLOW node. A boss encounter.", 5)]

    WEIGHTS = {0: 1, 1: 6, 2: 2, 3: 2, 4: 1, 5: 0, 6: 3}

    def weighted_pick(exclude_types=()):
        candidates = [r for r in pool if r["encounter_type"] not in exclude_types]
        weights    = [WEIGHTS.get(r["encounter_type"], 1) for r in (candidates or pool)]
        return rng.choices(candidates or pool, weights=weights, k=1)[0]

    def insert_node(parent_id, depth, branch, row, is_boss=False):
        enc_type = 5 if is_boss else row["encounter_type"]
        c.execute("""
            INSERT INTO path
                (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, parent_id, depth, branch,
              row["name"], row["description"], enc_type, level_range))
        return c.lastrowid

    extra_depths  = min(4, (player_level - 1) // 5)
    MIDDLE_DEPTHS = list(range(2, 4 + extra_depths))
    boss_depth    = MIDDLE_DEPTHS[-1] + 1 if MIDDLE_DEPTHS else 2

    c.execute("""
        INSERT INTO path
            (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
        VALUES (?, NULL, 0, 1, 'START', 'The journey begins here.', -1, ?)
    """, (run_id, level_range))
    root_id = c.lastrowid

    shop_candidates = [r for r in pool if r["encounter_type"] == 0]
    depth1_branches = sorted(rng.sample([0, 1, 2], rng.randint(2, 3)))
    depth1_ids      = []
    for i, branch in enumerate(depth1_branches):
        row = rng.choice(shop_candidates or pool) if i == 0 else weighted_pick(exclude_types=(5,))
        depth1_ids.append((insert_node(root_id, 1, branch, row), branch))

    prev_ids = depth1_ids
    for depth in MIDDLE_DEPTHS:
        next_ids = []
        for parent_id, _ in prev_ids:
            branches = sorted(rng.sample([0, 1, 2], rng.randint(1, 3)))
            for branch in branches:
                row = weighted_pick(exclude_types=(5,))
                next_ids.append((insert_node(parent_id, depth, branch, row), branch))
        prev_ids = next_ids

    for parent_id, _ in prev_ids:
        insert_node(parent_id, boss_depth, 1, rng.choice(boss_pool), is_boss=True)

    conn.commit()
    return root_id


def get_path_node(path_id: int):
    c.execute("SELECT * FROM path WHERE id = ?", (path_id,))
    return c.fetchone()


def get_path_children(path_id: int) -> list:
    c.execute("SELECT * FROM path WHERE parent_id = ? ORDER BY branch ASC", (path_id,))
    return c.fetchall()


def move_to_node(player_id: int, path_id: int):
    c.execute("UPDATE players SET current_path_id = ? WHERE id = ?", (path_id, player_id))
    conn.commit()


def finish_node(path_id: int):
    c.execute("UPDATE path SET finished = 1 WHERE id = ?", (path_id,))
    conn.commit()


def get_node(path_id: int) -> dict:
    row = get_path_node(path_id)
    return dict(row) if row else {}


def get_children(path_id: int) -> list:
    return [dict(r) for r in get_path_children(path_id)]


def start_run(player_id: int, custom_seed=None) -> dict:
    run_id, root_id, seed = init_run(player_id, custom_seed)
    events = load_events()
    _apply_solar_eclipse(player_id, events, remove=False)
    return {"run_id": run_id, "root_id": root_id, "seed": seed, "events": events}


def finish_run(run_id: int, outcome: str):
    c.execute("""
        UPDATE runs SET outcome = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (outcome, run_id))
    conn.commit()


def finish_run_full(run_id: int, player_id: int, outcome: str) -> dict:
    finish_run(run_id, outcome)
    events = load_events()
    _apply_solar_eclipse(player_id, events, remove=True)
    rebuild_stats(player_id)
    return dict(get_run_stats(run_id))


def get_run_stats(run_id: int):
    c.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    return c.fetchone()


def get_runs_amount(player_id: int) -> int:
    c.execute("SELECT COUNT(*) FROM runs WHERE player_id = ?", (player_id,))
    return c.fetchone()[0]


def fetch_runs_stats(player_id: int) -> list:
    c.execute("SELECT * FROM runs WHERE player_id = ? ORDER BY created_at", (player_id,))
    return c.fetchall()


def record_run_kill(run_id: int):
    c.execute("UPDATE runs SET kills = kills + 1 WHERE id = ?", (run_id,))
    conn.commit()


def record_run_bytes(run_id: int, amount: int):
    c.execute("UPDATE runs SET bytes_earned = bytes_earned + ? WHERE id = ?", (amount, run_id))
    conn.commit()


def record_run_node(run_id: int):
    c.execute("UPDATE runs SET nodes_cleared = nodes_cleared + 1 WHERE id = ?", (run_id,))
    conn.commit()


# ------------------------------------------------------------------ #
#  EVENTS                                                            #
# ------------------------------------------------------------------ #

def load_events() -> dict:
    c.execute("SELECT * FROM events LIMIT 1")
    row = c.fetchone()
    if row:
        return dict(row)
    return {
        "blood_moon": 0, "solar_eclipse": 0, "flood_omnya": 0,
        "monster_rush": 0, "fateful_day": 0, "encounters_since_reset": 0,
    }


def _apply_solar_eclipse(player_id: int, events: dict, remove: bool):
    if not events.get("solar_eclipse"):
        return
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    if c.fetchone()[0] != "The Indexer":
        return
    if remove:
        c.execute("UPDATE player_stats SET bonus_crit = bonus_crit / 2 WHERE player_id = ?",
                  (player_id,))
    else:
        c.execute("UPDATE player_stats SET bonus_crit = bonus_crit * 2 WHERE player_id = ?",
                  (player_id,))
    conn.commit()


def trigger_constraint_event(player_id: int, events: dict) -> dict:
    inactive = [e for e in CONSTRAINT_EVENTS if not events.get(e[0])]
    if not inactive:
        return {"fired": False}
    key, name, _ = random.choice(inactive)
    c.execute(f"UPDATE events SET {key} = 1")
    conn.commit()
    desc   = next((e[2] for e in CONSTRAINT_EVENTS if e[0] == key), "")
    events = load_events()
    if key == "solar_eclipse":
        _apply_solar_eclipse(player_id, events, remove=False)
    return {"fired": True, "key": key, "name": name, "desc": desc, "events": events}


def tick_event_counter() -> dict:
    c.execute("UPDATE events SET encounters_since_reset = encounters_since_reset + 1")
    conn.commit()
    c.execute("SELECT encounters_since_reset FROM events LIMIT 1")
    count = c.fetchone()[0]
    if count >= EVENT_EXPIRY_ENCOUNTERS:
        c.execute("""
            UPDATE events SET blood_moon=0, solar_eclipse=0, flood_omnya=0,
                              monster_rush=0, fateful_day=0, encounters_since_reset=0
        """)
        conn.commit()
        return {"reset": True, "events": load_events()}
    return {"reset": False, "events": load_events()}


# ------------------------------------------------------------------ #
#  NPC / ARCHIVIST                                                   #
# ------------------------------------------------------------------ #

def get_archivist_line(player_id: int, events: dict) -> str:
    c.execute("SELECT kills, deaths FROM players WHERE id = ?", (player_id,))
    row    = c.fetchone()
    kills  = row["kills"]
    deaths = row["deaths"]

    if events.get("blood_moon"):
        return "the moon runs red. i have not seen this in many cycles."
    elif events.get("flood_omnya"):
        return "the waters rise. some paths are lost to us now."
    elif events.get("monster_rush"):
        return "they come in waves. do not let them surround you."
    elif events.get("solar_eclipse"):
        return "the light dims. The Indexer's power swells in the dark."
    elif events.get("fateful_day"):
        return "the markets overflow today. rare things surface rarely."
    elif kills == 0:
        return "you have not yet drawn blood. the index waits."
    elif deaths > kills:
        return f"{deaths} deaths. {kills} kills. the corruption is winning."
    elif kills >= 50:
        return f"{kills} processes terminated. the schema remembers."
    elif kills >= 20:
        return f"you have cut a path through {kills} enemies. keep going."
    elif deaths == 0:
        return f"{kills} kills. no deaths. impressive uptime."
    else:
        return f"{kills} kills. {deaths} deaths. the balance shifts."


# ------------------------------------------------------------------ #
#  CONSTANTS FOR main.py                                             #
# ------------------------------------------------------------------ #

ENCOUNTER_NAME = {
    -1: "START",
    0:  "TRANSACTION",
    1:  "QUERY",
    2:  "STORED_PROCEDURE",
    3:  "DEADLOCK",
    4:  "CONSTRAINT",
    5:  "OVERFLOW",
    6:  "REST",
}

BRANCH_LABEL = ["←", "↑", "→"]

EVENT_LABELS = {
    "blood_moon":    "BLOOD MOON    — enemies strike with doubled power",
    "solar_eclipse": "SOLAR ECLIPSE — The Indexer's crit surges",
    "flood_omnya":   "FLOOD OF OMNYA — some paths are inaccessible",
    "monster_rush":  "MONSTER RUSH  — enemies attack twice per round",
    "fateful_day":   "FATEFUL DAY   — rare loot floods the markets",
}

INTRO_LINES = [
    "in the beginning, there was data.",
    "vast. formless. unindexed.",
    "then came the Schema.",
    "it imposed order. named the tables. defined the keys.",
    "for a time, the world was consistent.",
    "then the corruption spread.",
    "null pointers. deadlock wraiths. cascading failures.",
    "the OVERFLOW bosses seized the deep layers.",
    "you are a process. freshly spawned. assigned a class.",
    "your task: traverse the index. clear the corruption.",
    "restore the Schema.",
]
