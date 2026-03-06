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
            fateful_day INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS class (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            base_hp INTEGER NOT NULL,
            base_hit INTEGER NOT NULL,
            base_wisdom INTEGER NOT NULL
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
            gold INTEGER DEFAULT 50,
            base_hit INTEGER NOT NULL,
            bonus_hit INTEGER DEFAULT 0,
            base_wisdom INTEGER NOT NULL,
            bonus_wisdom INTEGER DEFAULT 0,
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
            bonus_wisdom INTEGER DEFAULT 0,
            defense_flat INTEGER DEFAULT 0,
            duration    INTEGER DEFAULT 1,
            price       INTEGER DEFAULT 15
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            base_hp INTEGER DEFAULT 80,
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
            bonus_wisdom INTEGER DEFAULT 0,
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
            bonus_wisdom INTEGER DEFAULT 0,
            found BOOLEAN DEFAULT 0
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

    # runs — one row per adventure session, holds the seed used to generate the path
    c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id   INTEGER NOT NULL,
            seed        INTEGER NOT NULL,
            level_range INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    """)

    # path — the actual tree the player walks through during a run.
    # Data is copied from the map pool at generation time, not FK'd,
    # so the tree is a self-contained snapshot tied to its seed.
    #
    # branch:  0 = <- (left)   1 = o (straight)   2 = -> (right)
    # depth 0 = root (start node, no encounter)
    # leaf nodes are always OVERFLOW (boss, encounter_type = 5)
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

    # visited_shops — TRANSACTION nodes the player can return to
    c.execute("""
        CREATE TABLE IF NOT EXISTS visited_shops (
            player_id INTEGER NOT NULL,
            path_id   INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (path_id)   REFERENCES path(id)
        )
    """)

    # Add run/path tracking columns to players if they don't exist yet
    try:
        c.execute("ALTER TABLE players ADD COLUMN current_run_id  INTEGER REFERENCES runs(id)")
    except sql.OperationalError:
        pass  # column already exists
    try:
        c.execute("ALTER TABLE players ADD COLUMN current_path_id INTEGER REFERENCES path(id)")
    except sql.OperationalError:
        pass

    # Encounter types stored in the map table:
    # 0 - TRANSACTION (shop)
    # 1 - QUERY       (combat)
    # 2 - STORED_PROCEDURE (dungeon)
    # 3 - DEADLOCK    (cave)
    # 4 - CONSTRAINT  (forest / events)
    # 5 - OVERFLOW    (boss)
    #
    # level_ranges:
    # 0 = level 1-10  ... 9 = level 91-100
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

    # Ensure a default events row exists
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO events DEFAULT VALUES")

    conn.commit()


def init_classes():
    # Class names are database operation archetypes
    classes = [
        ("The Executor", 120, 15, 5),   # Warrior archetype — brute force
        ("The Indexer",  70,  5, 20),   # Mage archetype   — precision and knowledge
        ("The Trigger",  90, 12, 10),   # Rogue archetype  — reacts instantly to events
    ]

    c.executemany("""
        INSERT OR IGNORE INTO class (name, base_hp, base_hit, base_wisdom)
        VALUES (?, ?, ?, ?)
    """, classes)

    conn.commit()


def loot_init():
    """Ensure the weapon and armor tables are populated with at least 100 entries each."""
    c.execute("SELECT COUNT(*) FROM weapons")
    count = c.fetchone()[0]
    if count < 100:
        for _ in range(100 - count):
            init_weapon()

    c.execute("SELECT COUNT(*) FROM armors")
    count = c.fetchone()[0]
    if count < 100:
        for _ in range(100 - count):
            init_armor()


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
    """Give the player a low-tier weapon matching their class."""
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]

    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = c.fetchone()[0]

    c.execute("""
        SELECT id, name, hit_mult
        FROM weapons
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
    """Give the player a low-tier armor matching their class."""
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]

    c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = c.fetchone()[0]

    c.execute("""
        SELECT id, name, hit_mult
        FROM armors
        WHERE class_type = ? AND found = 0
    """, (class_name,))
    armors = c.fetchall()

    if not armors:
        return

    low_armor = [w for w in armors if w[2] <= 10]
    chosen = random.choice(low_armor or armors)

    c.execute("UPDATE armors SET found = 1 WHERE id = ?", (chosen[0],))
    add_item(player_id, chosen[1], 1)


