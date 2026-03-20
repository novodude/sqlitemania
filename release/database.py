import sqlite3 as sql
import json
import random
from enum import Enum

DB_PATH = "game_data.db"

conn = sql.connect(DB_PATH)
conn.row_factory = sql.Row
c = conn.cursor()

class BonusType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    POTION = "potion"
    ENV = "env"

def init_db():
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            blood_moon INTEGER DEFAULT 0,
            solar_eclipse INTEGER DEFAULT 0,
            flood_omnya INTEGER DEFAULT 0,
            monster_rush INTEGER DEFAULT 0,
            fateful_day INTEGER DEFAULT 0,
            encounters_since_reset INTEGER DEFAULT 0
        )
    """)

    # Add encounters_since_reset column if it doesn't exist (migration)
    try:
        c.execute("ALTER TABLE events ADD COLUMN encounters_since_reset INTEGER DEFAULT 0")
    except sql.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS class (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            base_hp INTEGER NOT NULL,
            base_hit INTEGER NOT NULL,
            base_crit INTEGER NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS status_effects (
            player_id  INTEGER NOT NULL,
            effect     TEXT NOT NULL,   -- 'DEADLOCK' | 'CORRUPTION' | 'SEGFAULT'
            duration   INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            class_id INTEGER NOT NULL,
            equipped_armor TEXT,
            equipped_weapon TEXT,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES class(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER PRIMARY KEY,
            base_hp INTEGER NOT NULL,
            bonus_hp INTEGER DEFAULT 0,
            max_hp INTEGER NOT NULL,
            current_hp INTEGER NOT NULL,
            bytes INTEGER DEFAULT 50,
            base_hit INTEGER NOT NULL,
            bonus_hit INTEGER DEFAULT 0,
            base_crit INTEGER NOT NULL,
            bonus_crit INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            player_id INTEGER,
            item TEXT NOT NULL,
            amount INTEGER DEFAULT 1,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS potions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            potion_type TEXT NOT NULL,
            heal_amount INTEGER DEFAULT 0,
            bonus_hit   INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            defense_flat INTEGER DEFAULT 0,
            duration    INTEGER DEFAULT 1,
            price       INTEGER DEFAULT 15
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            base_hp INTEGER DEFAULT 80,
            max_hp INTEGER DEFAULT 80,
            base_hit INTEGER DEFAULT 10,
            weapon TEXT,
            experience_drop INTEGER,
            is_dead BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weapons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_type TEXT NOT NULL,
            hit_mult INTEGER NOT NULL,
            bonus_hp INTEGER DEFAULT 0,
            bonus_hit INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            found BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS armors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_type TEXT NOT NULL,
            hit_mult INTEGER NOT NULL,
            bonus_hp INTEGER DEFAULT 0,
            bonus_hit INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            found BOOLEAN DEFAULT 0
        )
    """)

    # Named boss loot — unique items dropped only by OVERFLOW bosses
    c.execute("""
        CREATE TABLE IF NOT EXISTS boss_loot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boss_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,  -- 'weapon' or 'armor'
            class_type TEXT NOT NULL,
            hit_mult INTEGER DEFAULT 20,
            bonus_hp INTEGER DEFAULT 0,
            bonus_hit INTEGER DEFAULT 0,
            bonus_crit INTEGER DEFAULT 0,
            claimed BOOLEAN DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TRIGGER IF NOT EXISTS weapon_limit
        BEFORE INSERT ON weapons
        WHEN (SELECT COUNT(*) FROM weapons) >= 100
        BEGIN
            SELECT RAISE(IGNORE);
        END;
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id   INTEGER NOT NULL,
            seed        INTEGER NOT NULL,
            level_range INTEGER NOT NULL,
            kills       INTEGER DEFAULT 0,
            bytes_earned INTEGER DEFAULT 0,
            nodes_cleared INTEGER DEFAULT 0,
            outcome     TEXT,                  -- 'win' | 'lose' | 'fled'
            ended_at    TIMESTAMP,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

    # Persists the exact stock a shop was rolled with, so revisits show the same items
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_stock (
            path_id    INTEGER NOT NULL,
            slot       INTEGER NOT NULL,       -- ordering index
            item_type  TEXT    NOT NULL,       -- 'weapon', 'armor', 'potion'
            item_name  TEXT    NOT NULL,
            PRIMARY KEY (path_id, slot),
            FOREIGN KEY (path_id) REFERENCES path(id)
        )
    """)

    try:
        c.execute("ALTER TABLE runs RENAME COLUMN bytes_earned TO bytes_earned")
    except sql.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE player_stats RENAME COLUMN bytes TO bytes")
    except sql.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE players ADD COLUMN overflow_kills INTEGER DEFAULT 0")
    except sql.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE players ADD COLUMN current_run_id  INTEGER REFERENCES runs(id)")
    except sql.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE players ADD COLUMN current_path_id INTEGER REFERENCES path(id)")
    except sql.OperationalError:
        pass
    # Migrate existing runs tables that predate the stat columns
    for col, default in [("kills", "0"), ("bytes_earned", "0"), ("nodes_cleared", "0"),
                         ("outcome", "NULL"), ("ended_at", "NULL")]:
        try:
            c.execute(f"ALTER TABLE runs ADD COLUMN {col} {'TEXT' if col in ('outcome','ended_at') else 'INTEGER DEFAULT 0'}")
        except sql.OperationalError:
            pass

    c.execute("""
    CREATE TABLE IF NOT EXISTS map(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        encounter_type INTEGER NOT NULL,
        level_range INTEGER NOT NULL,
        finished BOOLEAN DEFAULT 0
    )
    """)

    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO events DEFAULT VALUES")

    try:
        c.execute("ALTER TABLE weapons ADD COLUMN element TEXT DEFAULT 'QUERY'")
    except sql.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE armors ADD COLUMN element TEXT DEFAULT 'QUERY'")
    except sql.OperationalError:
        pass

    conn.commit()
    _init_boss_loot()


