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
        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            base_hp INTEGER DEFAULT 80,
            base_hit INTEGER DEFAULT 10,
            weapon TEXT,
            experience_drop INTEGER
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

    # table of enchounter types
    # 0 - shop
    # 1 - compat
    # 2 - dungeon
    # 3 - cave
    # 4 - forest
    # 5 - boss
    #
    # level_ranges
    #
    # 0 for level 1-10
    # 1 for level 11-20
    # 2 for level 21-30
    # 3 for level 31-40
    # 4 for level 41-50
    # 5 for level 51-60
    # 6 for level 61-70
    # 7 for level 71-80
    # 8 for level 81-90
    # 9 for level 91-100
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

    conn.commit()


def init_classes():
    classes = [
        ("Warrior", 120, 15, 5),
        ("Mage", 70, 5, 20),
        ("Rogue", 90, 12, 10),
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
    with open("weapon_name.json", "r") as w:
        data = json.load(w)

    name = f"{random.choice(data['first_name'])} {random.choice(data['second_name'])}"

    class_type = random.choice(["Warrior", "Rogue", "Mage"])

    if class_type == "Warrior":
        hit_mult = random.randint(1, 30)
        bonus_hp = random.randint(300, 500)
        bonus_hit = random.randint(20, 60)
        bonus_wisdom = random.randint(0, 10)
    elif class_type == "Rogue":
        hit_mult = random.randint(1, 30)
        bonus_hp = random.randint(100, 250)
        bonus_hit = random.randint(30, 50)
        bonus_wisdom = random.randint(25, 25)
    else:
        hit_mult = random.randint(1, 30)
        bonus_hp = random.randint(20, 100)
        bonus_hit = random.randint(5, 20)
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
    with open("armor_name.json", "r") as w:
        data = json.load(w)

    name = random.choice(data)

    class_type = random.choice(["Warrior", "Rogue", "Mage"])

    if class_type == "Warrior":
        hit_mult = random.randint(1, 30)
        bonus_hp = random.randint(300, 500)
        bonus_hit = random.randint(20, 60)
        bonus_wisdom = 0
    elif class_type == "Rogue":
        hit_mult = random.randint(1, 30)
        bonus_hp = random.randint(100, 250)
        bonus_hit = random.randint(30, 50)
        bonus_wisdom = random.randint(25, 25)
    else:
        hit_mult = random.randint(1, 30)
        bonus_hp = 10
        bonus_hit = random.randint(5, 20)
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
# Distribution per level range (total = 50)
    DISTRIBUTION = {
        0: 5,   # shop
        1: 30,  # combat
        2: 5,   # dungeon
        3: 5,   # cave
        4: 3,   # forest
        5: 2    # boss
    }

    LOW_ADJ = ["Quiet", "Small", "Dusty", "Worn", "Faded"]
    MID_ADJ = ["Savage", "Shadowed", "Ancient", "Ruthless", "Cursed"]
    HIGH_ADJ = ["Mythic", "Abyssal", "Cataclysmic", "Eternal", "Godslayer"]

    CREATURES = ["Goblins", "Bandits", "Wolves", "Skeletons", "Cultists", "Knights"]
    BOSSES = ["Warlord", "Overseer", "Tyrant", "Behemoth", "Archmage"]
    PLACES = ["Ruins", "Sanctum", "Fortress", "Temple", "Stronghold"]
    CAVE_TYPES = ["Crystal Cavern", "Molten Depths", "Frozen Hollow", "Echoing Cave"]
    FOREST_TYPES = ["Whispering Woods", "Twilight Grove", "Rotwood Forest", "Bloodleaf Wilds"]

    def get_adjectives(level_range):
        if level_range <= 2:
            return LOW_ADJ
        elif level_range <= 6:
            return MID_ADJ
        return HIGH_ADJ

    def generate_name(encounter_type, level_range):
        adj = random.choice(get_adjectives(level_range))

        if encounter_type == 0:
            return f"{adj} Traveling Merchant"
        if encounter_type == 1:
            return f"{adj} {random.choice(CREATURES)}"
        if encounter_type == 2:
            return f"{adj} {random.choice(PLACES)}"
        if encounter_type == 3:
            return f"{adj} {random.choice(CAVE_TYPES)}"
        if encounter_type == 4:
            return f"{adj} {random.choice(FOREST_TYPES)}"
        if encounter_type == 5:
            return f"{adj} {random.choice(BOSSES)}"

    def generate_description(encounter_type, level_range):
        min_lvl = level_range * 10 + 1
        max_lvl = (level_range + 1) * 10

        if encounter_type == 0:
            return f"A merchant offering gear suitable for adventurers level {min_lvl}-{max_lvl}."
        if encounter_type == 1:
            return f"Hostile enemies scaled for fighters level {min_lvl}-{max_lvl}."
        if encounter_type == 2:
            return f"A dangerous dungeon filled with traps and enemies level {min_lvl}-{max_lvl}."
        if encounter_type == 3:
            return f"A dark cave hiding creatures around level {min_lvl}-{max_lvl}."
        if encounter_type == 4:
            return f"A dense forest crawling with threats level {min_lvl}-{max_lvl}."
        if encounter_type == 5:
            return f"A powerful boss encounter meant for heroes level {min_lvl}-{max_lvl}."

    rows = []

    for level_range in range(10):
        for encounter_type, amount in DISTRIBUTION.items():
            for _ in range(amount):
                name = generate_name(encounter_type, level_range)
                description = generate_description(encounter_type, level_range)

                rows.append((
                    name,
                    description,
                    encounter_type,
                    level_range,
                    0
                ))

    c.executemany("""
    INSERT INTO map (name, description, encounter_type, level_range, finished)
    VALUES (?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    

def init_player(username: str, class_name: str):
    c.execute("""
        SELECT id, base_hp, base_hit, base_wisdom
        FROM class
        WHERE name = ?
    """, (class_name,))
    class_data = c.fetchone()

    if not class_data:
        raise ValueError("Class does not exist")

    class_id, hp, hit, wisdom = class_data

    conn.execute("BEGIN")

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
    c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = c.fetchone()[0]
    
    if class_id == 1:
        user_class_type = "Warrior"
    elif class_id == 2:
        user_class_type = "Mage"
    elif class_id == 3:
        user_class_type = "Rogue"
    
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
        
        hit_mult = weapon_data["hit_mult"]
        bonus_hp = weapon_data["bonus_hp"] * multiplier
        bonus_hit = weapon_data["bonus_hit"] * multiplier
        bonus_wisdom = weapon_data["bonus_wisdom"] * multiplier
        
        if weapon_data["class_type"] == user_class_type:
            if user_class_type == "Warrior":
                bonus_hp *= 2
            elif user_class_type == "Mage":
                bonus_wisdom *= 2
            elif user_class_type == "Rogue":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)
        
        if not remove:
            c.execute("""
                UPDATE player_stats
                SET base_hit = base_hit * ?
                WHERE player_id = ?
            """, (hit_mult, player_id))
        else:
            c.execute("""
                UPDATE player_stats
                SET base_hit = base_hit / ?
                WHERE player_id = ?
            """, (hit_mult, player_id))
        
        c.execute("""
            UPDATE player_stats
            SET
                bonus_hp = bonus_hp + ?,
                bonus_hit = bonus_hit + ?,
                bonus_wisdom = bonus_wisdom + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_wisdom, player_id))
        
        c.execute("""
            UPDATE player_stats
            SET max_hp = base_hp + bonus_hp
            WHERE player_id = ?
        """, (player_id,))
        
    elif bonus_type is BonusType.ARMOR:
        c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
        armor = c.fetchone()[0]
        
        if armor is None:
            return
        
        c.execute("SELECT * FROM armors WHERE name = ?", (armor,))
        armor_data = c.fetchone()
        
        if armor_data is None:
            return
        
        hit_mult = armor_data["hit_mult"]
        bonus_hp = armor_data["bonus_hp"] * multiplier
        bonus_hit = armor_data["bonus_hit"] * multiplier
        bonus_wisdom = armor_data["bonus_wisdom"] * multiplier
        
        if armor_data["class_type"] == user_class_type:
            if user_class_type == "Warrior":
                bonus_hp *= 2
            elif user_class_type == "Mage":
                bonus_wisdom *= 2
            elif user_class_type == "Rogue":
                bonus_hit = bonus_hit * 2 + (20 * multiplier)
        
        if not remove:
            c.execute("""
                UPDATE player_stats
                SET base_hit = base_hit * ?
                WHERE player_id = ?
            """, (hit_mult, player_id))
        else:
            c.execute("""
                UPDATE player_stats
                SET base_hit = base_hit / ?
                WHERE player_id = ?
            """, (hit_mult, player_id))
        
        c.execute("""
            UPDATE player_stats
            SET
                bonus_hp = bonus_hp + ?,
                bonus_hit = bonus_hit + ?,
                bonus_wisdom = bonus_wisdom + ?
            WHERE player_id = ?
        """, (bonus_hp, bonus_hit, bonus_wisdom, player_id))
        
        c.execute("""
            UPDATE player_stats
            SET max_hp = base_hp + bonus_hp
            WHERE player_id = ?
        """, (player_id,))
        
    elif bonus_type is BonusType.POTION:
        pass
    elif bonus_type is BonusType.ENV:
        pass
    
    conn.commit()

