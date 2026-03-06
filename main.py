import os
import time
import random
import database as db
import ascii_art

# --- Game state flags ---
run = True
menu = True
play = False
adventuring = False
inventory = False
selecting_item = False
player_id = None

# Inventory pagination
INV_PAGE_SIZE = 8


def clear_screen():
    print("\n" * 100)


def typewrite(text, delay=0.03):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def draw_logo():
    clear_screen()
    print(r"  _________      .__  .__  __                                 .__        ")
    print(r" /   _____/ _____|  | |__|/  |_  ____     _____ _____    ____ |__|____   ")
    print(r" \_____  \ / ____/  | |  \   __\/ __ \   /     \\__  \  /    \|  \__  \  ")
    print(r" /        < <_|  |  |_|  ||  | \  ___/  |  Y Y  \/ __ \|   |  \  |/ __ \_")
    print(r"/_______  /\__   |____/__||__|  \___  > |__|_|  (____  /___|  /__(____  /")
    print(r"        \/    |__|                  \/        \/     \/     \/        \/ ")
    print("by Novodude")
    time.sleep(1.5)


def initialize_game():
    draw_logo()
    typewrite("initializing db...", delay=0.01)
    db.init_db()
    typewrite("loading class schemas...", delay=0.01)
    db.init_classes()
    typewrite("generating loot tables...", delay=0.01)
    db.loot_init()
    typewrite("building world index...", delay=0.01)
    db.init_map()
    typewrite("ready.", delay=0.05)


def new_game():
    clear_screen()
    username = input("username: ")
    choose_class = input("(1) The Executor  (2) The Indexer  (3) The Trigger\n> ")

    if choose_class == "1":
        class_name = "The Executor"
    elif choose_class == "2":
        class_name = "The Indexer"
    elif choose_class == "3":
        class_name = "The Trigger"
    else:
        print("invalid class")
        return None

    try:
        return db.init_player(username, class_name)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"  username '{username}' is already taken.")
        else:
            print(f"  error creating player: {e}")
        input("\npress enter...")
        return None


def load_game():
    clear_screen()
    db.c.execute("SELECT id, username FROM players")
    usernames = db.c.fetchall()

    print("players:")
    for username in usernames:
        print(f"({username['id']}) {username['username']}")

    user_id = input("choose number: ")
    db.c.execute("SELECT id FROM players WHERE id = ?", (user_id,))
    row = db.c.fetchone()
    if not row:
        print("save not found")
        return None
    return row["id"]


def get_equipped(player_id):
    db.c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    row = db.c.fetchone()
    equipped_weapon = row["equipped_weapon"] if row else None

    db.c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
    row = db.c.fetchone()
    equipped_armor = row["equipped_armor"] if row else None

    return equipped_weapon, equipped_armor


def print_item_stats(data, label):
    print("====================")
    print(f"[{label}]")
    print("| Class:          ", data["class_type"])
    print("| Hit Multiplier: ", data["hit_mult"])
    print("| Bonus HP:       ", data["bonus_hp"])
    print("| Bonus Hit:      ", data["bonus_hit"])
    print("| Bonus Wisdom:   ", data["bonus_wisdom"])
    print("====================")


def xp_bar(current_xp: int, level: int, width: int = 20) -> str:
    """Return a visual XP progress bar string."""
    needed = db.experience_needed_for_next_level(level)
    filled = int((current_xp / needed) * width)
    filled = min(filled, width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current_xp}/{needed} xp"


def hp_bar(current: int, maximum: int, width: int = 20) -> str:
    """Return a colour-coded HP bar string.
    Full (>60%) = █  Wounded (30-60%) = ▓  Critical (<30%) = ░
    """
    if maximum <= 0:
        return f"[{'░' * width}] 0/0"
    ratio  = max(0, current) / maximum
    filled = int(ratio * width)
    if ratio > 0.60:
        block = "█"
    elif ratio > 0.30:
        block = "▓"
    else:
        block = "░"
    bar = block * filled + "·" * (width - filled)
    return f"[{bar}] {current}/{maximum}"


def show_stats(player_id):
    db.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
    username = db.c.fetchone()["username"]
    db.c.execute("""
        SELECT base_hp, bonus_hp, max_hp, current_hp, gold,
               base_hit, bonus_hit, base_wisdom, bonus_wisdom
        FROM player_stats WHERE player_id = ?
    """, (player_id,))
    stats = db.c.fetchone()
    db.c.execute("SELECT level, experience, deaths, kills FROM players WHERE id = ?", (player_id,))
    player_info = db.c.fetchone()

    header = f"=== [ {username} ] ==="
    print(header)
    print(f"Level: {player_info['level']}  |  {xp_bar(player_info['experience'], player_info['level'])}")
    print(f"HP:     {hp_bar(stats['current_hp'], stats['max_hp'])}  (base {stats['base_hp']} + bonus {stats['bonus_hp']})")
    print(f"Hit:    {stats['base_hit'] + stats['bonus_hit']}  (base {stats['base_hit']} + bonus {stats['bonus_hit']})")
    print(f"Wisdom: {stats['base_wisdom'] + stats['bonus_wisdom']}  (base {stats['base_wisdom']} + bonus {stats['bonus_wisdom']})")
    print(f"Kills: {player_info['kills']}   Deaths: {player_info['deaths']}")
    print(f"Gold:  {stats['gold']}")
    print("=" * len(header))