def _init_boss_loot():
    """Seed the boss_loot table with unique named items for each boss."""
    c.execute("SELECT COUNT(*) FROM boss_loot")
    if c.fetchone()[0] > 0:
        return

    loot = [
        # boss_name,         item_name,                    type,     class,          mult  hp    hit  wis
        ("The Warlord",   "Warlord's Cleave",             "weapon", "The Executor",  25,  600,  80,   0),
        ("The Warlord",   "Siege Plate",                  "armor",  "The Executor",  20,  700,  50,   0),
        ("The Tyrant",    "Tyrant's Decree",              "weapon", "The Indexer",   18,   80,  30, 100),
        ("The Tyrant",    "Nullchain Cowl",               "armor",  "The Trigger",   22,  250,  70,  40),
        ("The Behemoth",  "Behemoth Crasher",             "weapon", "The Executor",  28,  800,  90,   0),
        ("The Behemoth",  "Plated Colossus Shell",        "armor",  "The Executor",  24,  900,  60,   0),
        ("The Archmage",  "Staff of Final Queries",       "weapon", "The Indexer",   15,   50,  20, 140),
        ("The Archmage",  "Archmage's Inscription Robe",  "armor",  "The Indexer",   12,  100,  15, 120),
        ("The Overseer",  "Overseer's Verdict",           "weapon", "The Trigger",   26,  300,  95,  50),
        ("The Overseer",  "All-Seeing Carapace",          "armor",  "The Trigger",   20,  400,  80,  60),
    ]

    c.executemany("""
        INSERT INTO boss_loot (boss_name, item_name, item_type, class_type,
                               hit_mult, bonus_hp, bonus_hit, bonus_crit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, loot)
    conn.commit()


def drop_boss_loot(player_id: int, boss_type: str):
    """Grant the unique loot for a boss if it hasn't been claimed yet.
    Returns a list of (item_name, item_type) that were dropped, or [].
    """
    # Boss type string is "OVERFLOW — The Warlord" etc.
    boss_name = boss_type.replace("OVERFLOW — ", "").strip()

    c.execute("""
        SELECT id, item_name, item_type, class_type, hit_mult,
               bonus_hp, bonus_hit, bonus_crit
        FROM boss_loot
        WHERE boss_name = ? AND claimed = 0
    """, (boss_name,))
    rows = c.fetchall()

    dropped = []
    for row in rows:
        # Insert into the appropriate gear table so it can be equipped
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
                    (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, found)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (row["item_name"], row["class_type"], row["hit_mult"],
                  row["bonus_hp"], row["bonus_hit"], row["bonus_crit"]))

        add_item(player_id, row["item_name"], 1)
        c.execute("UPDATE boss_loot SET claimed = 1 WHERE id = ?", (row["id"],))
        dropped.append((row["item_name"], row["item_type"]))

    conn.commit()
    return dropped


def init_classes():
    classes = [
        ("The Executor", 120, 15, 5),
        ("The Indexer",  70,  5, 20),
        ("The Trigger",  90, 12, 10),
    ]
    c.executemany("""
        INSERT OR IGNORE INTO class (name, base_hp, base_hit, base_crit)
        VALUES (?, ?, ?, ?)
    """, classes)
    conn.commit()


def generate_gear(player_level: int, gear_type: str = "random"):
    """Generate a single weapon or armor scaled to player_level."""
    if gear_type == "random":
        gear_type = random.choice(["weapon", "armor"])

    level_bonus = player_level - 1  # scales linearly with level

    with open("weapon_name.json" if gear_type == "weapon" else "armor_name.json", "r") as f:
        data = json.load(f)

    if gear_type == "weapon":
        name = f"{random.choice(data['first_name'])} {random.choice(data['second_name'])}"
    else:
        name = random.choice(data)

    class_type = random.choice(["The Executor", "The Trigger", "The Indexer"])

    if class_type == "The Executor":
        bonus_hp    = random.randint(300, 500)  + level_bonus * 20
        bonus_hit   = random.randint(20,  60)   + level_bonus * 3
        bonus_crit  = random.randint(0,   10)   + level_bonus
        hit_mult    = random.randint(1,   30)
    elif class_type == "The Trigger":
        bonus_hp    = random.randint(100, 250)  + level_bonus * 12
        bonus_hit   = random.randint(30,  50)   + level_bonus * 4
        bonus_crit  = random.randint(20,  30)   + level_bonus * 2
        hit_mult    = random.randint(1,   30)
    else:  # The Indexer
        bonus_hp    = random.randint(20,  100)  + level_bonus * 5
        bonus_hit   = random.randint(5,   20)   + level_bonus * 2
        bonus_crit  = random.randint(30,  60)   + level_bonus * 4
        hit_mult    = random.randint(1,   30)

    table = "weapons" if gear_type == "weapon" else "armors"
    element = random.choice(["QUERY", "LOCK", "OVERFLOW", "NULL"])
    c.execute(f"""
        INSERT INTO {table} (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, element, found)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_crit, element))
    conn.commit()
    return c.lastrowid, name, gear_type

