import sqlite3 as sql
import json
import random

DB_PATH = "game_data.db"

conn = sql.connect(DB_PATH)
conn.row_factory = sql.Row
c = conn.cursor()


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
        CREATE TRIGGER IF NOT EXISTS weapon_limit
        BEFORE INSERT ON weapons
        WHEN (SELECT COUNT(*) FROM weapons) >= 100
        BEGIN
            SELECT RAISE(IGNORE);
        END;
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

    conn.commit()
    return player_id