def init_weapon():
    """INSERT a randomly generated weapon row into the weapons table."""
    with open("weapon_name.json", "r") as w:
        data = json.load(w)

    name = f"{random.choice(data['first_name'])} {random.choice(data['second_name'])}"

    # Class type determines stat distribution
    class_type = random.choice(["The Executor", "The Trigger", "The Indexer"])

    if class_type == "The Executor":
        hit_mult     = random.randint(1, 30)
        bonus_hp     = random.randint(300, 500)
        bonus_hit    = random.randint(20, 60)
        bonus_wisdom = random.randint(0, 10)
    elif class_type == "The Trigger":
        hit_mult     = random.randint(1, 30)
        bonus_hp     = random.randint(100, 250)
        bonus_hit    = random.randint(30, 50)
        bonus_wisdom = random.randint(25, 25)
    else:  # The Indexer
        hit_mult     = random.randint(1, 30)
        bonus_hp     = random.randint(20, 100)
        bonus_hit    = random.randint(5, 20)
        bonus_wisdom = random.randint(30, 60)

    c.execute("""
        INSERT INTO weapons (
            name, class_type, hit_mult,
            bonus_hp, bonus_hit, bonus_wisdom
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_wisdom))

    conn.commit()
    return name


def init_armor():
    """INSERT a randomly generated armor row into the armors table."""
    with open("armor_name.json", "r") as w:
        data = json.load(w)

    name = random.choice(data)

    class_type = random.choice(["The Executor", "The Trigger", "The Indexer"])

    if class_type == "The Executor":
        hit_mult     = random.randint(1, 30)
        bonus_hp     = random.randint(300, 500)
        bonus_hit    = random.randint(20, 60)
        bonus_wisdom = 0
    elif class_type == "The Trigger":
        hit_mult     = random.randint(1, 30)
        bonus_hp     = random.randint(100, 250)
        bonus_hit    = random.randint(30, 50)
        bonus_wisdom = random.randint(25, 25)
    else:  # The Indexer
        hit_mult     = random.randint(1, 30)
        bonus_hp     = 10
        bonus_hit    = random.randint(5, 20)
        bonus_wisdom = random.randint(30, 60)

    c.execute("""
        INSERT INTO armors (
            name, class_type, hit_mult,
            bonus_hp, bonus_hit, bonus_wisdom
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, class_type, hit_mult, bonus_hp, bonus_hit, bonus_wisdom))

    conn.commit()
    return name


def init_map():
    """Procedurally INSERT 500 encounter nodes into the map table."""

    # How many of each encounter type per level range (total = 50)
    DISTRIBUTION = {
        0: 5,   # TRANSACTION (shop)
        1: 30,  # QUERY       (combat)
        2: 5,   # STORED_PROCEDURE (dungeon)
        3: 5,   # DEADLOCK    (cave)
        4: 3,   # CONSTRAINT  (forest)
        5: 2    # OVERFLOW    (boss)
    }

    LOW_ADJ  = ["Quiet", "Small", "Dusty", "Worn", "Faded"]
    MID_ADJ  = ["Savage", "Shadowed", "Ancient", "Ruthless", "Cursed"]
    HIGH_ADJ = ["Mythic", "Abyssal", "Cataclysmic", "Eternal", "Godslayer"]

    CREATURES   = ["Goblins", "Bandits", "Wolves", "Skeletons", "Cultists", "Knights"]
    BOSSES      = ["Warlord", "Overseer", "Tyrant", "Behemoth", "Archmage"]
    PLACES      = ["Ruins", "Sanctum", "Fortress", "Temple", "Stronghold"]
    CAVE_TYPES  = ["Crystal Cavern", "Molten Depths", "Frozen Hollow", "Echoing Cave"]
    FOREST_TYPES = ["Whispering Woods", "Twilight Grove", "Rotwood Forest", "Bloodleaf Wilds"]

    def get_adjectives(level_range):
        if level_range <= 2:
            return LOW_ADJ
        elif level_range <= 6:
            return MID_ADJ
        return HIGH_ADJ

    def generate_name(encounter_type, level_range):
        adj = random.choice(get_adjectives(level_range))
        if encounter_type == 0: return f"{adj} Traveling Merchant"
        if encounter_type == 1: return f"{adj} {random.choice(CREATURES)}"
        if encounter_type == 2: return f"{adj} {random.choice(PLACES)}"
        if encounter_type == 3: return f"{adj} {random.choice(CAVE_TYPES)}"
        if encounter_type == 4: return f"{adj} {random.choice(FOREST_TYPES)}"
        if encounter_type == 5: return f"{adj} {random.choice(BOSSES)}"

    def generate_description(encounter_type, level_range):
        min_lvl = level_range * 10 + 1
        max_lvl = (level_range + 1) * 10
        if encounter_type == 0: return f"A TRANSACTION node. A merchant offering gear for adventurers level {min_lvl}-{max_lvl}."
        if encounter_type == 1: return f"A QUERY node. Hostile enemies scaled for fighters level {min_lvl}-{max_lvl}."
        if encounter_type == 2: return f"A STORED_PROCEDURE node. A dungeon with scripted traps and enemies level {min_lvl}-{max_lvl}."
        if encounter_type == 3: return f"A DEADLOCK node. A dark cave where two forces collide around level {min_lvl}-{max_lvl}."
        if encounter_type == 4: return f"A CONSTRAINT node. A forest where the world pushes back, level {min_lvl}-{max_lvl}."
        if encounter_type == 5: return f"An OVERFLOW node. A boss encounter for heroes level {min_lvl}-{max_lvl}."

    rows = []
    for level_range in range(10):
        for encounter_type, amount in DISTRIBUTION.items():
            for _ in range(amount):
                rows.append((
                    generate_name(encounter_type, level_range),
                    generate_description(encounter_type, level_range),
                    encounter_type,
                    level_range,
                    0
                ))

    c.executemany("""
        INSERT INTO map (name, description, encounter_type, level_range, finished)
        VALUES (?, ?, ?, ?, ?)
    """, rows)

    conn.commit()


