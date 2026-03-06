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


def clear_screen():
    """Push old output out of view."""
    print("\n" * 100)


def typewrite(text, delay=0.03):
    """Print text one character at a time for a typewriter effect."""
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
    """Prompt for a username and class, then INSERT a new player into the db."""
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
    """SELECT existing saves and let the player pick one by ID."""
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
    """SELECT and return (equipped_weapon_name, equipped_armor_name) for the player."""
    db.c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    row = db.c.fetchone()
    equipped_weapon = row["equipped_weapon"] if row else None

    db.c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
    row = db.c.fetchone()
    equipped_armor = row["equipped_armor"] if row else None

    return equipped_weapon, equipped_armor


def print_item_stats(data, label):
    """Print a formatted stat block for a weapon or armor row."""
    print("====================")
    print(f"[{label}]")
    print("| Class:          ", data["class_type"])
    print("| Hit Multiplier: ", data["hit_mult"])
    print("| Bonus HP:       ", data["bonus_hp"])
    print("| Bonus Hit:      ", data["bonus_hit"])
    print("| Bonus Wisdom:   ", data["bonus_wisdom"])
    print("====================")

def show_stats(player_id):
    """Fetch and print the player's current stats."""
    db.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
    username = db.c.fetchone()["username"]
    db.c.execute("""
        SELECT
            base_hp, bonus_hp, max_hp, 
            current_hp, gold, base_hit,
            bonus_hit, base_wisdom, bonus_wisdom
        FROM player_stats
        WHERE player_id = ?""",
        (player_id,)
    )
    stats = db.c.fetchone()
    db.c.execute("SELECT level, experience, deaths FROM players WHERE id = ?", (player_id,))
    player_info = db.c.fetchone()
    
    experience_to_next_level = 100 + (player_info['level'] - 1) * 50

    header = f"=== [ {username} ] ==="

    print(header)
    print(f"Level: {player_info['level']}  |  XP: {player_info['experience']} | next level in {experience_to_next_level - player_info['experience']} xp")
    print(f"HP: {stats['current_hp']}/{stats['max_hp']}  (Base: {stats['base_hp']} + Bonus: {stats['bonus_hp']})")
    print(f"Hit:  {stats['base_hit'] + stats['bonus_hit']}( Base: {stats['base_hit']} + Bonus: {stats['bonus_hit']})")
    print(f"Wisdom: {stats['base_wisdom'] + stats['bonus_wisdom']} (Base: {stats['base_wisdom']} + Bonus: {stats['bonus_wisdom']})")
    print(f"Deaths: {player_info['deaths']}")
    print(f"Gold: {stats['gold']}")
    print("=" * len(header))

# ------------------------------------------------------------------ #
#  COMBAT                                                            #
# ------------------------------------------------------------------ #

def get_combat_potions(player_id):
    """Return inventory rows that are potions."""
    potion_names = {p[0] for p in db.get_potion_pool()}
    db.c.execute(
        "SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,)
    )
    return [i for i in db.c.fetchall() if i["item"] in potion_names]


def draw_combat_screen(player_id, enemy_id, events, active_defense, log):
    """Render the full combat screen and return fetched stats and potions."""
    db.c.execute(
        "SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (player_id,)
    )
    pstats = db.c.fetchone()
    db.c.execute(
        "SELECT type, base_hp FROM enemies WHERE id = ?", (enemy_id,)
    )
    estats = db.c.fetchone()

    clear_screen()
    ascii_art.print_enemy_art(estats["type"])
    print()
    print(f"  [ {estats['type']} ]")
    print(f"  HP: {estats['base_hp']}")
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
    print(f"  [ YOU ]   HP: {pstats['current_hp']}/{pstats['max_hp']}{barrier_str}")
    print()

    potions = get_combat_potions(player_id)
    print("  (1) attack")
    for i, pot in enumerate(potions, 2):
        print(f"  ({i}) use {pot['item']}  x{pot['amount']}")
    print(f"  ({len(potions) + 2}) flee")
    print()

    return estats, pstats, potions