def loot_init():
    c.execute("SELECT COUNT(*) FROM weapons")
    if c.fetchone()[0] == 0:
        for _ in range(20):
            generate_gear(player_level=1, gear_type="weapon")
    c.execute("SELECT COUNT(*) FROM armors")
    if c.fetchone()[0] == 0:
        for _ in range(20):
            generate_gear(player_level=1, gear_type="armor")

def add_item(player_id: int, item: str, amount: int = 1):
    c.execute("""
        INSERT INTO inventory (player_id, item, amount)
        VALUES (?, ?, ?)
    """, (player_id, item, amount))


def remove_item(player_id: int, item: str):
    c.execute("""
        DELETE FROM inventory
        WHERE player_id = ? AND item = ?
    """, (player_id, item))


def starter_weapon(player_id: int):
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = c.fetchone()[0]

    c.execute("""
        SELECT id, name, hit_mult FROM weapons
        WHERE class_type = ? AND found = 0
    """, (class_name,))
    weapons = c.fetchall()
    if not weapons:
        return

    low_weapons = [w for w in weapons if w[2] <= 10]
    chosen = random.choice(low_weapons or weapons)
    c.execute("UPDATE weapons SET found = 1 WHERE id = ?", (chosen[0],))
    add_item(player_id, chosen[1], 1)


def starter_armor(player_id: int):
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = c.fetchone()[0]

    c.execute("""
        SELECT id, name, hit_mult FROM armors
        WHERE class_type = ? AND found = 0
    """, (class_name,))
    armors = c.fetchall()
    if not armors:
        return

    low_armor = [w for w in armors if w[2] <= 10]
    chosen = random.choice(low_armor or armors)
    c.execute("UPDATE armors SET found = 1 WHERE id = ?", (chosen[0],))
    add_item(player_id, chosen[1], 1)


def init_map():
    DISTRIBUTION = {
        0: 5, 1: 30, 2: 5, 3: 5, 4: 3, 5: 2, 6: 4
    }
    LOW_ADJ  = ["Cached", "Indexed", "Idle", "Dormant", "Deprecated"]
    MID_ADJ  = ["Corrupted", "Fragmented", "Recursive", "Locked", "Overloaded"]
    HIGH_ADJ = ["Null", "Truncated", "Cascading", "Unhandled", "Catastrophic"]
    CREATURES    = ["Processes", "Daemons", "Threads", "Queries", "Triggers", "Cursors"]
    BOSSES       = ["Warlord", "Overseer", "Tyrant", "Behemoth", "Archmage"]
    PLACES       = ["Schema", "Warehouse", "Cluster", "Replica", "Shard"]
    CAVE_TYPES   = ["Deadlock Chamber", "Rollback Depths", "Isolation Vault", "Constraint Hollow"]
    FOREST_TYPES = ["Cascade Wilds", "Foreign Key Tangle", "Trigger Thicket", "Index Sprawl"]
    REST_TYPES   = ["Checkpoint Node", "Savepoint Alcove", "Commit Cache", "Buffer Clearing"]

    def get_adjectives(lr):
        if lr <= 2: return LOW_ADJ
        elif lr <= 6: return MID_ADJ
        return HIGH_ADJ

    def generate_name(et, lr):
        adj = random.choice(get_adjectives(lr))
        if et == 0: return f"{adj} Traveling Merchant"
        if et == 1: return f"{adj} {random.choice(CREATURES)}"
        if et == 2: return f"{adj} {random.choice(PLACES)}"
        if et == 3: return f"{adj} {random.choice(CAVE_TYPES)}"
        if et == 4: return f"{adj} {random.choice(FOREST_TYPES)}"
        if et == 5: return f"{adj} {random.choice(BOSSES)}"
        if et == 6: return f"{adj} {random.choice(REST_TYPES)}"

    def generate_description(et, lr):
        mn, mx = lr * 10 + 1, (lr + 1) * 10
        if et == 0: return f"A TRANSACTION node. A merchant offering gear for adventurers level {mn}-{mx}."
        if et == 1: return f"A QUERY node. Hostile enemies scaled for fighters level {mn}-{mx}."
        if et == 2: return f"A STORED_PROCEDURE node. A dungeon with scripted traps and enemies level {mn}-{mx}."
        if et == 3: return f"A DEADLOCK node. A dark cave where two forces collide around level {mn}-{mx}."
        if et == 4: return f"A CONSTRAINT node. A forest where the world pushes back, level {mn}-{mx}."
        if et == 5: return f"An OVERFLOW node. A boss encounter for heroes level {mn}-{mx}."
        if et == 6: return f"A REST node. A quiet place to recover, level {mn}-{mx}."

    rows = []
    for level_range in range(10):
        for encounter_type, amount in DISTRIBUTION.items():
            for _ in range(amount):
                rows.append((
                    generate_name(encounter_type, level_range),
                    generate_description(encounter_type, level_range),
                    encounter_type, level_range, 0
                ))

    c.executemany("""
        INSERT INTO map (name, description, encounter_type, level_range, finished)
        VALUES (?, ?, ?, ?, ?)
    """, rows)
    conn.commit()