def init_run(player_id: int, custom_seed: int = None):
    """Create a new run for the player — generate a seed, INSERT the run row,
    build the full path tree, and set the player's current position to the root."""

    # Determine level_range from player's current level
    c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = c.fetchone()[0]
    level_range = min((player_level - 1) // 10, 9)  # 0-9

    # Generate and store the seed so the run is reproducible
    seed = custom_seed if custom_seed is not None else random.randint(0, 999_999)

    c.execute("""
        INSERT INTO runs (player_id, seed, level_range)
        VALUES (?, ?, ?)
    """, (player_id, seed, level_range))
    run_id = c.lastrowid

    # Build the tree using this seed
    root_id = generate_path(run_id, level_range, seed)

    # Point the player at the root node
    c.execute("""
        UPDATE players
        SET current_run_id = ?, current_path_id = ?
        WHERE id = ?
    """, (run_id, root_id, player_id))

    conn.commit()
    return run_id, root_id, seed


def generate_path(run_id: int, level_range: int, seed: int):
    """Build a full path tree and INSERT all nodes into the path table.

    Tree shape:
      depth 0 — root (START, no encounter)
      depth 1 — up to 3 children, mixed encounter types
      depth 2 — up to 3 children per depth-1 node
      depth 3 — up to 3 children per depth-2 node
      depth 4 — leaf nodes, always OVERFLOW (boss)

    Returns the path.id of the root node.

    Branch values: 0 = <- (left)  1 = o (straight)  2 = -> (right)
    """

    # Seed random so the same seed always produces the same tree
    rng = random.Random(seed)

    # Pull the map pool for this level_range — exclude OVERFLOW (5), those are leaves only
    c.execute("""
        SELECT name, description, encounter_type
        FROM map
        WHERE level_range = ? AND encounter_type != 5
    """, (level_range,))
    pool = c.fetchall()

    # Separate boss pool for leaf nodes
    c.execute("""
        SELECT name, description, encounter_type
        FROM map
        WHERE level_range = ? AND encounter_type = 5
    """, (level_range,))
    boss_pool = c.fetchall()

    # Fallback if pools are empty (shouldn't happen after init_map)
    if not pool:
        pool = [("Unknown Path", "A mysterious encounter.", 1)]
    if not boss_pool:
        boss_pool = [("Ancient Overflow", "An OVERFLOW node. A boss encounter.", 5)]

    # Encounter type weights for non-leaf nodes:
    # QUERY (1) is most common, TRANSACTION (0) is rare, others in between
    WEIGHTS = {0: 1, 1: 6, 2: 2, 3: 2, 4: 1}

    def weighted_pick(exclude_types=()):
        """Pick a random map row, weighted by encounter type frequency."""
        candidates = [r for r in pool if r["encounter_type"] not in exclude_types]
        if not candidates:
            candidates = pool
        weights = [WEIGHTS.get(r["encounter_type"], 1) for r in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]

    def insert_node(parent_id, depth, branch, row, is_boss=False):
        enc_type = 5 if is_boss else row["encounter_type"]
        c.execute("""
            INSERT INTO path (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, parent_id, depth, branch, row["name"], row["description"], enc_type, level_range))
        return c.lastrowid

    # --- depth 0: root (START node, type = -1 means no encounter) ---
    c.execute("""
        INSERT INTO path (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
        VALUES (?, NULL, 0, 1, 'START', 'The journey begins here.', -1, ?)
    """, (run_id, level_range))
    root_id = c.lastrowid

    # --- depth 1: 2 or 3 branches from root ---
    depth1_count = rng.randint(2, 3)
    branches_1 = rng.sample([0, 1, 2], depth1_count)  # pick which branch slots to use

    depth1_ids = []
    for branch in sorted(branches_1):
        # Guarantee at least one TRANSACTION (shop) at depth 1
        if branch == branches_1[0]:
            candidates = [r for r in pool if r["encounter_type"] == 0]
            row = rng.choice(candidates) if candidates else weighted_pick()
        else:
            row = weighted_pick(exclude_types=(5,))
        node_id = insert_node(root_id, 1, branch, row)
        depth1_ids.append((node_id, branch))

    # --- depth 2 and 3: grow children from each parent ---
    prev_depth_ids = depth1_ids

    for depth in range(2, 4):
        next_depth_ids = []
        for parent_id, _ in prev_depth_ids:
            child_count = rng.randint(1, 3)
            branches = rng.sample([0, 1, 2], child_count)
            for branch in sorted(branches):
                row = weighted_pick(exclude_types=(5,))
                node_id = insert_node(parent_id, depth, branch, row)
                next_depth_ids.append((node_id, branch))
        prev_depth_ids = next_depth_ids

    # --- depth 4: leaf nodes — always OVERFLOW (boss) ---
    for parent_id, _ in prev_depth_ids:
        row = rng.choice(boss_pool)
        insert_node(parent_id, 4, 1, row, is_boss=True)

    conn.commit()
    return root_id


def get_path_node(path_id: int):
    """SELECT a single path node by id."""
    c.execute("SELECT * FROM path WHERE id = ?", (path_id,))
    return c.fetchone()


def get_path_children(path_id: int):
    """SELECT the children of a path node, ordered by branch (left to right)."""
    c.execute("""
        SELECT * FROM path
        WHERE parent_id = ?
        ORDER BY branch ASC
    """, (path_id,))
    return c.fetchall()


def move_to_node(player_id: int, path_id: int):
    """UPDATE the player's current position in the path tree."""
    c.execute("""
        UPDATE players SET current_path_id = ? WHERE id = ?
    """, (path_id, player_id))
    conn.commit()


def finish_node(path_id: int):
    """Mark a path node as cleared."""
    c.execute("UPDATE path SET finished = 1 WHERE id = ?", (path_id,))
    conn.commit()


def register_shop_visit(player_id: int, path_id: int):
    """INSERT a visited shop record so the player can return to it."""
    # Avoid duplicate entries
    c.execute("""
        SELECT 1 FROM visited_shops WHERE player_id = ? AND path_id = ?
    """, (player_id, path_id))
    if not c.fetchone():
        c.execute("""
            INSERT INTO visited_shops (player_id, path_id) VALUES (?, ?)
        """, (player_id, path_id))
        conn.commit()


def get_visited_shops(player_id: int):
    """SELECT all shop nodes the player can return to."""
    c.execute("""
        SELECT p.* FROM path p
        JOIN visited_shops v ON v.path_id = p.id
        WHERE v.player_id = ?
    """, (player_id,))
    return c.fetchall()


def init_player(username: str, class_name: str):
    """INSERT a new player row and their starting stats, weapon, and armor."""
    c.execute("""
        SELECT id, base_hp, base_hit, base_wisdom
        FROM class
        WHERE name = ?
    """, (class_name,))
    class_data = c.fetchone()

    if not class_data:
        raise ValueError(f"Class '{class_name}' does not exist")

    class_id, hp, hit, wisdom = class_data


    c.execute("""
        INSERT INTO players (username, class_id)
        VALUES (?, ?)
    """, (username, class_id))
    player_id = c.lastrowid

    c.execute("""
        INSERT INTO player_stats (
            player_id, base_hp, max_hp, current_hp,
            base_hit, base_wisdom
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, hp, hp, hp, hit, wisdom))

    starter_weapon(player_id)
    starter_armor(player_id)
    conn.commit()

    return player_id


def bonus_calc(bonus_type: BonusType, player_id: int, remove: bool = False):
    """Apply or remove stat bonuses when equipping/unequipping gear.
    Class-matching gear fires an additional class bonus on top."""

    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]

    # Map class_id back to class name
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
        bonus_wisdom = weapon_data["bonus_wisdom"] * multiplier

        # Class bonus — fires only when gear matches player class
        if weapon_data["class_type"] == user_class_type:
            if user_class_type == "The Executor":
                bonus_hp *= 2
            elif user_class_type == "The Indexer":
                bonus_wisdom *= 2
            elif user_class_type == "The Trigger":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)

        # hit_mult scales base_hit multiplicatively
        if not remove:
            c.execute("UPDATE player_stats SET base_hit = base_hit * ? WHERE player_id = ?", (hit_mult, player_id))
        else:
            c.execute("UPDATE player_stats SET base_hit = base_hit / ? WHERE player_id = ?", (hit_mult, player_id))

        c.execute("""
            UPDATE player_stats
            SET bonus_hp = bonus_hp + ?,
                bonus_hit = bonus_hit + ?,
                bonus_wisdom = bonus_wisdom + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_wisdom, player_id))

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
        bonus_wisdom = armor_data["bonus_wisdom"] * multiplier

        # Class bonus
        if armor_data["class_type"] == user_class_type:
            if user_class_type == "The Executor":
                bonus_hp *= 2
            elif user_class_type == "The Indexer":
                bonus_wisdom *= 2
            elif user_class_type == "The Trigger":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)

        if not remove:
            c.execute("UPDATE player_stats SET base_hit = base_hit * ? WHERE player_id = ?", (hit_mult, player_id))
        else:
            c.execute("UPDATE player_stats SET base_hit = base_hit / ? WHERE player_id = ?", (hit_mult, player_id))

        c.execute("""
            UPDATE player_stats
            SET bonus_hp = bonus_hp + ?,
                bonus_hit = bonus_hit + ?,
                bonus_wisdom = bonus_wisdom + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_wisdom, player_id))

        c.execute("UPDATE player_stats SET max_hp = base_hp + bonus_hp WHERE player_id = ?", (player_id,))

    elif bonus_type is BonusType.POTION:
        pass  # potions are applied directly via apply_potion()
    elif bonus_type is BonusType.ENV:
        pass

    conn.commit()


def get_potion_pool():
    """Return the full list of available potion definitions.
    Called to populate shop stock and enemy drops.

    Potion types:
      RESTORE          — pure healing
      SURGE            — attack boost (bonus_hit)
      CLARITY          — wisdom boost (bonus_wisdom)
      BARRIER          — defense (flat damage reduction for one combat)
      RESTORE_SURGE    — heal + attack
      RESTORE_CLARITY  — heal + wisdom
      SURGE_CLARITY    — attack + wisdom
    """
    return [
        # name,                  type,             heal  hit  wis  def  dur  price
        ("Minor Restore",        "RESTORE",         30,   0,   0,   0,   1,   10),
        ("Restore",              "RESTORE",         60,   0,   0,   0,   1,   20),
        ("Major Restore",        "RESTORE",         120,  0,   0,   0,   1,   40),
        ("Minor Surge",          "SURGE",           0,    8,   0,   0,   3,   15),
        ("Surge",                "SURGE",           0,    18,  0,   0,   3,   30),
        ("Major Surge",          "SURGE",           0,    35,  0,   0,   5,   55),
        ("Minor Clarity",        "CLARITY",         0,    0,   8,   0,   3,   15),
        ("Clarity",              "CLARITY",         0,    0,   18,  0,   3,   30),
        ("Major Clarity",        "CLARITY",         0,    0,   35,  0,   5,   55),
        ("Minor Barrier",        "BARRIER",         0,    0,   0,   10,  3,   15),
        ("Barrier",              "BARRIER",         0,    0,   0,   22,  3,   30),
        ("Major Barrier",        "BARRIER",         0,    0,   0,   45,  5,   55),
        ("Mending Surge",        "RESTORE_SURGE",   40,   12,  0,   0,   3,   35),
        ("Vital Surge",          "RESTORE_SURGE",   80,   25,  0,   0,   3,   65),
        ("Mending Clarity",      "RESTORE_CLARITY", 40,   0,   12,  0,   3,   35),
        ("Vital Clarity",        "RESTORE_CLARITY", 80,   0,   25,  0,   3,   65),
        ("Mind and Blade",       "SURGE_CLARITY",   0,    15,  15,  0,   3,   50),
        ("Grand Elixir",         "SURGE_CLARITY",   0,    30,  30,  0,   5,   90),
    ]


def apply_potion(player_id: int, potion_name: str):
    """Apply a potion's effects to the player's stats.
    Temporary buffs (hit/wisdom/defense) are tracked via potion_active table.
    Returns a dict describing what was applied so the caller can display it.
    """
    # Find the potion definition
    pool = {p[0]: p for p in get_potion_pool()}
    if potion_name not in pool:
        return {}

    _, ptype, heal, bhit, bwis, bdef, dur, _ = pool[potion_name]

    result = {}

    # Healing — immediate, applied to current_hp capped at max_hp
    if heal > 0:
        c.execute("""
            UPDATE player_stats
            SET current_hp = MIN(current_hp + ?, max_hp)
            WHERE player_id = ?
        """, (heal, player_id))
        result["heal"] = heal

    # Stat buffs — added directly; stored so combat can read defense
    if bhit > 0:
        c.execute("""
            UPDATE player_stats SET bonus_hit = bonus_hit + ? WHERE player_id = ?
        """, (bhit, player_id))
        result["bonus_hit"] = bhit

    if bwis > 0:
        c.execute("""
            UPDATE player_stats SET bonus_wisdom = bonus_wisdom + ? WHERE player_id = ?
        """, (bwis, player_id))
        result["bonus_wisdom"] = bwis

    # Defense stored as a session value — combat reads it then decrements
    if bdef > 0:
        result["defense"] = bdef
        # Store in a temporary key on player_stats (reuse bonus columns safely)
        # We track active defense in memory; main.py holds it per-combat

    conn.commit()
    return result


def enemy_drop_potion(player_id: int):
    """Roll for a potion drop after combat. 35% base chance.
    Returns potion name if dropped, else None.
    """
    if random.random() > 0.35:
        return None

    pool = get_potion_pool()
    # Weight toward minor/cheap potions for regular enemies
    weights = [1 / (p[7] + 1) * 100 for p in pool]  # inverse of price
    chosen = random.choices(pool, weights=weights, k=1)[0]
    potion_name = chosen[0]

    add_item(player_id, potion_name, 1)
    return potion_name


def generate_enemy(player_id: int, is_boss: bool = False):
    """INSERT a new enemy row scaled to the player's current stats, not just level.

    Pulls the player's actual max_hp and total hit so enemies always feel threatening.
    Boss enemies get a separate multiplier on top.
    """
    c.execute("""
        SELECT p.level, ps.max_hp, ps.base_hit + ps.bonus_hit AS total_hit
        FROM players p
        JOIN player_stats ps ON ps.player_id = p.id
        WHERE p.id = ?
    """, (player_id,))
    row = c.fetchone()
    player_level = row["level"]
    player_hp    = row["max_hp"]
    player_hit   = row["total_hit"]

    enemy_types = ["Corrupted Index", "Null Pointer", "Stack Overflow", "Deadlock Wraith", "Zombie Process"]
    enemy_type  = random.choice(enemy_types)

    # --- Scaling goals ---
    # Enemy should take 5-8 player hits to kill (accounting for ±15% dmg variance + crits)
    # Enemy should deal enough damage to kill the player in 24 hits
    #
    # player_hit  = base_hit * hit_mult + bonus_hit  (full gear stack)
    # player_hp   = base_hp + bonus_hp               (full gear stack)
    # Both are already read from player_stats so they reflect all equipped bonuses.

    target_rounds_to_die  = random.randint(5, 8)    # how many player hits to kill enemy
    target_rounds_to_kill = random.randint(6, 24)   # how many enemy hits to kill player

    hp_variance  = random.uniform(0.88, 1.12)
    hit_variance = random.uniform(0.88, 1.12)

    # Average player damage per hit (mid-variance, no crit)
    avg_player_dmg = player_hit * 1.0

    # Enemy HP = average player damage * desired rounds multiplied by 0.5 to make it easier for players
    base_hp  = max(40, int((avg_player_dmg * target_rounds_to_die * hp_variance) * 0.5))

    # Enemy hit = player HP / desired rounds to kill player multiplied by 0.5 to make it easier for players
    base_hit = max(8,  int(((player_hp / target_rounds_to_kill) * hit_variance) * 0.5))
    experience_drop = 20 + (player_level * 5) + random.randint(-5, 5)

    # Boss multiplier — significantly tankier and harder hitting
    if is_boss:
        base_hp  = int(base_hp  * 3.5)
        base_hit = int(base_hit * 1.8)
        experience_drop *= 5
        enemy_type = "OVERFLOW — " + random.choice(["The Warlord", "The Tyrant", "The Behemoth", "The Archmage", "The Overseer"])

    c.execute("""
        INSERT INTO enemies (type, base_hp, base_hit, experience_drop)
        VALUES (?, ?, ?, ?)
    """, (enemy_type, base_hp, base_hit, experience_drop))

    conn.commit()
    return c.lastrowid


def enemy_attack(player_id: int, enemy_id: int):
    """Run one round of combat — both sides deal damage simultaneously."""
    damage_to_enemy, damage_to_player = calculate_damage(player_id, enemy_id)

    c.execute("""
        UPDATE player_stats
        SET current_hp = current_hp - ?
        WHERE player_id = ?
    """, (damage_to_player, player_id))

    c.execute("""
        UPDATE enemies
        SET base_hp = base_hp - ?
        WHERE id = ?
    """, (damage_to_enemy, enemy_id))

    conn.commit()


def check_combat_outcome(player_id: int, enemy_id: int):
    """SELECT both HP values and return the current combat state."""
    c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
    player_hp = c.fetchone()[0]

    c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hp = c.fetchone()[0]

    if player_hp <= 0 and enemy_hp <= 0:
        return "draw"
    elif player_hp <= 0:
        return "enemy_win"
    elif enemy_hp <= 0:
        return "player_win"
    else:
        return "ongoing"


def calculate_damage(player_id: int, enemy_id: int):
    """Calculate damage both sides deal in one round."""
    c.execute("SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,))
    player_stats = c.fetchone()
    player_hit   = player_stats["base_hit"] + player_stats["bonus_hit"]

    c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    enemy_hit = c.fetchone()[0]

    damage_to_enemy  = max(0, player_hit - random.randint(0, 5))
    damage_to_player = max(0, enemy_hit  - random.randint(0, 5))

    return damage_to_enemy, damage_to_player


def reconnect():
    """Reconnect to the database. Useful for long-running sessions."""
    global conn, c
    conn.close()
    conn = sql.connect("game_data.db")
    conn.row_factory = sql.Row
    c = conn.cursor()

def experience_needed_for_next_level(current_level: int):
    """Calculate the experience needed to reach the next level.
    Uses a simple formula: 100 XP for level 2, then +50 XP per additional level."""
    if current_level < 1:
        return 100
    return 100 + (current_level - 1) * 50

def level_up(player_id: int):
    """Increase player level by 1 and apply stat increases."""
    c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
    row = c.fetchone()
    current_level = row[0]
    current_experience = row[1]
    new_level = current_level + 1

    # Level up bonuses — simple flat increases per level
    hp_increase = 20
    hit_increase = 5
    wisdom_increase = 3

    if current_experience < experience_needed_for_next_level(current_level):
        raise ValueError("Not enough experience to level up")
    
    c.execute("""
        UPDATE players SET experience = experience - ? WHERE id = ?
    """, (experience_needed_for_next_level(current_level), player_id))

    c.execute("""
        UPDATE players SET level = ? WHERE id = ?
    """, (new_level, player_id))

    c.execute("""
        UPDATE player_stats
        SET base_hp = base_hp + ?,
            max_hp = max_hp + ?,
            current_hp = max_hp + ?,  -- heal on level up
            base_hit = base_hit + ?,
            base_wisdom = base_wisdom + ?
        WHERE player_id = ?
    """, (hp_increase, hp_increase, hp_increase, hit_increase, wisdom_increase, player_id))

    conn.commit()

    print(f"\nlevel up! ({current_level} -> {new_level})")