def player_attack(player_id, enemy_id):
    """Player deals damage to enemy. Returns damage dealt."""
    import random
    db.c.execute(
        "SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,)
    )
    pstats = db.c.fetchone()
    dmg = max(1, pstats["base_hit"] + pstats["bonus_hit"] - random.randint(0, 5))
    db.c.execute(
        "UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (dmg, enemy_id)
    )
    db.conn.commit()
    return dmg


def enemy_turn(player_id, enemy_id, events, active_defense):
    """Enemy attacks player. Returns (active_defense, log_lines)."""
    import random
    log = []

    db.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    ehit = db.c.fetchone()[0]

    dmg = max(0, ehit - random.randint(0, 5))

    # Barrier absorbs first
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

    if events["blood_moon"]:
        extra = max(0, int(ehit * 0.6) + random.randint(0, 4))
        db.c.execute(
            "UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
            (extra, player_id)
        )
        log.append(f"blood moon surge: -{extra} hp.")

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
    """Turn-based combat. Returns ('win'|'lose'|'flee', active_defense).

    Turn order:
      1. Player chooses: attack / use potion / flee
      2. Attack: player hits first. If enemy survives, enemy retaliates.
      3. Potion: applied instantly, enemy does NOT counter-attack.
      4. Flee: enemy gets one free hit, then combat ends.
    """
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

            # Check enemy death
            db.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
            if db.c.fetchone()[0] <= 0:
                db.c.execute(
                    "SELECT experience_drop FROM enemies WHERE id = ?", (enemy_id,)
                )
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

            # Check player death
            db.c.execute(
                "SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,)
            )
            if db.c.fetchone()[0] <= 0:
                db.c.execute(
                    "UPDATE players SET deaths = deaths + 1 WHERE id = ?", (player_id,)
                )
                db.c.execute(
                    "UPDATE player_stats SET current_hp = max_hp/2 WHERE player_id = ?", (player_id,)
                )
                db.conn.commit()
                clear_screen()
                typewrite("  you have been defeated.", delay=0.03)
                input("\npress enter...")
                return "lose", 0

        # ---- USE POTION (free action, no enemy counter) ---- #
        elif 2 <= action <= len(potions) + 1:
            pot_row = potions[action - 2]
            result  = db.apply_potion(player_id, pot_row["item"])

            if pot_row["amount"] <= 1:
                db.c.execute(
                    "DELETE FROM inventory WHERE rowid = ?", (pot_row["rowid"],)
                )
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

#  SHOP                                                                #
# ------------------------------------------------------------------ #

SHOP_STOCK_SIZE = 4   # number of items the shop offers