# ------------------------------------------------------------------ #
#  COMBAT                                                             #
# ------------------------------------------------------------------ #

def get_combat_potions(player_id):
    potion_names = {p[0] for p in db.get_potion_pool()}
    db.c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
    return [i for i in db.c.fetchall() if i["item"] in potion_names]


def draw_combat_screen(player_id, enemy_id, events, active_defense, log):
    db.c.execute("SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (player_id,))
    pstats = db.c.fetchone()
    db.c.execute("SELECT type, base_hp, max_hp FROM enemies WHERE id = ?", (enemy_id,))
    estats = db.c.fetchone()

    clear_screen()
    ascii_art.print_enemy_art(estats["type"])
    print()
    print(f"  [ {estats['type']} ]")
    print(f"  HP: {hp_bar(estats['base_hp'], estats['max_hp'])}")
    print()

    if events["blood_moon"]:
        print("  * BLOOD MOON active *")
    if events["monster_rush"]:
        print("  * MONSTER RUSH active *")
    if events["blood_moon"] or events["monster_rush"]:
        print()

    if log:
        for entry in log[-3:]:
            print(f"  > {entry}")
        print()

    barrier_str = f"  [BARRIER: {active_defense}]" if active_defense > 0 else ""
    print(f"  [ YOU ]   {hp_bar(pstats['current_hp'], pstats['max_hp'])}{barrier_str}")
    print()

    potions = get_combat_potions(player_id)
    print("  (1) attack")
    for i, pot in enumerate(potions, 2):
        print(f"  ({i}) use {pot['item']}  x{pot['amount']}")
    print(f"  ({len(potions) + 2}) flee")
    print()

    return estats, pstats, potions


def player_attack(player_id, enemy_id):
    db.c.execute("SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,))
    pstats = db.c.fetchone()
    dmg = max(1, pstats["base_hit"] + pstats["bonus_hit"] - random.randint(0, 5))
    db.c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (dmg, enemy_id))
    db.conn.commit()
    return dmg


def enemy_turn(player_id, enemy_id, events, active_defense):
    log = []
    db.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    ehit = db.c.fetchone()[0]

    dmg = max(0, ehit - random.randint(0, 5))

    if active_defense > 0:
        absorbed = min(active_defense, dmg)
        dmg -= absorbed
        active_defense -= absorbed
        if absorbed:
            log.append(f"barrier absorbs {absorbed} damage.")

    if dmg > 0:
        db.c.execute(
            "UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
            (dmg, player_id)
        )
        log.append(f"enemy hits you for {dmg} damage.")
    else:
        log.append("enemy attacks — barrier holds!")

    # blood_moon: extra hit is baked into base_hit at generation time via
    # apply_event_combat_modifiers(), so the regular attack already reflects it.
    # monster_rush: literal second strike
    if events["monster_rush"]:
        extra = max(0, int(ehit * 0.5) + random.randint(0, 3))
        db.c.execute(
            "UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
            (extra, player_id)
        )
        log.append(f"monster rush second strike: -{extra} hp.")

    db.conn.commit()
    return active_defense, log


def run_combat(player_id, enemy_id, events, active_defense=0):
    """Turn-based combat. Returns ('win'|'lose'|'flee', active_defense)."""
    log = []

    while True:
        estats, pstats, potions = draw_combat_screen(
            player_id, enemy_id, events, active_defense, log
        )
        flee_option = len(potions) + 2

        try:
            action = int(input("> ").strip())
        except ValueError:
            continue

        # ---- ATTACK ---- #
        if action == 1:
            dmg = player_attack(player_id, enemy_id)
            log = [f"you hit for {dmg} damage."]

            db.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
            if db.c.fetchone()[0] <= 0:
                db.c.execute("SELECT experience_drop FROM enemies WHERE id = ?", (enemy_id,))
                xp = db.c.fetchone()[0]
                gold_drop = random.randint(8, 30)
                db.c.execute(
                    "UPDATE players SET experience = experience + ?, kills = kills + 1 WHERE id = ?",
                    (xp, player_id)
                )
                db.c.execute(
                    "UPDATE player_stats SET gold = gold + ? WHERE player_id = ?",
                    (gold_drop, player_id)
                )
                db.conn.commit()

                drop = db.enemy_drop_potion(player_id)

                clear_screen()
                ascii_art.print_enemy_art(estats["type"])
                print()
                typewrite(f"  enemy defeated!", delay=0.02)
                typewrite(f"  +{xp} xp   +{gold_drop} gold", delay=0.02)
                db.c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
                row = db.c.fetchone()
                if row[1] >= db.experience_needed_for_next_level(row[0]):
                    db.level_up(player_id)
                if drop:
                    typewrite(f"  loot: {drop}", delay=0.02)
                input("\npress enter...")
                return "win", active_defense

            # Enemy retaliates
            active_defense, enemy_log = enemy_turn(
                player_id, enemy_id, events, active_defense
            )
            log += enemy_log

            db.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            if db.c.fetchone()[0] <= 0:
                db.c.execute("UPDATE players SET deaths = deaths + 1 WHERE id = ?", (player_id,))
                db.c.execute(
                    "UPDATE player_stats SET current_hp = max_hp/2 WHERE player_id = ?", (player_id,)
                )
                db.conn.commit()
                clear_screen()
                typewrite("  you have been defeated.", delay=0.03)
                input("\npress enter...")
                return "lose", 0

        # ---- USE POTION ---- #
        elif 2 <= action <= len(potions) + 1:
            pot_row = potions[action - 2]
            result  = db.apply_potion(player_id, pot_row["item"])

            if pot_row["amount"] <= 1:
                db.c.execute("DELETE FROM inventory WHERE rowid = ?", (pot_row["rowid"],))
            else:
                db.c.execute(
                    "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                    (pot_row["rowid"],)
                )
            db.conn.commit()

            log = []
            if result.get("heal"):
                log.append(f"restored {result['heal']} hp.")
            if result.get("bonus_hit"):
                log.append(f"attack surges +{result['bonus_hit']} hit.")
            if result.get("bonus_wisdom"):
                log.append(f"clarity +{result['bonus_wisdom']} wisdom.")
            if result.get("defense"):
                active_defense += result["defense"]
                log.append(f"barrier active: {active_defense} reduction.")

        # ---- FLEE ---- #
        elif action == flee_option:
            db.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
            ehit = db.c.fetchone()[0]
            flee_dmg = max(0, ehit // 2 - random.randint(0, 3))
            db.c.execute(
                "UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
                (flee_dmg, player_id)
            )
            db.conn.commit()
            clear_screen()
            typewrite(f"  you flee — taking {flee_dmg} damage on the way out.", delay=0.02)
            input("\npress enter...")
            return "flee", active_defense


# ------------------------------------------------------------------ #
#  DUNGEON  (STORED_PROCEDURE / DEADLOCK)                             #
# ------------------------------------------------------------------ #

DUNGEON_ROOM_COUNT  = 3   # non-boss rooms before the final chamber
TRAP_DAMAGE_PERCENT = 0.15  # trap deals 15% of max HP


def run_dungeon(player_id, node_name, enc_type, events):
    """Multi-room dungeon crawl for STORED_PROCEDURE (2) and DEADLOCK (3) nodes.

    Layout:
      Rooms 1..DUNGEON_ROOM_COUNT — each has a random encounter:
        * combat     (most common)
        * trap       — roll Wisdom to reduce damage; fail = full hit
        * rest site  — small heal, no enemy
      Final chamber — guaranteed combat + guaranteed loot INSERT on clear

    DEADLOCK flavour: all rooms have an extra "mirror enemy" that fights
    simultaneously (represented as a second enemy in the same combat via
    a doubled enemy hit stat, keeping it to one combat loop call).

    Returns True if the player cleared the dungeon, False if they fled/died.
    """
    is_deadlock = (enc_type == 3)
    label       = "DEADLOCK" if is_deadlock else "STORED_PROCEDURE"

    clear_screen()
    typewrite(f"  [ {node_name} ]  —  {label}", delay=0.02)
    if is_deadlock:
        typewrite("  two forces stir inside. neither will yield.", delay=0.02)
    else:
        typewrite("  the procedure begins. each step is scripted.", delay=0.02)
    input("\npress enter to enter...")

    total_rooms = DUNGEON_ROOM_COUNT + 1   # +1 for final chamber
    active_defense = 0

    for room_num in range(1, total_rooms + 1):
        is_final = (room_num == total_rooms)
        clear_screen()

        print(f"  [ {node_name} ]  —  Room {room_num}/{total_rooms}")
        if is_final:
            print("  *** FINAL CHAMBER ***")
        print()

        # Reload events each room in case something changed
        events = load_events()

        if is_final:
            room_type = "combat"
        else:
            roll = random.random()
            if roll < 0.55:
                room_type = "combat"
            elif roll < 0.80:
                room_type = "trap"
            else:
                room_type = "rest"

        # ---- TRAP ROOM ---- #
        if room_type == "trap":
            db.c.execute("SELECT base_wisdom + bonus_wisdom AS wis FROM player_stats WHERE player_id = ?",
                         (player_id,))
            wisdom = db.c.fetchone()["wis"]
            db.c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
            max_hp = db.c.fetchone()["max_hp"]

            trap_dmg_full = max(5, int(max_hp * TRAP_DAMAGE_PERCENT))
            # Wisdom check: each point of wisdom is a 0.5% chance to halve damage (cap 60%)
            dodge_chance = min(0.60, wisdom * 0.005)
            dodged = random.random() < dodge_chance
            trap_dmg = trap_dmg_full // 2 if dodged else trap_dmg_full

            typewrite("  CONSTRAINT VIOLATION — a trap fires.", delay=0.02)
            if dodged:
                typewrite(f"  your wisdom lets you sidestep the worst of it: -{trap_dmg} hp.", delay=0.02)
            else:
                typewrite(f"  you walk straight into it: -{trap_dmg} hp.", delay=0.02)

            db.c.execute(
                "UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
                (trap_dmg, player_id)
            )
            db.conn.commit()

            # Check if trap would have killed — keep player at 1 hp but warn
            db.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            if db.c.fetchone()["current_hp"] <= 1:
                typewrite("  barely alive.", delay=0.02)

            input("\npress enter to continue...")

        # ---- REST ROOM ---- #
        elif room_type == "rest":
            db.c.execute("SELECT max_hp, current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            row = db.c.fetchone()
            heal_amt = max(5, int(row["max_hp"] * 0.12))
            db.c.execute(
                "UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?",
                (heal_amt, player_id)
            )
            db.conn.commit()
            typewrite("  a brief respite — you catch your breath.", delay=0.02)
            typewrite(f"  +{heal_amt} hp restored.", delay=0.02)
            input("\npress enter to continue...")

        # ---- COMBAT ROOM ---- #
        else:
            enemy_id = db.generate_enemy(player_id, is_boss=False)

            # DEADLOCK: mirror enemy — double the hit stat to simulate two attackers
            if is_deadlock and not is_final:
                db.c.execute("UPDATE enemies SET base_hit = base_hit * 2 WHERE id = ?", (enemy_id,))
                db.conn.commit()
                typewrite("  two forms emerge — they move as one.", delay=0.02)
                print()

            db.apply_event_combat_modifiers(enemy_id, events)
            result, active_defense = run_combat(player_id, enemy_id, events, active_defense)

            if result == "lose":
                return False

            if result == "flee":
                typewrite("  you retreat from the dungeon.", delay=0.02)
                input("\npress enter...")
                return False

            # Tick the event counter after each combat encounter
            was_reset = db.tick_event_counter()
            if was_reset:
                events = load_events()
                clear_screen()
                typewrite("  the world shifts — all events have expired.", delay=0.02)
                input("\npress enter...")

    # ---- DUNGEON CLEARED — guaranteed loot ---- #
    clear_screen()
    typewrite(f"  [ {node_name} ] — CLEARED", delay=0.02)
    print()
    typewrite("  the final chamber falls silent.", delay=0.02)

    # Guaranteed loot: pick an unfound gear piece
    db.c.execute("SELECT id, name FROM weapons WHERE found = 0 ORDER BY RANDOM() LIMIT 1")
    loot_w = db.c.fetchone()
    db.c.execute("SELECT id, name FROM armors  WHERE found = 0 ORDER BY RANDOM() LIMIT 1")
    loot_a = db.c.fetchone()
    loot_choice = random.choice([l for l in [loot_w, loot_a] if l])

    if loot_choice:
        if loot_choice == loot_w:
            db.c.execute("UPDATE weapons SET found = 1 WHERE id = ?", (loot_choice["id"],))
        else:
            db.c.execute("UPDATE armors  SET found = 1 WHERE id = ?", (loot_choice["id"],))
        db.add_item(player_id, loot_choice["name"], 1)
        db.conn.commit()
        typewrite(f"  guaranteed loot: {loot_choice['name']}", delay=0.02)

    input("\npress enter...")
    return True


# ------------------------------------------------------------------ #
#  SHOP                                                                #
# ------------------------------------------------------------------ #

SHOP_STOCK_SIZE = 4


def run_shop(player_id, node_name, events):
    fateful_day = events["fateful_day"]

    db.c.execute(
        "SELECT * FROM weapons WHERE found = 0 ORDER BY RANDOM() LIMIT ?",
        (SHOP_STOCK_SIZE * 3,)
    )
    weapon_pool = list(db.c.fetchall())

    db.c.execute(
        "SELECT * FROM armors WHERE found = 0 ORDER BY RANDOM() LIMIT ?",
        (SHOP_STOCK_SIZE * 3,)
    )
    armor_pool = list(db.c.fetchall())

    combined = weapon_pool + armor_pool
    if fateful_day:
        def item_score(i):
            return i["bonus_hp"] + i["bonus_hit"] + i["bonus_wisdom"] + 1
        scores     = [item_score(i) for i in combined]
        gear_stock = random.choices(combined, weights=scores, k=min(SHOP_STOCK_SIZE, len(combined)))
    else:
        gear_stock = random.sample(combined, min(SHOP_STOCK_SIZE, len(combined)))

    all_potions  = db.get_potion_pool()
    if fateful_day:
        pw = [p[7] for p in all_potions]
    else:
        pw = [1 / (p[7] + 1) * 100 for p in all_potions]
    potion_stock = random.choices(all_potions, weights=pw, k=SHOP_STOCK_SIZE)

    def gear_price(item):
        return max(10, (item["bonus_hp"] // 10) + item["bonus_hit"]
                   + item["bonus_wisdom"] * 2 + item["hit_mult"] * 3)

    def gear_sell_price(item):
        return max(5, gear_price(item) // 2)

    def show_gear_stats(item, price, gold):
        kind       = "WEAPON" if item in weapon_pool else "ARMOR"
        affordable = "buy" if gold >= price else "can't afford"
        print(f"  [{kind}] {item['name']}")
        print(f"  Class:          {item['class_type']}")
        print(f"  Hit Multiplier: {item['hit_mult']}")
        print(f"  Bonus HP:       {item['bonus_hp']}")
        print(f"  Bonus Hit:      {item['bonus_hit']}")
        print(f"  Bonus Wisdom:   {item['bonus_wisdom']}")
        print(f"  Price:          {price}g  [{affordable}]")

    def show_potion_stats(pot, gold):
        pname, ptype, pheal, pbhit, pbwis, pbdef, pdur, pprice = pot
        affordable = "buy" if gold >= pprice else "can't afford"
        print(f"  [POTION] {pname}  ({ptype})")
        if pheal: print(f"  Heal:    +{pheal} hp")
        if pbhit: print(f"  Attack:  +{pbhit} hit  (lasts {pdur} rounds)")
        if pbwis: print(f"  Wisdom:  +{pbwis} wis  (lasts {pdur} rounds)")
        if pbdef: print(f"  Barrier: +{pbdef} dmg reduction  (lasts {pdur} rounds)")
        print(f"  Price:   {pprice}g  [{affordable}]")

    in_shop = True
    while in_shop:
        clear_screen()

        db.c.execute("SELECT gold FROM player_stats WHERE player_id = ?", (player_id,))
        gold = db.c.fetchone()["gold"]

        db.c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
        inv_items = db.c.fetchall()

        gear_end   = len(gear_stock)
        potion_end = gear_end + len(potion_stock)
        sell_end   = potion_end + len(inv_items)

        print(f"[ {node_name} ] — TRANSACTION")
        if fateful_day:
            print("  * FATEFUL DAY — rare stock available *")
        print(f"  gold: {gold}")
        print()

        print("  [ FOR SALE — GEAR ]")
        if gear_stock:
            for i, item in enumerate(gear_stock, 1):
                kind  = "WPN" if item in weapon_pool else "ARM"
                price = gear_price(item)
                tag   = "" if gold >= price else " (can't afford)"
                print(f"  ({i}) [{kind}] {item['name']}  —  {item['class_type']}  —  {price}g{tag}")
        else:
            print("  (no gear in stock)")
        print()

        print("  [ FOR SALE — POTIONS ]")
        for j, pot in enumerate(potion_stock, gear_end + 1):
            pname, ptype, pheal, pbhit, pbwis, pbdef, pdur, pprice = pot
            effects = []
            if pheal: effects.append(f"+{pheal}hp")
            if pbhit: effects.append(f"+{pbhit}hit")
            if pbwis: effects.append(f"+{pbwis}wis")
            if pbdef: effects.append(f"+{pbdef}barrier")
            tag = "" if gold >= pprice else " (can't afford)"
            print(f"  ({j}) [POT] {pname}  —  {', '.join(effects)}  —  {pprice}g{tag}")
        print()

        print("  [ SELL ]")
        if inv_items:
            for k, inv_row in enumerate(inv_items, potion_end + 1):
                db.c.execute("SELECT * FROM weapons WHERE name = ?", (inv_row["item"],))
                wdata = db.c.fetchone()
                db.c.execute("SELECT * FROM armors WHERE name = ?", (inv_row["item"],))
                adata = db.c.fetchone()
                idata = wdata or adata
                sv    = gear_sell_price(idata) if idata else 5
                print(f"  ({k}) {inv_row['item']}  x{inv_row['amount']}  —  sell for {sv}g")
        else:
            print("  (inventory empty)")
        print()
        print("  (0) leave shop")
        print()

        try:
            choice = int(input("> "))
        except ValueError:
            continue

        if choice == 0:
            in_shop = False

        elif 1 <= choice <= gear_end:
            item  = gear_stock[choice - 1]
            price = gear_price(item)
            clear_screen()
            show_gear_stats(item, price, gold)
            print()
            print("  (1) buy")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                if gold < price:
                    typewrite("  not enough gold.", delay=0.02)
                    input("\npress enter...")
                else:
                    db.c.execute("UPDATE player_stats SET gold = gold - ? WHERE player_id = ?",
                                 (price, player_id))
                    db.add_item(player_id, item["name"], 1)
                    if item in weapon_pool:
                        db.c.execute("UPDATE weapons SET found = 1 WHERE id = ?", (item["id"],))
                    else:
                        db.c.execute("UPDATE armors  SET found = 1 WHERE id = ?", (item["id"],))
                    db.conn.commit()
                    gear_stock.remove(item)
                    typewrite(f"  bought {item['name']} for {price}g.", delay=0.02)
                    input("\npress enter...")

        elif gear_end < choice <= potion_end:
            pot    = potion_stock[choice - gear_end - 1]
            pprice = pot[7]
            clear_screen()
            show_potion_stats(pot, gold)
            print()
            print("  (1) buy")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                if gold < pprice:
                    typewrite("  not enough gold.", delay=0.02)
                    input("\npress enter...")
                else:
                    db.c.execute("UPDATE player_stats SET gold = gold - ? WHERE player_id = ?",
                                 (pprice, player_id))
                    db.add_item(player_id, pot[0], 1)
                    db.conn.commit()
                    typewrite(f"  bought {pot[0]} for {pprice}g.", delay=0.02)
                    input("\npress enter...")

        elif potion_end < choice <= sell_end:
            inv_row = inv_items[choice - potion_end - 1]
            db.c.execute("SELECT * FROM weapons WHERE name = ?", (inv_row["item"],))
            wdata = db.c.fetchone()
            db.c.execute("SELECT * FROM armors WHERE name = ?", (inv_row["item"],))
            adata = db.c.fetchone()
            idata = wdata or adata
            sv    = gear_sell_price(idata) if idata else 5

            clear_screen()
            if idata:
                show_gear_stats(idata, gear_price(idata), gold)
            else:
                print(f"  {inv_row['item']}")
            print(f"  Sell value: {sv}g")
            print()
            print("  (1) sell")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                db.c.execute("UPDATE player_stats SET gold = gold + ? WHERE player_id = ?",
                             (sv, player_id))
                if inv_row["amount"] <= 1:
                    db.c.execute("DELETE FROM inventory WHERE rowid = ?", (inv_row["rowid"],))
                else:
                    db.c.execute(
                        "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                        (inv_row["rowid"],)
                    )
                db.conn.commit()
                typewrite(f"  sold {inv_row['item']} for {sv}g.", delay=0.02)
                input("\npress enter...")


# ------------------------------------------------------------------ #
#  EVENTS                                                              #
# ------------------------------------------------------------------ #

def load_events():
    db.c.execute("SELECT * FROM events LIMIT 1")
    row = db.c.fetchone()
    if row:
        return dict(row)
    return {
        "blood_moon": 0, "solar_eclipse": 0, "flood_omnya": 0,
        "monster_rush": 0, "fateful_day": 0, "encounters_since_reset": 0,
    }


def apply_solar_eclipse(player_id, events, remove=False):
    if not events["solar_eclipse"]:
        return
    db.c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = db.c.fetchone()[0]
    db.c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = db.c.fetchone()[0]
    if class_name != "The Indexer":
        return
    if remove:
        db.c.execute("UPDATE player_stats SET bonus_wisdom = bonus_wisdom / 2 WHERE player_id = ?",
                     (player_id,))
    else:
        db.c.execute("UPDATE player_stats SET bonus_wisdom = bonus_wisdom * 2 WHERE player_id = ?",
                     (player_id,))
    db.conn.commit()


def print_active_events(events):
    labels = {
        "blood_moon":    "BLOOD MOON    — enemies strike with doubled power",
        "solar_eclipse": "SOLAR ECLIPSE — The Indexer's wisdom surges",
        "flood_omnya":   "FLOOD OF OMNYA — some paths are inaccessible",
        "monster_rush":  "MONSTER RUSH  — enemies attack twice per round",
        "fateful_day":   "FATEFUL DAY   — rare loot floods the markets",
    }
    active = [v for k, v in labels.items() if events.get(k)]
    if active:
        remaining = db.EVENT_EXPIRY_ENCOUNTERS - events.get("encounters_since_reset", 0)
        print(f"  [ ACTIVE EVENTS ]  (expire in ~{remaining} encounters)")
        for e in active:
            print(f"  * {e}")
        print()


def run_constraint_encounter(player_id, node_name, events):
    """CONSTRAINT node — fire a world event, then a combat encounter with modifiers applied."""
    clear_screen()
    typewrite(f"  [ {node_name} ] — CONSTRAINT", delay=0.02)
    print()

    # Fire an event
    result = db.trigger_constraint_event(events)
    if result:
        key, name = result
        # Find the description from CONSTRAINT_EVENTS
        desc = next((e[2] for e in db.CONSTRAINT_EVENTS if e[0] == key), "")
        typewrite(f"  EVENT TRIGGERED: {name}", delay=0.03)
        typewrite(f"  {desc}", delay=0.02)
        print()
        # Reload events so the combat sees the new flag
        events = load_events()

        # Solar eclipse may need to be applied immediately for The Indexer
        if key == "solar_eclipse":
            apply_solar_eclipse(player_id, events, remove=False)
    else:
        typewrite("  the forest hums. no new events stir.", delay=0.02)
    input("\npress enter to face the encounter...")

    enemy_id = db.generate_enemy(player_id)
    db.apply_event_combat_modifiers(enemy_id, events)
    result_combat, _ = run_combat(player_id, enemy_id, events)

    # Tick the encounter counter — events may expire
    was_reset = db.tick_event_counter()
    if was_reset:
        events = load_events()
        clear_screen()
        typewrite("  the world settles — all active events have expired.", delay=0.02)
        input("\npress enter...")

    return result_combat, events


# ------------------------------------------------------------------ #
#  INVENTORY (paginated, with delete confirm)                          #
# ------------------------------------------------------------------ #

def show_inventory_screen(player_id):
    page = 0
    while True:
        clear_screen()
        db.c.execute(
            "SELECT rowid, item, amount FROM inventory WHERE player_id = ?",
            (player_id,)
        )
        items = db.c.fetchall()
        equipped_weapon, equipped_armor = get_equipped(player_id)

        total_pages = max(1, (len(items) + INV_PAGE_SIZE - 1) // INV_PAGE_SIZE)
        page        = max(0, min(page, total_pages - 1))
        page_items  = items[page * INV_PAGE_SIZE : (page + 1) * INV_PAGE_SIZE]

        if not items:
            print("  inventory empty")
        else:
            print(f"  [ INVENTORY ]  page {page + 1}/{total_pages}")
            print()
            for row in page_items:
                tag = " [EQUIPPED]" if row["item"] in (equipped_weapon, equipped_armor) else ""
                print(f"  {row['rowid']:3}  {row['item']}  x{row['amount']}{tag}")

        print()
        nav = []
        if page > 0:             nav.append("(p) prev")
        if page < total_pages-1: nav.append("(n) next")
        nav.append("(0) back")
        print("  " + "   ".join(nav))
        print("  choose item by rowid to inspect")
        print()

        raw = input("> ").strip().lower()

        if raw == "0":
            return
        elif raw == "n" and page < total_pages - 1:
            page += 1
            continue
        elif raw == "p" and page > 0:
            page -= 1
            continue

        try:
            choice = int(raw)
        except ValueError:
            continue

        # Inspect selected item
        selected_item = next((i for i in items if i["rowid"] == choice), None)
        if not selected_item:
            continue

        _inspect_item(player_id, selected_item, items)


def _inspect_item(player_id, selected_item, items):
    """Show item detail with equip/unequip and throw (with confirm) actions."""
    while True:
        equipped_weapon, equipped_armor = get_equipped(player_id)
        item_name = selected_item["item"]

        db.c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
        weapon_data = db.c.fetchone()
        db.c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
        armor_data = db.c.fetchone()

        clear_screen()
        if weapon_data:
            print_item_stats(weapon_data, f"WEAPON - {item_name}")
        elif armor_data:
            print_item_stats(armor_data, f"ARMOR  - {item_name}")
        else:
            print(f"  {item_name}  x{selected_item['amount']}")

        is_equipped = item_name in (equipped_weapon, equipped_armor)
        print("(1)", "unequip" if is_equipped else "use/equip")
        print("(2) throw")
        print("(3) go back")
        action = input("> ")

        if action == "1":
            if weapon_data:
                if is_equipped:
                    db.bonus_calc(db.BonusType.WEAPON, player_id=player_id, remove=True)
                    db.c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
                else:
                    db.c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (item_name, player_id))
                    db.bonus_calc(db.BonusType.WEAPON, player_id=player_id)
                db.conn.commit()
            elif armor_data:
                if is_equipped:
                    db.bonus_calc(db.BonusType.ARMOR, player_id=player_id, remove=True)
                    db.c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
                else:
                    db.c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (item_name, player_id))
                    db.bonus_calc(db.BonusType.ARMOR, player_id=player_id)
                db.conn.commit()
            return  # back to inventory list

        elif action == "2":
            # Confirm before deleting
            clear_screen()
            print(f"  throw away {item_name}?")
            print("  (1) yes, discard it")
            print("  (2) no, keep it")
            confirm = input("> ").strip()
            if confirm == "1":
                db.c.execute("DELETE FROM inventory WHERE rowid = ?", (selected_item["rowid"],))
                db.conn.commit()
                typewrite(f"  {item_name} discarded.", delay=0.02)
                input("\npress enter...")
                return  # item gone, back to list

        elif action == "3":
            return


# ------------------------------------------------------------------ #
#  ONE-TIME SETUP                                                      #
# ------------------------------------------------------------------ #

initialize_game()

try:
    # ------------------------------------------------------------------ #
    #  MAIN LOOP                                                           #
    # ------------------------------------------------------------------ #
    while run:

        # ---- MENU ---- #
        while menu:
            clear_screen()
            print("(1) new game")
            print("(2) load game")
            print("(3) reset database")
            print("(4) quit")
            choice = input("> ")

            if choice == "1":
                player_id = new_game()
                if player_id:
                    menu = False
                    play = True

            elif choice == "2":
                player_id = load_game()
                if player_id:
                    menu = False
                    play = True

            elif choice == "3":
                os.remove("game_data.db")
                db.reconnect()
                initialize_game()

            elif choice == "4":
                print("connection closed.")
                quit()

        # ---- PLAY ---- #
        while play:
            clear_screen()
            print("(0) adventure")
            print("(1) inventory")
            print("(2) equipped items and stats")
            print("(3) back to menu")
            choice = input("> ")

            if choice == "0":
                adventuring = True
                play = False

            elif choice == "1":
                show_inventory_screen(player_id)

            elif choice == "2":
                clear_screen()
                equipped_weapon, equipped_armor = get_equipped(player_id)
                db.c.execute("SELECT * FROM weapons WHERE name = ?", (equipped_weapon,))
                weapon_data = db.c.fetchone()
                db.c.execute("SELECT * FROM armors WHERE name = ?", (equipped_armor,))
                armor_data = db.c.fetchone()

                w_label = equipped_weapon if equipped_weapon else "nothing"
                a_label = equipped_armor  if equipped_armor  else "nothing"

                print("==================================================")
                print(f"weapon: {w_label}  |  armor: {a_label}")
                print("==================================================")
                if weapon_data:
                    print_item_stats(weapon_data, "WEAPON")
                if armor_data:
                    print_item_stats(armor_data, "ARMOR")
                if not weapon_data and not armor_data:
                    print("No items equipped.")
                print("==================================================")
                input("\npress enter to show stats...")
                clear_screen()
                show_stats(player_id)
                input("\npress enter to go back...")

            elif choice == "3":
                play = False
                menu = True

        # ------------------------------------------------------------------ #
        #  ADVENTURE                                                           #
        # ------------------------------------------------------------------ #
        while adventuring:
            clear_screen()
            events = load_events()

            print("enter a seed (or press enter to generate one):")
            seed_input = input("> ").strip()

            if seed_input.isdigit():
                custom_seed = int(seed_input)
                run_id, current_node_id, seed = db.init_run(player_id, custom_seed)
            else:
                run_id, current_node_id, seed = db.init_run(player_id)

            clear_screen()
            typewrite("querying the world index...", delay=0.01)
            typewrite(f"seed: {seed}", delay=0.005)
            print()

            apply_solar_eclipse(player_id, events, remove=False)
            print_active_events(events)
            input("press enter to begin...")

            BRANCH_LABEL   = ["<-", " o", "->"]
            ENCOUNTER_NAME = {
                -1: "START",
                0:  "TRANSACTION",
                1:  "QUERY",
                2:  "STORED_PROCEDURE",
                3:  "DEADLOCK",
                4:  "CONSTRAINT",
                5:  "OVERFLOW",
            }

            run_lost     = False
            path_running = True

            while path_running:
                clear_screen()
                node     = db.get_path_node(current_node_id)
                enc_type = node["encounter_type"]

                print(f"[ {node['name']} ] — {ENCOUNTER_NAME.get(enc_type, '???')}")
                print(node["description"] or "")
                print()

                # Reload events before every node
                events = load_events()

                # ---- Dispatch encounter by type ---- #

                if enc_type == -1:
                    pass  # START — no encounter

                elif enc_type == 0:
                    db.register_shop_visit(player_id, node["id"])
                    run_shop(player_id, node["name"], events)

                elif enc_type in (1,):
                    # QUERY — standard combat
                    enemy_id = db.generate_enemy(player_id)
                    db.apply_event_combat_modifiers(enemy_id, events)
                    result, _ = run_combat(player_id, enemy_id, events)

                    if result == "lose":
                        run_lost    = True
                        path_running = False
                        adventuring  = False
                        play         = True
                        break

                    was_reset = db.tick_event_counter()
                    if was_reset:
                        events = load_events()
                        clear_screen()
                        typewrite("  the world settles — all active events have expired.", delay=0.02)
                        input("\npress enter...")

                elif enc_type in (2, 3):
                    # STORED_PROCEDURE / DEADLOCK — dungeon crawl
                    cleared = run_dungeon(player_id, node["name"], enc_type, events)
                    if not cleared:
                        run_lost    = True
                        path_running = False
                        adventuring  = False
                        play         = True
                        break

                elif enc_type == 4:
                    # CONSTRAINT — fire event then fight
                    if events["flood_omnya"]:
                        clear_screen()
                        typewrite("  FLOOD OF OMNYA — the path is submerged. you turn back.", delay=0.02)
                        input("\npress enter...")
                    else:
                        result_combat, events = run_constraint_encounter(
                            player_id, node["name"], events
                        )
                        if result_combat == "lose":
                            run_lost    = True
                            path_running = False
                            adventuring  = False
                            play         = True
                            break

                elif enc_type == 5:
                    # OVERFLOW — boss
                    clear_screen()
                    typewrite("  [ the air thickens. something massive stirs. ]", delay=0.03)
                    print()
                    enemy_id = db.generate_enemy(player_id, is_boss=True)
                    db.apply_event_combat_modifiers(enemy_id, events)
                    result, _ = run_combat(player_id, enemy_id, events)

                    if result == "lose":
                        run_lost    = True
                        path_running = False
                        adventuring  = False
                        play         = True
                        break

                    # Boss kill — unique named loot
                    db.c.execute("SELECT type FROM enemies WHERE id = ?", (enemy_id,))
                    boss_type = db.c.fetchone()["type"]
                    boss_drops = db.drop_boss_loot(player_id, boss_type)
                    if boss_drops:
                        clear_screen()
                        typewrite("  [ UNIQUE LOOT ]", delay=0.03)
                        for item_name, item_type in boss_drops:
                            typewrite(f"  {item_type.upper()}: {item_name}", delay=0.02)
                        input("\npress enter...")

                # Mark node finished
                db.finish_node(node["id"])

                # ---- Get next choices ---- #
                children = db.get_path_children(node["id"])

                if not children:
                    clear_screen()
                    typewrite("run complete. returning to camp...", delay=0.03)
                    apply_solar_eclipse(player_id, events, remove=True)
                    input("\npress enter...")
                    path_running = False
                    adventuring  = False
                    play         = True
                    break

                # ---- Navigation menu ---- #
                clear_screen()
                print(f"[ {node['name']} ] — cleared")
                print()
                print_active_events(events)
                print("choose your next path:")
                print()

                shops       = db.get_visited_shops(player_id)
                shop_offset = len(children)

                for i, child in enumerate(children, 1):
                    label   = BRANCH_LABEL[child["branch"]]
                    enc     = ENCOUNTER_NAME.get(child["encounter_type"], "???")
                    flooded = (child["encounter_type"] == 4 and events["flood_omnya"])
                    suffix  = "  [FLOODED]" if flooded else ""
                    print(f"  {label}  ({i}) {child['name']}  — {enc}{suffix}")

                print()
                if shops:
                    print("  [ return to a shop ]")
                    for j, shop in enumerate(shops, shop_offset + 1):
                        print(f"         ({j}) {shop['name']}")
                    print()

                print("  (0) flee — return to camp")
                print()

                try:
                    choice = int(input("> "))
                except ValueError:
                    continue

                if choice == 0:
                    apply_solar_eclipse(player_id, events, remove=True)
                    path_running = False
                    adventuring  = False
                    play         = True

                elif 1 <= choice <= len(children):
                    chosen          = children[choice - 1]
                    current_node_id = chosen["id"]
                    db.move_to_node(player_id, current_node_id)

                elif shops and shop_offset < choice <= shop_offset + len(shops):
                    chosen_shop     = shops[choice - shop_offset - 1]
                    current_node_id = chosen_shop["id"]
                    db.move_to_node(player_id, current_node_id)

            if run_lost:
                clear_screen()
                typewrite("  you have fallen. the run is over.", delay=0.03)
                apply_solar_eclipse(player_id, events, remove=True)
                input("\npress enter...")

except KeyboardInterrupt:
    print("\nconnection closed.")