def generate_enemy(player_id: int):
    c.execute("""
        SELECT level
        FROM players
        WHERE id = ?
    """, (player_id,))
    player_level = c.fetchone()[0]
    
    enemy_types = ["Goblin", "Skeleton", "Orc", "Troll", "Bandit"]
    enemy_type = random.choice(enemy_types)
    
    base_hp = 50 + (player_level * 10) + random.randint(-10, 10)
    base_hit = 5 + (player_level * 2) + random.randint(-2, 2)
    experience_drop = 20 + (player_level * 5) + random.randint(-5, 5)
    
    c.execute("""
        INSERT INTO enemies (type, base_hp, base_hit, experience_drop)
        VALUES (?, ?, ?, ?)
    """, (enemy_type, base_hp, base_hit, experience_drop))
    
    conn.commit()
    return c.lastrowid

def enemy_attack(player_id: int, enemy_id: int):
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
    c.execute("""
        SELECT current_hp
        FROM player_stats
        WHERE player_id = ?
    """, (player_id,))
    player_hp = c.fetchone()[0]
    
    c.execute("""
        SELECT base_hp
        FROM enemies
        WHERE id = ?
    """, (enemy_id,))
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
    c.execute("""
        SELECT base_hit, bonus_hit
        FROM player_stats
        WHERE player_id = ?
    """, (player_id,))
    player_stats = c.fetchone()
    player_hit = player_stats["base_hit"] + player_stats["bonus_hit"]
    
    c.execute("""
        SELECT base_hit
        FROM enemies
        WHERE id = ?
    """, (enemy_id,))
    enemy_hit = c.fetchone()[0]
    
    damage_to_enemy = max(0, player_hit - random.randint(0, 5))
    damage_to_player = max(0, enemy_hit - random.randint(0, 5))
    
    return damage_to_enemy, damage_to_player