def run_shop(player_id, node_name, events):
    """Interactive shop. Numbers select an item to inspect — then confirm to buy/sell.

    Event modifiers:
      fateful_day — stock weighted toward powerful items
    """
    import random

    fateful_day = events["fateful_day"]

    # --- Build gear stock ---
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
        scores    = [item_score(i) for i in combined]
        gear_stock = random.choices(combined, weights=scores, k=min(SHOP_STOCK_SIZE, len(combined)))
    else:
        gear_stock = random.sample(combined, min(SHOP_STOCK_SIZE, len(combined)))

    # --- Build potion stock ---
    all_potions = db.get_potion_pool()
    if fateful_day:
        pw = [p[7] for p in all_potions]
    else:
        pw = [1 / (p[7] + 1) * 100 for p in all_potions]
    potion_stock = random.choices(all_potions, weights=pw, k=SHOP_STOCK_SIZE)

    # --- Pricing helpers ---
    def gear_price(item):
        return max(10, (item["bonus_hp"] // 10) + item["bonus_hit"]
                   + item["bonus_wisdom"] * 2 + item["hit_mult"] * 3)

    def gear_sell_price(item):
        return max(5, gear_price(item) // 2)

    def show_gear_stats(item, price, gold):
        """Print a stat card for a weapon or armor."""
        kind = "WEAPON" if item in weapon_pool else "ARMOR"
        affordable = "buy" if gold >= price else "can't afford"
        print(f"  [{kind}] {item['name']}")
        print(f"  Class:          {item['class_type']}")
        print(f"  Hit Multiplier: {item['hit_mult']}")
        print(f"  Bonus HP:       {item['bonus_hp']}")
        print(f"  Bonus Hit:      {item['bonus_hit']}")
        print(f"  Bonus Wisdom:   {item['bonus_wisdom']}")
        print(f"  Price:          {price}g  [{affordable}]")

    def show_potion_stats(pot, gold):
        """Print a stat card for a potion."""
        pname, ptype, pheal, pbhit, pbwis, pbdef, pdur, pprice = pot
        affordable = "buy" if gold >= pprice else "can't afford"
        print(f"  [POTION] {pname}  ({ptype})")
        if pheal: print(f"  Heal:     +{pheal} hp")
        if pbhit: print(f"  Attack:   +{pbhit} hit  (lasts {pdur} rounds)")
        if pbwis: print(f"  Wisdom:   +{pbwis} wis  (lasts {pdur} rounds)")
        if pbdef: print(f"  Barrier:  +{pbdef} dmg reduction  (lasts {pdur} rounds)")
        print(f"  Price:    {pprice}g  [{affordable}]")

    # --- Main shop loop ---
    in_shop = True
    while in_shop:
        clear_screen()

        db.c.execute(
            "SELECT gold FROM player_stats WHERE player_id = ?", (player_id,)
        )
        gold = db.c.fetchone()["gold"]

        db.c.execute(
            "SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,)
        )
        inv_items = db.c.fetchall()

        # --- Offsets ---
        gear_end    = len(gear_stock)                        # 1..gear_end
        potion_end  = gear_end + len(potion_stock)           # gear_end+1..potion_end
        sell_end    = potion_end + len(inv_items)            # potion_end+1..sell_end

        # --- Display ---
        print(f"[ {node_name} ] — TRANSACTION")
        if fateful_day:
            print("  * FATEFUL DAY — rare stock available *")
        print(f"  gold: {gold}")
        print()

        print("  [ FOR SALE — GEAR ]")
        if gear_stock:
            for i, item in enumerate(gear_stock, 1):
                kind = "WPN" if item in weapon_pool else "ARM"
                price = gear_price(item)
                tag = "" if gold >= price else " (can't afford)"
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
                sv = gear_sell_price(idata) if idata else 5
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

        # --- Leave ---
        if choice == 0:
            in_shop = False

        # --- Inspect & buy gear ---
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
                    db.c.execute(
                        "UPDATE player_stats SET gold = gold - ? WHERE player_id = ?",
                        (price, player_id)
                    )
                    db.add_item(player_id, item["name"], 1)
                    if item in weapon_pool:
                        db.c.execute(
                            "UPDATE weapons SET found = 1 WHERE id = ?", (item["id"],)
                        )
                    else:
                        db.c.execute(
                            "UPDATE armors SET found = 1 WHERE id = ?", (item["id"],)
                        )
                    db.conn.commit()
                    gear_stock.remove(item)
                    typewrite(f"  bought {item['name']} for {price}g.", delay=0.02)
                    input("\npress enter...")

        # --- Inspect & buy potion ---
        elif gear_end < choice <= potion_end:
            pot   = potion_stock[choice - gear_end - 1]
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
                    db.c.execute(
                        "UPDATE player_stats SET gold = gold - ? WHERE player_id = ?",
                        (pprice, player_id)
                    )
                    db.add_item(player_id, pot[0], 1)
                    db.conn.commit()
                    typewrite(f"  bought {pot[0]} for {pprice}g.", delay=0.02)
                    input("\npress enter...")

        # --- Inspect & sell inventory item ---
        elif potion_end < choice <= sell_end:
            inv_row = inv_items[choice - potion_end - 1]
            db.c.execute("SELECT * FROM weapons WHERE name = ?", (inv_row["item"],))
            wdata = db.c.fetchone()
            db.c.execute("SELECT * FROM armors WHERE name = ?", (inv_row["item"],))
            adata = db.c.fetchone()
            idata = wdata or adata

            sv = gear_sell_price(idata) if idata else 5

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
                db.c.execute(
                    "UPDATE player_stats SET gold = gold + ? WHERE player_id = ?",
                    (sv, player_id)
                )
                if inv_row["amount"] <= 1:
                    db.c.execute(
                        "DELETE FROM inventory WHERE rowid = ?", (inv_row["rowid"],)
                    )
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
    """SELECT the events row. Returns a dict of event flags (all 0 if no row exists)."""
    db.c.execute("SELECT * FROM events LIMIT 1")
    row = db.c.fetchone()
    if row:
        return dict(row)
    # Default — no active events
    return {
        "blood_moon":   0,
        "solar_eclipse": 0,
        "flood_omnya":  0,
        "monster_rush": 0,
        "fateful_day":  0,
    }


def apply_solar_eclipse(player_id, events, remove=False):
    """Solar eclipse: double (or halve) The Indexer's wisdom bonus for the run."""
    if not events["solar_eclipse"]:
        return

    db.c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = db.c.fetchone()[0]
    db.c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = db.c.fetchone()[0]

    if class_name != "The Indexer":
        return

    if remove:
        db.c.execute(
            "UPDATE player_stats SET bonus_wisdom = bonus_wisdom / 2 WHERE player_id = ?",
            (player_id,)
        )
    else:
        db.c.execute(
            "UPDATE player_stats SET bonus_wisdom = bonus_wisdom * 2 WHERE player_id = ?",
            (player_id,)
        )
    db.conn.commit()


def print_active_events(events):
    """Print a summary of any active world events."""
    labels = {
        "blood_moon":    "BLOOD MOON    — enemies strike with doubled power",
        "solar_eclipse": "SOLAR ECLIPSE — The Indexer's wisdom surges",
        "flood_omnya":   "FLOOD OF OMNYA — some paths are inaccessible",
        "monster_rush":  "MONSTER RUSH  — enemies attack twice per round",
        "fateful_day":   "FATEFUL DAY   — rare loot floods the markets",
    }
    active = [v for k, v in labels.items() if events.get(k)]
    if active:
        print("  [ ACTIVE EVENTS ]")
        for e in active:
            print(f"  * {e}")
        print()


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

            # -- Adventure -- #
            if choice == "0":
                adventuring = True
                play = False

            # -- Inventory -- #
            elif choice == "1":
                inventory = True

                while inventory:
                    clear_screen()

                    db.c.execute(
                        "SELECT rowid, item, amount FROM inventory WHERE player_id = ?",
                        (player_id,)
                    )
                    items = db.c.fetchall()

                    equipped_weapon, equipped_armor = get_equipped(player_id)

                    if not items:
                        print("inventory empty")
                    else:
                        for row in items:
                            tag = " [EQUIPPED]" if row["item"] in (equipped_weapon, equipped_armor) else ""
                            print(f"{row['rowid']}  {row['item']}  x{row['amount']}{tag}")

                    print("\n(0) to exit")
                    print("choose item by number")

                    try:
                        choice = int(input("> "))
                    except ValueError:
                        continue

                    if choice == 0:
                        inventory = False
                        continue

                    selecting_item = True
                    inventory = False

                    while selecting_item:
                        equipped_weapon, equipped_armor = get_equipped(player_id)

                        selected_item = next((i for i in items if i["rowid"] == choice), None)

                        if not selected_item:
                            clear_screen()
                            print("Item not found.")
                            selecting_item = False
                            inventory = True
                            break

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
                            print(f"(no stat data found for '{item_name}')")

                        is_equipped = item_name in (equipped_weapon, equipped_armor)

                        print("(1)", "unequip" if is_equipped else "use/equip")
                        print("(2) throw")
                        print("(3) go back")
                        print("choose action:")
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

                            selecting_item = False
                            inventory = True

                        elif action == "2":
                            db.c.execute("DELETE FROM inventory WHERE rowid = ?", (selected_item["rowid"],))
                            db.conn.commit()
                            selecting_item = False
                            inventory = True

                        elif action == "3":
                            selecting_item = False
                            inventory = True

            # -- Equipped items and stats summary -- #
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

            # --- Load active world events ---
            events = load_events()

            # --- Seed input: generate random or let player enter one ---
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

            # Apply solar eclipse buff for The Indexer at run start
            apply_solar_eclipse(player_id, events, remove=False)

            # Print any active events so player knows what they're walking into
            print_active_events(events)
            input("press enter to begin...")

            # --- Branch direction labels (index = path.branch value) ---
            BRANCH_LABEL = ["<-", " o", "->"]

            # --- Encounter type display names ---
            ENCOUNTER_NAME = {
                -1: "START",
                0:  "TRANSACTION",
                1:  "QUERY",
                2:  "STORED_PROCEDURE",
                3:  "DEADLOCK",
                4:  "CONSTRAINT",
                5:  "OVERFLOW",
            }

            run_lost = False   # set True if player dies — ends the run immediately
            path_running = True

            while path_running:
                clear_screen()

                node     = db.get_path_node(current_node_id)
                enc_type = node["encounter_type"]

                print(f"[ {node['name']} ] — {ENCOUNTER_NAME.get(enc_type, '???')}")
                print(node["description"] or "")
                print()

                # ---- Dispatch encounter by type ---- #

                if enc_type == -1:
                    # START — no encounter, fall through to path choice
                    pass

                elif enc_type == 0:
                    # TRANSACTION — shop
                    db.register_shop_visit(player_id, node["id"])
                    run_shop(player_id, node["name"], events)

                elif enc_type in (1, 2, 3, 4):
                    # QUERY / STORED_PROCEDURE / DEADLOCK / CONSTRAINT — all combat
                    # CONSTRAINT nodes (forests) additionally check flood_omnya
                    if enc_type == 4 and events["flood_omnya"]:
                        clear_screen()
                        typewrite("  FLOOD OF OMNYA — the path is submerged. you turn back.", delay=0.02)
                        input("\npress enter...")
                        # Skip this node — treat as cleared without a fight
                    else:
                        enemy_id = db.generate_enemy(player_id)
                        result, _ = run_combat(player_id, enemy_id, events)

                        if result == "lose":
                            run_lost = True
                            path_running = False
                            adventuring = False
                            play = True
                            break

                elif enc_type == 5:
                    # OVERFLOW — boss (same combat, just presented differently)
                    clear_screen()
                    typewrite("  [ the air thickens. something massive stirs. ]", delay=0.03)
                    print()
                    enemy_id = db.generate_enemy(player_id, is_boss=True)

                    result, _ = run_combat(player_id, enemy_id, events)

                    if result == "lose":
                        run_lost = True
                        path_running = False
                        adventuring = False
                        play = True
                        break

                # Mark node finished
                db.finish_node(node["id"])

                # ---- Get next choices ---- #
                children = db.get_path_children(node["id"])

                if not children:
                    # Leaf cleared — run complete
                    clear_screen()
                    typewrite("run complete. returning to camp...", delay=0.03)
                    # Undo solar eclipse buff now that the run is over
                    apply_solar_eclipse(player_id, events, remove=True)
                    input("\npress enter...")
                    path_running = False
                    adventuring = False
                    play = True
                    break

                # ---- Build navigation menu ---- #
                clear_screen()
                print(f"[ {node['name']} ] — cleared")
                print()
                print_active_events(events)
                print("choose your next path:")
                print()

                shops      = db.get_visited_shops(player_id)
                shop_offset = len(children)

                for i, child in enumerate(children, 1):
                    label = BRANCH_LABEL[child["branch"]]
                    enc   = ENCOUNTER_NAME.get(child["encounter_type"], "???")
                    # Grey out flooded CONSTRAINT nodes
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
                    adventuring = False
                    play = True

                elif 1 <= choice <= len(children):
                    chosen = children[choice - 1]
                    current_node_id = chosen["id"]
                    db.move_to_node(player_id, current_node_id)

                elif shops and shop_offset < choice <= shop_offset + len(shops):
                    chosen_shop = shops[choice - shop_offset - 1]
                    current_node_id = chosen_shop["id"]
                    db.move_to_node(player_id, current_node_id)

            if run_lost:
                clear_screen()
                typewrite("  you have fallen. the run is over.", delay=0.03)
                apply_solar_eclipse(player_id, events, remove=True)
                input("\npress enter...")

except KeyboardInterrupt:
    print("\nconnection closed.")