def init_run(player_id: int, custom_seed: int = None):
    import time
    seed = custom_seed if custom_seed is not None else int(time.time() * 1000) % (2**31)

    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()[0]
    level_range = min((player_level - 1) // 10, 9)

    c.execute("""
        INSERT INTO runs (player_id, seed, level_range) VALUES (?, ?, ?)
    """, (player_id, seed, level_range))
    run_id = c.lastrowid
    conn.commit()

    c.execute("UPDATE players SET current_run_id = ? WHERE id = ?", (run_id, player_id))
    conn.commit()

    root_id = generate_path(run_id, level_range, seed)
    recommended_min = level_range * 10 + 1

    if player_level < recommended_min:
        print(f"  WARNING: this run is tuned for level {recommended_min}+.")
        print(f"  you are level {player_level}. proceed with caution.")
        print()
    return run_id, root_id, seed


def record_run_kill(run_id: int):
    c.execute("UPDATE runs SET kills = kills + 1 WHERE id = ?", (run_id,))
    conn.commit()


def record_run_bytes(run_id: int, amount: int):
    c.execute("UPDATE runs SET bytes_earned = bytes_earned + ? WHERE id = ?", (amount, run_id))
    conn.commit()


def record_run_node(run_id: int):
    c.execute("UPDATE runs SET nodes_cleared = nodes_cleared + 1 WHERE id = ?", (run_id,))
    conn.commit()


def finish_run(run_id: int, outcome: str):
    """outcome: 'win' | 'lose' | 'fled'"""
    c.execute("""
        UPDATE runs SET outcome = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (outcome, run_id))
    conn.commit()


def get_run_stats(run_id: int):
    c.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    return c.fetchone()


def generate_path(run_id: int, level_range: int, seed: int):
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
        weights = [WEIGHTS.get(r["encounter_type"], 1) for r in (candidates or pool)]
        return rng.choices(candidates or pool, weights=weights, k=1)[0]

    def insert_node(parent_id, depth, branch, row, is_boss=False):
        enc_type = 5 if is_boss else row["encounter_type"]
        c.execute("""
            INSERT INTO path
                (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, parent_id, depth, branch, row["name"], row["description"], enc_type, level_range))
        return c.lastrowid

    # ROOT
    c.execute("""
        INSERT INTO path (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
        VALUES (?, NULL, 0, 1, 'START', 'The journey begins here.', -1, ?)
    """, (run_id, level_range))
    root_id = c.lastrowid

    # DEPTH 1 — always includes one shop, rest are random
    shop_candidates = [r for r in pool if r["encounter_type"] == 0]
    depth1_branches = sorted(rng.sample([0, 1, 2], rng.randint(2, 3)))
    depth1_ids = []
    for i, branch in enumerate(depth1_branches):
        row = rng.choice(shop_candidates or pool) if i == 0 else weighted_pick(exclude_types=(5,))
        depth1_ids.append((insert_node(root_id, 1, branch, row), branch))

    # DEPTHS 2–3 — each parent spawns 1-3 children
    MIDDLE_DEPTHS = [2, 3]
    prev_ids = depth1_ids
    for depth in MIDDLE_DEPTHS:
        next_ids = []
        for parent_id, _ in prev_ids:
            branches = sorted(rng.sample([0, 1, 2], rng.randint(1, 3)))
            for branch in branches:
                row = weighted_pick(exclude_types=(5,))
                next_ids.append((insert_node(parent_id, depth, branch, row), branch))
        prev_ids = next_ids

    # DEPTH 4 — boss node for every leaf
    for parent_id, _ in prev_ids:
        insert_node(parent_id, 4, 1, rng.choice(boss_pool), is_boss=True)

    conn.commit()
    return root_id


def get_path_node(path_id: int):
    c.execute("SELECT * FROM path WHERE id = ?", (path_id,))
    return c.fetchone()


def get_path_children(path_id: int):
    c.execute("""
        SELECT * FROM path WHERE parent_id = ? ORDER BY branch ASC
    """, (path_id,))
    return c.fetchall()


def move_to_node(player_id: int, path_id: int):
    c.execute("UPDATE players SET current_path_id = ? WHERE id = ?", (path_id, player_id))
    conn.commit()


def finish_node(path_id: int):
    c.execute("UPDATE path SET finished = 1 WHERE id = ?", (path_id,))
    conn.commit()


def register_shop_visit(player_id: int, path_id: int):
    c.execute("""
        SELECT 1 FROM visited_shops WHERE player_id = ? AND path_id = ?
    """, (player_id, path_id))
    if not c.fetchone():
        c.execute("DELETE FROM visited_shops")
        c.execute("""
            INSERT INTO visited_shops (player_id, path_id) VALUES (?, ?)
        """, (player_id, path_id))
        conn.commit()


def save_shop_stock(path_id: int, stock: list):
    """Persist a shop's rolled stock so revisits see the same items.

    stock is a list of (item_type, item_name) tuples where item_type is
    'weapon', 'armor', or 'potion'.
    """
    c.execute("SELECT COUNT(*) FROM shop_stock WHERE path_id = ?", (path_id,))
    if c.fetchone()[0] > 0:
        return  # already saved, don't overwrite
    rows = [(path_id, i, t, n) for i, (t, n) in enumerate(stock)]
    c.executemany("""
        INSERT OR IGNORE INTO shop_stock (path_id, slot, item_type, item_name)
        VALUES (?, ?, ?, ?)
    """, rows)
    conn.commit()


def load_shop_stock(path_id: int):
    """Return saved stock for a shop, or None if never saved."""
    c.execute("""
        SELECT item_type, item_name FROM shop_stock
        WHERE path_id = ? ORDER BY slot ASC
    """, (path_id,))
    rows = c.fetchall()
    return rows if rows else None


def get_visited_shops(player_id: int):
    c.execute("""
        SELECT p.* FROM path p
        JOIN visited_shops v ON v.path_id = p.id
        WHERE v.player_id = ?
    """, (player_id,))
    return c.fetchall()


def init_player(username: str, class_name: str):
    c.execute("""
        SELECT id, base_hp, base_hit, base_crit FROM class WHERE name = ?
    """, (class_name,))
    class_data = c.fetchone()
    if not class_data:
        raise ValueError(f"Class '{class_name}' does not exist")

    class_id, hp, hit, crit = class_data
    c.execute("""
        INSERT INTO players (username, class_id) VALUES (?, ?)
    """, (username, class_id))
    player_id = c.lastrowid

    c.execute("""
        INSERT INTO player_stats (player_id, base_hp, max_hp, current_hp, base_hit, base_crit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, hp, hp, hp, hit, crit))

    starter_weapon(player_id)
    starter_armor(player_id)

    # Auto-equip starter gear
    c.execute("SELECT item FROM inventory WHERE player_id = ? LIMIT 1 OFFSET 0", (player_id,))
    w = c.fetchone()
    c.execute("SELECT item FROM inventory WHERE player_id = ? LIMIT 1 OFFSET 1", (player_id,))
    a = c.fetchone()

    if w:
        c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (w["item"], player_id))
    if a:
        c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (a["item"], player_id))

    conn.commit()

    # Apply gear bonuses so max_hp and stats reflect equipped items
    if w:
        bonus_calc(BonusType.WEAPON, player_id)
    if a:
        bonus_calc(BonusType.ARMOR, player_id)

    # Set current_hp to full after bonuses are applied
    c.execute("""
        UPDATE player_stats SET current_hp = max_hp WHERE player_id = ?
    """, (player_id,))
    conn.commit()
    return player_id


def bonus_calc(bonus_type: BonusType, player_id: int, remove: bool = False):
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    user_class_type = c.fetchone()[0]
    multiplier = -1 if remove else 1

    if bonus_type is BonusType.WEAPON:
        c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
        weapon = c.fetchone()[0]
        if weapon is None:
            return
        c.execute("SELECT * FROM weapons WHERE name = ?", (weapon,))
        weapon_data = c.fetchone()
        if weapon_data is None:
            return

        hit_mult     = weapon_data["hit_mult"]
        bonus_hp     = weapon_data["bonus_hp"]     * multiplier
        bonus_hit    = weapon_data["bonus_hit"]    * multiplier
        bonus_crit = weapon_data["bonus_crit"] * multiplier

        if weapon_data["class_type"] == user_class_type:
            if user_class_type == "The Executor":
                bonus_hp *= 2
            elif user_class_type == "The Indexer":
                bonus_crit *= 2
            elif user_class_type == "The Trigger":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)

        if not remove:
            c.execute("UPDATE player_stats SET base_hit = base_hit * ? WHERE player_id = ?", (hit_mult, player_id))
        else:
            c.execute("UPDATE player_stats SET base_hit = base_hit / ? WHERE player_id = ?", (hit_mult, player_id))

        c.execute("""
            UPDATE player_stats
            SET bonus_hp = bonus_hp + ?, bonus_hit = bonus_hit + ?, bonus_crit = bonus_crit + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_crit, player_id))
        c.execute("UPDATE player_stats SET max_hp = base_hp + bonus_hp WHERE player_id = ?", (player_id,))

    elif bonus_type is BonusType.ARMOR:
        c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
        armor = c.fetchone()[0]
        if armor is None:
            return
        c.execute("SELECT * FROM armors WHERE name = ?", (armor,))
        armor_data = c.fetchone()
        if armor_data is None:
            return

        hit_mult     = armor_data["hit_mult"]
        bonus_hp     = armor_data["bonus_hp"]     * multiplier
        bonus_hit    = armor_data["bonus_hit"]    * multiplier
        bonus_crit = armor_data["bonus_crit"] * multiplier

        if armor_data["class_type"] == user_class_type:
            if user_class_type == "The Executor":
                bonus_hp *= 2
            elif user_class_type == "The Indexer":
                bonus_crit *= 2
            elif user_class_type == "The Trigger":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)

        if not remove:
            c.execute("UPDATE player_stats SET base_hit = base_hit * ? WHERE player_id = ?", (hit_mult, player_id))
        else:
            c.execute("UPDATE player_stats SET base_hit = base_hit / ? WHERE player_id = ?", (hit_mult, player_id))

        c.execute("""
            UPDATE player_stats
            SET bonus_hp = bonus_hp + ?, bonus_hit = bonus_hit + ?, bonus_crit = bonus_crit + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_crit, player_id))
        c.execute("UPDATE player_stats SET max_hp = base_hp + bonus_hp WHERE player_id = ?", (player_id,))

    conn.commit()

ENEMY_ELEMENT = {
    "Corrupted Index": "LOCK",
    "Null Pointer":    "NULL",
    "Stack Overflow":  "OVERFLOW",
    "Deadlock Wraith": "LOCK",
    "Zombie Process":  "NULL",
}

ELEMENT_WEAKNESS = {
    "QUERY":    "LOCK",      # QUERY beats LOCK
    "LOCK":     "OVERFLOW",  # LOCK beats OVERFLOW
    "OVERFLOW": "NULL",      # OVERFLOW beats NULL
    "NULL":     "QUERY",     # NULL beats QUERY
}



def get_potion_pool():
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
        ("Minor Barrier",      "BARRIER",           0,    0,   0,  200,   3,   15),
        ("Barrier",            "BARRIER",           0,    0,   0,  460,   3,   30),
        ("Major Barrier",      "BARRIER",           0,    0,   0,  960,   5,   55),
        ("Mending Surge",      "RESTORE_SURGE",    20,   12,   0,   0,   3,   35),
        ("Vital Surge",        "RESTORE_SURGE",    40,   25,   0,   0,   3,   65),
        ("Mending Clarity",    "RESTORE_CLARITY",  20,    0,  12,   0,   3,   35),
        ("Vital Clarity",      "RESTORE_CLARITY",  40,    0,  25,   0,   3,   65),
        ("Mind and Blade",     "SURGE_CLARITY",     0,   15,  15,   0,   3,   50),
        ("Grand Elixir",       "SURGE_CLARITY",     0,   30,  30,   0,   5,   90),
    ]


def apply_potion(player_id: int, potion_name: str):
    pool = {p[0]: p for p in get_potion_pool()}
    if potion_name not in pool:
        return {}

    _, ptype, heal_pct, bhit, bcrit, bdef, dur, _ = pool[potion_name]
    result = {}

    if heal_pct > 0:
        c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
        max_hp = c.fetchone()["max_hp"]
        heal = max(1, int(max_hp * heal_pct / 100))
        c.execute("""
            UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?
        """, (heal, player_id))
        result["heal"] = heal

    if bhit > 0:
        c.execute("SELECT base_hit FROM player_stats WHERE player_id = ?", (player_id,))
        base_hit = c.fetchone()["base_hit"]
        gain = max(1, int(base_hit * bhit / 100))
        c.execute("UPDATE player_stats SET bonus_hit = bonus_hit + ? WHERE player_id = ?", (gain, player_id))
        result["bonus_hit"] = gain

    if bcrit > 0:
        c.execute("SELECT base_crit FROM player_stats WHERE player_id = ?", (player_id,))
        base_crit = c.fetchone()["base_crit"]
        crit = max(1, int(base_crit * bcrit / 100))
        c.execute("UPDATE player_stats SET bonus_crit = bonus_crit + ? WHERE player_id = ?", (crit, player_id))
        result["bonus_crit"] = crit

    if bdef > 0:
        result["defense"] = bdef

    conn.commit()
    return result


def enemy_drop_potion(player_id: int):
    if random.random() > 0.35:
        return None
    pool = get_potion_pool()
    weights = [1 / (p[7] + 1) * 100 for p in pool]
    chosen = random.choices(pool, weights=weights, k=1)[0]
    add_item(player_id, chosen[0], 1)
    return chosen[0]


ENEMY_PROFILES = {
    "Corrupted Index": {"hp_mult": 1.2, "hit_mult": 0.8, "xp_mult": 1.0},  # tanky, slow
    "Null Pointer":    {"hp_mult": 0.7, "hit_mult": 1.4, "xp_mult": 1.1},  # glass cannon
    "Stack Overflow":  {"hp_mult": 1.0, "hit_mult": 1.2, "xp_mult": 1.2},  # aggressive
    "Deadlock Wraith": {"hp_mult": 0.9, "hit_mult": 0.9, "xp_mult": 0.9},  # balanced, low reward
    "Zombie Process":  {"hp_mult": 1.5, "hit_mult": 0.6, "xp_mult": 0.8},  # very tanky, weak hits
}

BASE_ENEMY_HP  = 60   # HP at level 1 before profile multiplier
BASE_ENEMY_HIT = 10   # hit at level 1 before profile multiplier
HP_PER_LEVEL   = 15
HIT_PER_LEVEL  = 3

def generate_enemy(player_id: int, is_boss: bool = False):
    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()["level"]

    enemy_type = random.choice(list(ENEMY_PROFILES.keys()))
    profile    = ENEMY_PROFILES[enemy_type]

    hp_variance  = random.uniform(0.88, 1.12)
    hit_variance = random.uniform(0.88, 1.12)

    base_hp  = max(40, int((BASE_ENEMY_HP  + HP_PER_LEVEL  * (player_level - 1)) * profile["hp_mult"]  * hp_variance))
    base_hit = max(8,  int((BASE_ENEMY_HIT + HIT_PER_LEVEL * (player_level - 1)) * profile["hit_mult"] * hit_variance))
    experience_drop = int((20 + player_level * 5 + random.randint(-5, 5)) * profile["xp_mult"])

    if is_boss:
        base_hp  = int(base_hp  * 3.5)
        base_hit = int(base_hit * 1.8)
        experience_drop *= 5
        enemy_type = "OVERFLOW — " + random.choice(["The Warlord", "The Tyrant", "The Behemoth", "The Archmage", "The Overseer"])

    c.execute("""
        INSERT INTO enemies (type, base_hp, max_hp, base_hit, experience_drop) VALUES (?, ?, ?, ?, ?)
    """, (enemy_type, base_hp, base_hp, base_hit, experience_drop))
    conn.commit()
    return c.lastrowid


def enemy_attack(player_id: int, enemy_id: int):
    damage_to_enemy, damage_to_player = calculate_damage(player_id, enemy_id)
    c.execute("UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
              (damage_to_player, player_id))
    c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?",
              (damage_to_enemy, enemy_id))
    conn.commit()


def check_combat_outcome(player_id: int, enemy_id: int):
    c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    player_hp = c.fetchone()[0]
    c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hp = c.fetchone()[0]
    if player_hp <= 0 and enemy_hp <= 0: return "draw"
    elif player_hp <= 0: return "enemy_win"
    elif enemy_hp <= 0: return "player_win"
    return "ongoing"


def calculate_damage(player_id: int, enemy_id: int):
    c.execute("SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,))
    player_stats = c.fetchone()
    player_hit   = player_stats["base_hit"] + player_stats["bonus_hit"]
    c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hit = c.fetchone()[0]
    damage_to_enemy  = max(0, player_hit - random.randint(0, 5))
    damage_to_player = max(0, enemy_hit  - random.randint(0, 5))
    return damage_to_enemy, damage_to_player


def reconnect():
    global conn, c
    conn.close()
    conn = sql.connect("game_data.db")
    conn.row_factory = sql.Row
    c = conn.cursor()


def experience_needed_for_next_level(current_level: int):
    if current_level < 1:
        return 100
    return int(100 * (1.4 ** (current_level - 1)))


def level_up(player_id: int):
    c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    current_level      = row[0]
    current_experience = row[1]
    new_level          = current_level + 1

    hp_increase      = 20
    hit_increase     = 5
    crit_increase  = 3

    if current_experience < experience_needed_for_next_level(current_level):
        raise ValueError("Not enough experience to level up")

    c.execute("UPDATE players SET experience = experience - ? WHERE id = ?",
              (experience_needed_for_next_level(current_level), player_id))
    c.execute("UPDATE players SET level = ? WHERE id = ?", (new_level, player_id))
    c.execute("""
        UPDATE player_stats
        SET base_hp      = base_hp      + ?,
            max_hp       = max_hp       + ?,
            current_hp   = MIN(current_hp + ?, max_hp + ?),
            base_hit     = base_hit     + ?,
            base_crit  = base_crit  + ?
        WHERE player_id = ?
    """, (hp_increase, hp_increase, hp_increase, hp_increase,
          hit_increase, crit_increase, player_id))
    conn.commit()
    print(f"\nlevel up! ({current_level} -> {new_level})")


# ------------------------------------------------------------------ #
#  EVENTS — CONSTRAINT node logic                                      #
# ------------------------------------------------------------------ #

# How many combat encounters before all active events auto-reset
EVENT_EXPIRY_ENCOUNTERS = 10

CONSTRAINT_EVENTS = [
    ("blood_moon",    "BLOOD MOON",    "All enemies strike with doubled force."),
    ("solar_eclipse", "SOLAR ECLIPSE", "The Indexer's crit surges to new heights."),
    ("flood_omnya",   "FLOOD OF OMNYA","Certain paths are swallowed by rising waters."),
    ("monster_rush",  "MONSTER RUSH",  "Each enemy strikes an additional time."),
    ("fateful_day",   "FATEFUL DAY",   "Rare treasures surface in every market."),
]


def trigger_constraint_event(events: dict) -> tuple[str, str] | None:
    """Fire a random world event from a CONSTRAINT node.
    Returns (event_key, event_name) that was activated, or None if nothing new fires.
    Inactive events are weighted; an already-active event can still be re-rolled (no-op).
    """
    inactive = [e for e in CONSTRAINT_EVENTS if not events.get(e[0])]
    if not inactive:
        return None  # all events already active

    key, name, _ = random.choice(inactive)
    c.execute(f"UPDATE events SET {key} = 1")
    conn.commit()
    return key, name


def tick_event_counter() -> bool:
    """Increment the encounter counter and reset all events if the threshold is reached.
    Returns True if events were reset this tick.
    """
    c.execute("UPDATE events SET encounters_since_reset = encounters_since_reset + 1")
    conn.commit()
    c.execute("SELECT encounters_since_reset FROM events LIMIT 1")
    count = c.fetchone()[0]
    if count >= EVENT_EXPIRY_ENCOUNTERS:
        reset_events()
        return True
    return False


def reset_events():
    """Clear all active event flags and reset the counter."""
    c.execute("""
        UPDATE events
        SET blood_moon = 0, solar_eclipse = 0, flood_omnya = 0,
            monster_rush = 0, fateful_day = 0, encounters_since_reset = 0
    """)
    conn.commit()


def apply_event_combat_modifiers(enemy_id: int, events: dict):
    """Apply CONSTRAINT event modifiers to a freshly spawned enemy.
    Called once when the enemy is generated, before combat begins.
    """
    if events.get("blood_moon"):
        c.execute("UPDATE enemies SET base_hit = base_hit * 2 WHERE id = ?", (enemy_id,))
        conn.commit()

    if events.get("monster_rush"):
        # monster_rush handled in enemy_turn; nothing to bake into the row
        pass

def apply_status(player_id: int, effect: str, duration: int):
    c.execute("""
        INSERT INTO status_effects (player_id, effect, duration) VALUES (?, ?, ?)
    """, (player_id, effect, duration))
    conn.commit()

def get_statuses(player_id: int):
    c.execute("SELECT effect, duration FROM status_effects WHERE player_id = ?", (player_id,))
    return c.fetchall()

def tick_statuses(player_id: int):
    """Decrement durations, remove expired, apply CORRUPTION DoT. Returns log lines."""
    c.execute("SELECT rowid, effect, duration FROM status_effects WHERE player_id = ?", (player_id,))
    rows = c.fetchall()
    log = []
    for row in rows:
        if row["effect"] == "CORRUPTION":
            c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
            max_hp = c.fetchone()["max_hp"]
            dot = max(1, int(max_hp * 0.05))
            c.execute("UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
                      (dot, player_id))
            log.append(f"CORRUPTION burns you for {dot} damage.")
        if row["effect"] == "SEGFAULT":
            stat = random.choice(["bonus_hit", "bonus_crit"])
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

def is_first_launch() -> bool:
    c.execute("SELECT value FROM meta WHERE key = 'intro_shown'")
    return c.fetchone() is None

def mark_intro_shown():
    c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('intro_shown', '1')")
    conn.commit()


def init_node_flavour():
    c.execute("SELECT COUNT(*) FROM node_flavour")
    if c.fetchone()[0] > 0:
        return
    lines = [
        # TRANSACTION (0)
        (0, "the merchant's eyes flicker like a cursor awaiting input."),
        (0, "goods change hands. the economy persists."),
        (0, "a traveling vendor. their wares update each visit."),
        # QUERY (1)
        (1, "something has detected your process. it does not yield."),
        (1, "hostile threads converge. execution is contested."),
        (1, "a query fires. the answer is violence."),
        # STORED_PROCEDURE (2)
        (2, "the dungeon runs a fixed routine. each room, scripted."),
        (2, "these walls remember every traveler. none have changed them."),
        (2, "a procedure locked in place long before you arrived."),
        # DEADLOCK (3)
        (3, "two forces hold each other in permanent contention."),
        (3, "neither will release. neither can advance. you are the variable."),
        (3, "a stalemate older than the current schema."),
        # CONSTRAINT (4)
        (4, "the world enforces its rules here. violation is painful."),
        (4, "a foreign key tangle. the paths resist traversal."),
        (4, "something fundamental shifts as you enter."),
        # OVERFLOW (5)
        (5, "the air thickens. the logs show something massive."),
        (5, "an OVERFLOW event. the stack cannot contain what lives here."),
        (5, "this is where corrupted processes come to grow beyond bounds."),
        # REST (6)
        (6, "a savepoint. the system breathes."),
        (6, "rollback is possible here, if only for a moment."),
        (6, "the noise fades. your process stabilizes."),
    ]
    c.executemany("INSERT INTO node_flavour (encounter_type, line) VALUES (?, ?)", lines)
    conn.commit()

def get_node_flavour(encounter_type: int) -> str:
    c.execute("""
        SELECT line FROM node_flavour WHERE encounter_type = ?
        ORDER BY RANDOM() LIMIT 1
    """, (encounter_type,))
    row = c.fetchone()
    return row["line"] if row else ""

def record_overflow_kill(player_id: int) -> int:
    """Increment overflow kill count. Returns new total."""
    c.execute("UPDATE players SET overflow_kills = overflow_kills + 1 WHERE id = ?", (player_id,))
    conn.commit()
    c.execute("SELECT overflow_kills FROM players WHERE id = ?", (player_id,))
    return c.fetchone()["overflow_kills"]

OVERFLOW_BOSSES_TOTAL = 5  # Warlord, Tyrant, Behemoth, Archmage, Overseer
