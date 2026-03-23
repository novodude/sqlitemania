import os
import time
import random
import sys, select
from datetime import datetime
import game_engine as ge
import ascii_art
import sys, termios, tty, select

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)


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

# Randomness seeding
seed = datetime.now().timestamp()
random.seed(seed)

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


def show_useless_tip():
    tips = [
        "tip: dying is just the game's way of telling you to get better.",
        "tip: enemies with more HP take more hits to kill.",
        "tip: if you run out of HP, you lose.",
        "tip: bytes are like gold, but worse.\n\tyou have to malloc them.",
        "tip: the boss will not negotiate.",
        "tip: reading the tutorial does not guarantee survival.",
        "tip: potions are single-use.\n\tunlike your mistakes.",
        "tip: higher levels have harder enemies.\n\tstay safe out there.",
        "tip: fleeing costs HP.\n\tstanding still also costs HP.",
        "tip: the schema does not care about your feelings.",
        "tip: critting twice in a row is not a strategy.\n\tit's luck. probably.",
        "tip: shops restock every run.\n\tyour dignity does not.",
        "tip: DEADLOCK nodes have enemies that hit twice.\n\tjust so you know.",
        "tip: if everything seems fine,\n\tyou may have missed something.",
        "tip: you can have at most 3 lives.\n\tlosing them all resets everything. no exceptions.",
        "tip: gear sets unlock every 5 clears.\n\tkeep clearing.",
        "tip: the OVERFLOW bosses are named.\n\tthey remember you. probably.",
        "tip: rest nodes exist.\n\tuse them. please.",
        "tip: world events can stack.\n\tthis is rarely good news for you.",
        "tip: the archivist has seen worse than you.\n\tsignificantly worse.",
        "tip: buying something doesn't mean you know how to use it.",
        "tip: your bytes reset on a death wipe.\n\tspend them before you die.",
        "tip: you cannot buy the same potion twice from the same shop.",
        "tip: critting does double damage.\n\tnot triple. double.",
        "tip: longer runs appear at higher levels.\n\tplan accordingly.",
        "tip: python uses indentation instead of braces.\n\tone wrong space and everything is your fault.",
        "tip: python is 'readable'.\n\tthis is why you can read exactly what went wrong.",
        "tip: python has a GIL.\n\tnobody fully understands it. this is fine.",
        "tip: python 2 is dead.\n\tif you're still using it, so is your project.",
        "tip: 'import antigravity' is a real python module.\n\tit opens a comic. this is peak engineering.",
        "tip: javascript: where 0 == '0' is true,\n\t0 == [] is true,\n\tbut '0' == [] is false.\n\ttrust nothing.",
        "tip: NaN === NaN is false in javascript.\n\tthe language is consistent about being inconsistent.",
        "tip: javascript was made in 10 days.\n\tyou can tell.",
        "tip: typeof null === 'object' in javascript.\n\tthis is a bug from 1995. it will never be fixed.",
        "tip: node.js:\n\tbecause sometimes one language doing weird things isn't enough.",
        "tip: java: write once,\n\tdebug everywhere.",
        "tip: java has been around since 1995\n\tand is still asking you to update it.",
        "tip: knock knock.\n\twho's there?\n\tvery long pause... java.",
        "tip: java developer: we have a problem.\n\talso java developer: let's use more classes.",
        "tip: in java,\n\teverything is an object except the things that aren't.",
        "tip: c gives you enough rope to hang yourself.\n\tc++ ships the gallows preassembled.",
        "tip: in c,\n\tyou manage memory manually.\n\tit goes well. always.",
        "tip: segmentation fault (core dumped).\n\tthat's it. that's the whole error message.",
        "tip: c++ has 11 ways to initialize a variable.\n\tnone of them feel right.",
        "tip: undefined behavior in c++ means anything can happen.\n\tand it will.",
        "tip: php:\n\tthe only language where the documentation apologizes.",
        "tip: php was designed by accident\n\tand then kept going by momentum.",
        "tip: in php,\n\tstrpos returns false or 0.\n\tboth are falsy.\n\tgood luck.",
        "tip: php has mysql_query, mysqli_query, and PDO.\n\tall do the same thing.\n\tnone agree on how.",
        "tip: go doesn't have generics.\n\tit didn't need them.\n\texcept when it did.\n\tso now it does.",
        "tip: go:\n\tif err != nil { return err }\n\trepeated until your wrist gives out.",
        "tip: go compiles fast\n\tbecause it doesn't do very much.\n\tthis is a feature.",
        "tip: rust won't let you shoot yourself in the foot.\n\tit will, however, make you justify why you wanted to.",
        "tip: the rust borrow checker is smarter than you.\n\tit knows this.\n\tyou'll come to accept it.",
        "tip: rust developers have been voting it 'most loved language' for 9 years.\n\tthey are not okay.",
        "tip: rewriting it in rust will not fix your architecture.\n\tit will fix it faster though.",
        "tip: css:\n\tthe language where centering a div has caused more therapy sessions than any other technology.",
        "tip: !important in css means\n\t'i give up understanding why this doesn't work'.",
        "tip: css is turing complete.\n\tthis should terrify you.",
        "tip: two css properties walk into a bar.\n\tevery stool in the restaurant falls over.",
        "tip: a sql query walks into a bar,\n\tsees two tables and says\n\t'can i JOIN you?'",
        "tip: DROP TABLE is permanent.\n\tthere is no undo.\n\task me how I know.",
        "tip: select * from production where id = 1;\n\t500,000 rows returned.\n\tyou're welcome.",
        "tip: 99 bugs in the code.\n\tfix one.\n\t127 bugs in the code.",
        "tip: the most used programming language is profanity.",
        "tip: if at first you don't succeed,\n\tcall it version 1.0.",
        "tip: software can be fast, reliable, or cheap.\n\tpick two.",
        "tip: it's not a bug.\n\tit's an undocumented feature.",
        "tip: the best code is no code.\n\tyou wrote code.\n\tbold move.",
        "tip: there are 10 kinds of people:\n\tthose who understand binary and those who don't.",
        "tip: programming is 10% writing code\n\tand 90% understanding why it doesn't work."
    ]
    tip = random.choice(tips)
    clear_screen()
    print()
    print()
    print(f"  {tip}")
    print()
    input("  press enter to continue...")


def initialize_game():
    draw_logo()
    typewrite("initializing db...", delay=0.01)
    ge.init_db()
    typewrite("loading class schemas...", delay=0.01)
    ge.init_classes()
    typewrite("generating loot tables...", delay=0.01)
    ge.loot_init()
    typewrite("building world index...", delay=0.01)
    ge.init_map()
    typewrite("ready.", delay=0.05)
    clear_screen()
    show_intro()
    print("\n" * 3)
    typewrite("building world index...", delay=0.01)
    ge.init_map()
    ge.init_node_flavour()
    show_useless_tip()

def show_intro():
    if not ge.is_first_launch():
        return
    clear_screen()
    time.sleep(0.5)
    typewrite("in the beginning, there was data.", delay=0.04)
    time.sleep(0.4)
    typewrite("vast. formless. unindexed.", delay=0.04)
    time.sleep(0.4)
    typewrite("then came the Schema.", delay=0.04)
    time.sleep(0.6)
    typewrite("it imposed order. named the tables. defined the keys.", delay=0.03)
    time.sleep(0.4)
    typewrite("for a time, the world was consistent.", delay=0.03)
    time.sleep(0.6)
    typewrite("then the corruption spread.", delay=0.04)
    time.sleep(0.4)
    typewrite("null pointers. deadlock wraiths. cascading failures.", delay=0.03)
    time.sleep(0.4)
    typewrite("the OVERFLOW bosses seized the deep layers.", delay=0.03)
    time.sleep(0.6)
    typewrite("you are a process. freshly spawned. assigned a class.", delay=0.03)
    time.sleep(0.4)
    typewrite("your task: traverse the index. clear the corruption.", delay=0.03)
    time.sleep(0.4)
    typewrite("restore the Schema.", delay=0.05)
    time.sleep(0.8)
    input("\n  press enter to begin...")
    ge.mark_intro_shown()


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
        return ge.init_player(username, class_name)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"  username '{username}' is already taken.")
        else:
            print(f"  error creating player: {e}")
        input("\npress enter...")
        return None


def load_game():
    clear_screen()
    ge.c.execute("SELECT id, username FROM players")
    usernames = ge.c.fetchall()

    print("players:")
    for username in usernames:
        print(f"({username['id']}) {username['username']}")

    user_id = input("choose number: ")
    ge.c.execute("SELECT id FROM players WHERE id = ?", (user_id,))
    row = ge.c.fetchone()
    if not row:
        print("save not found")
        return None
    return row["id"]


# ------------------------------------------------------------------ #
#  DEATH HANDLER                                                       #
# ------------------------------------------------------------------ #

def _handle_death(player_id):
    """Show defeat message, record death via db, notify if stat reset triggered."""
    dsr, did_reset = ge.record_death_and_check_reset(player_id)
    lives = ge.get_lives(player_id)
    life_icons = "♥ " * lives + "♡ " * (3 - lives)

    clear_screen()
    typewrite("  you have been defeated.", delay=0.03)
    print()
    print(f"  Lives: {life_icons.strip()}")

    if did_reset:
        print()
        typewrite("  3 deaths reached — the system flushes your process.", delay=0.03)
        typewrite("  stats, gear, and inventory have been wiped.", delay=0.03)
        typewrite("  lives restored to 3.", delay=0.03)
    else:
        remaining = 3 - dsr
        typewrite(f"  {remaining} death(s) until a full stat reset.", delay=0.02)

    input("\npress enter...")


# ------------------------------------------------------------------ #
#  GEAR SETS SCREEN                                                    #
# ------------------------------------------------------------------ #

def show_gear_sets_screen(player_id):
    """Let the player choose and equip a starter gear set they have unlocked."""
    all_sets   = ge.get_all_gear_sets()
    unlocked   = {s["id"] for s in ge.get_unlocked_gear_sets(player_id)}

    if not unlocked:
        clear_screen()
        typewrite("  no gear sets unlocked yet.", delay=0.02)
        typewrite("  clear your first run to unlock Set 1.", delay=0.02)
        input("\npress enter...")
        return

    while True:
        clear_screen()
        print("  [ STARTER GEAR SETS ]")
        print()

        # Header row
        header_cells = []
        for s in all_sets:
            if s["id"] in unlocked:
                header_cells.append(f"  Set {s['id']} — {s['set_name']}")
            else:
                lock_msg = f"(unlock at clear {s['id'] * 5})"
                header_cells.append(f"  Set {s['id']} — [LOCKED {lock_msg}]")

        col_w = 34
        print("".join(c.ljust(col_w) for c in header_cells))
        print("  " + "-" * (col_w * len(all_sets) - 2))

        # Weapon row
        w_cells = []
        for s in all_sets:
            if s["id"] in unlocked:
                w_cells.append(f"  W: {s['weapon_name'][:28]}")
            else:
                w_cells.append("  W: ???")
        print("".join(c.ljust(col_w) for c in w_cells))

        # Weapon stats row
        ws_cells = []
        for s in all_sets:
            if s["id"] in unlocked:
                ws_cells.append(
                    f"    hp+{s['w_bonus_hp']} hit+{s['w_bonus_hit']} "
                    f"crit+{s['w_bonus_crit']} x{s['w_hit_mult']}"
                )
            else:
                ws_cells.append("    ???")
        print("".join(c.ljust(col_w) for c in ws_cells))

        # Armor row
        a_cells = []
        for s in all_sets:
            if s["id"] in unlocked:
                a_cells.append(f"  A: {s['armor_name'][:28]}")
            else:
                a_cells.append("  A: ???")
        print("".join(c.ljust(col_w) for c in a_cells))

        # Armor stats row
        as_cells = []
        for s in all_sets:
            if s["id"] in unlocked:
                as_cells.append(
                    f"    hp+{s['a_bonus_hp']} hit+{s['a_bonus_hit']} "
                    f"crit+{s['a_bonus_crit']}"
                )
            else:
                as_cells.append("    ???")
        print("".join(c.ljust(col_w) for c in as_cells))

        print()
        print("  choose gear> ", end="")
        # Build options only for unlocked sets
        unlocked_ids = sorted(unlocked)
        for idx, sid in enumerate(unlocked_ids, 1):
            s = next(x for x in all_sets if x["id"] == sid)
            print(f"  ({idx}) {s['set_name']}", end="   ")
        print()
        print("  (0) back")
        print()

        raw = input("> ").strip()
        if raw == "0":
            return

        try:
            choice = int(raw)
        except ValueError:
            continue

        if 1 <= choice <= len(unlocked_ids):
            chosen_id  = unlocked_ids[choice - 1]
            chosen_set = next(s for s in all_sets if s["id"] == chosen_id)

            # Ensure weapon/armor rows exist in DB
            ge.ensure_starter_gear_in_db(chosen_set)

            # Give items to player if not already in inventory
            ge.c.execute(
                "SELECT COUNT(*) FROM inventory WHERE player_id = ? AND item = ?",
                (player_id, chosen_set["weapon_name"])
            )
            if ge.c.fetchone()[0] == 0:
                ge.add_item(player_id, chosen_set["weapon_name"], 1)

            ge.c.execute(
                "SELECT COUNT(*) FROM inventory WHERE player_id = ? AND item = ?",
                (player_id, chosen_set["armor_name"])
            )
            if ge.c.fetchone()[0] == 0:
                ge.add_item(player_id, chosen_set["armor_name"], 1)

            # Equip them
            ge.c.execute(
                "UPDATE players SET equipped_weapon = ?, equipped_armor = ? WHERE id = ?",
                (chosen_set["weapon_name"], chosen_set["armor_name"], player_id)
            )
            ge.rebuild_stats(player_id)
            ge.conn.commit()

            clear_screen()
            typewrite(f"  [ {chosen_set['set_name']} ] equipped.", delay=0.03)
            typewrite(f"  weapon : {chosen_set['weapon_name']}", delay=0.02)
            typewrite(f"  armor  : {chosen_set['armor_name']}", delay=0.02)
            input("\npress enter...")
            return


def _handle_run_clear(player_id):
    """Called on every run win.
    - Increments total_clears.
    - Every 5 clears: wipes inventory/gear/bytes and plays the purge sequence.
    - Unlocks a gear set at clears 5, 10, 15.
    Returns total_clears after increment.
    """
    total_clears = ge.increment_clears(player_id)

    # Every 5 clears — wipe the player and run the purge cinematic
    if total_clears % 5 == 0:
        ge.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
        username = ge.c.fetchone()["username"]
        ge.clear_user(player_id)

        enable_cbreak()
        clear_screen()
        typewrite(f"great work {username}...")
        if skip(): disable_cbreak(); return total_clears
        time.sleep(0.5)
        typewrite("...")
        if skip(): disable_cbreak(); return total_clears
        time.sleep(0.5)
        typewrite("..hm..")
        if skip(): disable_cbreak(); return total_clears
        time.sleep(0.5)
        typewrite("there's no need for you now..")
        if skip(): disable_cbreak(); return total_clears
        time.sleep(0.5)
        print()
        typewrite(f"DELETE data FROM users WHERE name = {username}")
        if skip(): disable_cbreak(); return total_clears
        time.sleep(0.5)
        typewrite("1..2..3..done!")
        time.sleep(0,5)
        disable_cbreak()
        input("\n  press enter to start again!")

    # Unlock gear sets at clears 5, 10, 15
    newly_unlocked = []
    if total_clears == 5:
        ge.unlock_gear_set(player_id, 1)
        newly_unlocked.append(1)
    elif total_clears == 10:
        ge.unlock_gear_set(player_id, 2)
        newly_unlocked.append(2)
    elif total_clears == 15:
        ge.unlock_gear_set(player_id, 3)
        newly_unlocked.append(3)

    if newly_unlocked:
        clear_screen()
        typewrite("  [ GEAR SET UNLOCKED ]", delay=0.03)
        print()
        all_sets = ge.get_all_gear_sets()
        for sid in newly_unlocked:
            s = next(x for x in all_sets if x["id"] == sid)
            typewrite(f"  Set {sid}: {s['set_name']}", delay=0.02)
            typewrite(f"    Weapon : {s['weapon_name']}", delay=0.01)
            typewrite(f"      hp+{s['w_bonus_hp']} hit+{s['w_bonus_hit']} crit+{s['w_bonus_crit']} x{s['w_hit_mult']}", delay=0.01)
            typewrite(f"    Armor  : {s['armor_name']}", delay=0.01)
            typewrite(f"      hp+{s['a_bonus_hp']} hit+{s['a_bonus_hit']} crit+{s['a_bonus_crit']}", delay=0.01)
        print()
        typewrite("  access your gear sets from the camp menu.", delay=0.02)
        input("\npress enter to return to camp...")

    return total_clears


def get_equipped(player_id):
    ge.c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    row = ge.c.fetchone()
    equipped_weapon = row["equipped_weapon"] if row else None

    ge.c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
    row = ge.c.fetchone()
    equipped_armor = row["equipped_armor"] if row else None

    return equipped_weapon, equipped_armor


def print_item_stats(data, label):
    print("====================")
    print(f"[{label}]")
    print("| Class:          ", data["class_type"])
    if "hit_mult" in data.keys():
        print("| Hit Multiplier: ", data["hit_mult"])
    print("| Bonus HP:       ", data["bonus_hp"])
    print("| Bonus Hit:      ", data["bonus_hit"])
    print("| Bonus Crit:     ", data["bonus_crit"])
    print("====================")


def xp_bar(current_xp: int, level: int, width: int = 20) -> str:
    """Return a visual XP progress bar string."""
    needed = ge.experience_needed_for_next_level(level)
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
    ge.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
    username = ge.c.fetchone()["username"]
    ge.c.execute("""
        SELECT base_hp, bonus_hp, max_hp, current_hp, bytes,
               base_hit, bonus_hit, base_crit, bonus_crit
        FROM player_stats WHERE player_id = ?
    """, (player_id,))
    stats = ge.c.fetchone()
    ge.c.execute("SELECT level, experience, deaths, kills FROM players WHERE id = ?", (player_id,))
    player_info = ge.c.fetchone()

    header = f"=== [ {username} ] ==="
    print(header)
    print(f"Level: {player_info['level']}  |  {xp_bar(player_info['experience'], player_info['level'])}")
    print(f"HP:     {hp_bar(stats['current_hp'], stats['max_hp'])}  (base {stats['base_hp']} + bonus {stats['bonus_hp']})")
    print(f"Hit:    {stats['base_hit'] + stats['bonus_hit']}  (base {stats['base_hit']} + bonus {stats['bonus_hit']})")
    print(f"crit: {stats['base_crit'] + stats['bonus_crit']}  (base {stats['base_crit']} + bonus {stats['bonus_crit']})")
    lives = ge.get_lives(player_id)
    life_icons = "♥ " * lives + "♡ " * (3 - lives)
    clears = ge.get_total_clears(player_id)
    print(f"Kills: {player_info['kills']}   Deaths: {player_info['deaths']}")
    print(f"Lives: {life_icons.strip()}  (resets every 3 deaths)")
    print(f"Clears: {clears}")
    print(f"bytes:  {stats['bytes']}")
    print("=" * len(header))


# ------------------------------------------------------------------ #
#  COMBAT                                                             #
# ------------------------------------------------------------------ #

def get_combat_potions(player_id):
    potion_names = {p[0] for p in ge.get_potion_pool()}
    ge.c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
    return [i for i in ge.c.fetchall() if i["item"] in potion_names]


def draw_combat_screen(player_id, enemy_id, events, active_defense, log, combo = 0):
    ge.c.execute("SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (player_id,))
    pstats = ge.c.fetchone()
    ge.c.execute("SELECT type, base_hp, max_hp FROM enemies WHERE id = ?", (enemy_id,))
    estats = ge.c.fetchone()

    clear_screen()
    ascii_art.print_enemy_art(estats["type"])
    print()
    print(f"  [ {estats['type']} ]")
    print(f"  HP: {hp_bar(estats['base_hp'], estats['max_hp'])}")
    statuses = ge.get_statuses(player_id)
    if statuses:
        status_str = "  ".join(f"[{s['effect']}:{s['duration']}]" for s in statuses)
        print(f"  {status_str}")
    if combo > 0:
        print(f"  [ COMBO: {combo}/3 ]")
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
    ge.c.execute("SELECT base_hit, bonus_hit, base_crit, bonus_crit FROM player_stats WHERE player_id = ?", (player_id,))
    pstats = ge.c.fetchone()
    dmg = max(1, pstats["base_hit"] + pstats["bonus_hit"] - random.randint(0, 5))
    total_crit = pstats["base_crit"] + pstats["bonus_crit"]
    crit_chance = min(0.60, total_crit * 0.005)
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg *= 2
    ge.c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (dmg, enemy_id))
    ge.conn.commit()
    ge.c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    weapon_name = ge.c.fetchone()["equipped_weapon"]
    element_bonus = False
    if weapon_name:
        ge.c.execute("SELECT element FROM weapons WHERE name = ?", (weapon_name,))
        w_row = ge.c.fetchone()
        ge.c.execute("SELECT type FROM enemies WHERE id = ?", (enemy_id,))
        enemy_type = ge.c.fetchone()["type"]
        # Strip OVERFLOW boss prefix
        base_type = enemy_type.replace("OVERFLOW — ", "").strip()
        enemy_element = ge.ENEMY_ELEMENT.get(base_type)
        weapon_element = w_row["element"] if w_row else None
        if weapon_element and enemy_element and ge.ELEMENT_WEAKNESS.get(weapon_element) == enemy_element:
            dmg = int(dmg * 1.5)
            element_bonus = True
    return dmg, is_crit, element_bonus


def enemy_turn(player_id, enemy_id, events, active_defense):
    log = []
    ge.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
    ehit = ge.c.fetchone()[0]

    dmg = max(0, ehit - random.randint(0, 5))

    if active_defense > 0:
        absorbed = min(active_defense, dmg)
        dmg -= absorbed
        active_defense -= absorbed
        if absorbed:
            log.append(f"barrier absorbs {absorbed} damage.")

    if dmg > 0:
        ge.c.execute(
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
        ge.c.execute(
            "UPDATE player_stats SET current_hp = current_hp - ? WHERE player_id = ?",
            (extra, player_id)
        )
        log.append(f"monster rush second strike: -{extra} hp.")

    # Random status proc — 15% chance
    if random.random() < 0.15:
        effect = random.choice(["DEADLOCK", "CORRUPTION", "SEGFAULT"])
        duration = random.randint(2, 3)
        ge.apply_status(player_id, effect, duration)
        log.append(f"  you are afflicted with {effect} for {duration} turns!")

    ge.conn.commit()
    return active_defense, log

def run_rest(player_id, node_name):
    in_rest = True
    while in_rest:
        clear_screen()
        ge.c.execute("""
            SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?
        """, (player_id,))
        row = ge.c.fetchone()
        current_hp, max_hp = row["current_hp"], row["max_hp"]

        print(f"[ {node_name} ] — REST")
        print(f"  HP: {hp_bar(current_hp, max_hp)}")
        print()
        print("  (1) rest — recover 50%-100% of missing HP")
        print("  (2) change gear")
        print("  (3) use a potion")
        print("  (0) leave")
        print()

        try:
            choice = int(input("> "))
        except ValueError:
            continue

        if choice == 0:
            in_rest = False

        elif choice == 1:
            missing = max_hp - current_hp
            heal_pct = random.uniform(0.5, 1.0)
            heal_amt = max(1, int(missing * heal_pct))
            ge.c.execute("""
                UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp)
                WHERE player_id = ?
            """, (heal_amt, player_id))
            ge.conn.commit()
            in_rest = False
            typewrite(f"  you rest. +{heal_amt} hp restored.", delay=0.02)
            input("\npress enter...")

        elif choice == 2:
            show_inventory_screen(player_id)

        elif choice == 3:
            ge.c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
            inv_items = ge.c.fetchall()
            potion_names = {p[0] for p in ge.get_potion_pool()}
            potions = [i for i in inv_items if i["item"] in potion_names]

            if not potions:
                typewrite("  no potions in inventory.", delay=0.02)
                input("\npress enter...")
                continue

            clear_screen()
            print("  [ POTIONS ]")
            print()
            for i, pot in enumerate(potions, 1):
                print(f"  ({i}) {pot['item']}  x{pot['amount']}")
            print("  (0) back")
            print()

            try:
                pchoice = int(input("> "))
            except ValueError:
                continue

            if 1 <= pchoice <= len(potions):
                pot_row = potions[pchoice - 1]
                result = ge.apply_potion(player_id, pot_row["item"])
                if pot_row["amount"] <= 1:
                    ge.c.execute("DELETE FROM inventory WHERE rowid = ?", (pot_row["rowid"],))
                else:
                    ge.c.execute(
                        "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                        (pot_row["rowid"],)
                    )
                ge.conn.commit()
                if result.get("heal"):
                    typewrite(f"  restored {result['heal']} hp.", delay=0.02)
                if result.get("bonus_crit"):
                    typewrite(f"  crit +{result['bonus_crit']}.", delay=0.02)
                if result.get("defense"):
                    typewrite(f"  barrier +{result['defense']} (only active in combat).", delay=0.02)
                input("\npress enter...")

def run_combat(player_id, enemy_id, events, active_defense=0, run_id=None):
    """Turn-based combat. Returns ('win'|'lose'|'flee', active_defense)."""
    log   = []
    combo = 0

    while True:
        # ---- Tick statuses at start of each turn ---- #
        status_log = ge.tick_statuses(player_id)
        if status_log:
            log += status_log

        estats, pstats, potions = draw_combat_screen(
            player_id, enemy_id, events, active_defense, log, combo
        )
        flee_option = len(potions) + 2

        # ---- DEADLOCK — skip player turn ---- #
        statuses = ge.get_statuses(player_id)
        if any(s["effect"] == "DEADLOCK" for s in statuses):
            log = ["DEADLOCK — your turn is skipped!"]
            active_defense, enemy_log = enemy_turn(player_id, enemy_id, events, active_defense)
            log += enemy_log
            ge.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            if ge.c.fetchone()[0] <= 0:
                ge.c.execute("UPDATE players SET deaths = deaths + 1 WHERE id = ?", (player_id,))
                ge.c.execute("UPDATE player_stats SET current_hp = max_hp WHERE player_id = ?", (player_id,))
                ge.c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
                ge.conn.commit()
                _handle_death(player_id)
                return "lose", 0
                return "lose", 0
            combo = 0
            continue

        try:
            action = int(input("> ").strip())
        except ValueError:
            continue

        # ---- ATTACK ---- #
        if action == 1:
            dmg, is_crit, element_bonus = player_attack(player_id, enemy_id)
            msg = f"{'CRITICAL! ' if is_crit else ''}you hit for {dmg} damage.{' [EFFECTIVE]' if element_bonus else ''}"
            log = [msg]

            ge.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (enemy_id,))
            if ge.c.fetchone()[0] <= 0:
                ge.c.execute("SELECT experience_drop FROM enemies WHERE id = ?", (enemy_id,))
                xp = ge.c.fetchone()[0]
                bytes_drop = random.randint(8, 30)
                ge.c.execute(
                    "UPDATE players SET experience = experience + ?, kills = kills + 1 WHERE id = ?",
                    (xp, player_id)
                )
                ge.c.execute(
                    "UPDATE player_stats SET bytes = bytes + ? WHERE player_id = ?",
                    (bytes_drop, player_id)
                )
                ge.conn.commit()
                if run_id:
                    ge.record_run_kill(run_id)
                    ge.record_run_bytes(run_id, bytes_drop)

                ge.c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
                ge.conn.commit()
                drop = ge.enemy_drop_potion(player_id)

                clear_screen()
                ascii_art.print_enemy_art(estats["type"])
                print()
                typewrite(f"  enemy defeated!", delay=0.02)
                typewrite(f"  +{xp} xp   +{bytes_drop} bytes", delay=0.02)
                ge.c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
                row = ge.c.fetchone()
                if row[1] >= ge.experience_needed_for_next_level(row[0]):
                    ge.level_up(player_id)
                if drop:
                    typewrite(f"  loot: {drop}", delay=0.02)
                input("\npress enter...")
                return "win", active_defense

            # Snapshot HP before enemy turn
            ge.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            hp_before = ge.c.fetchone()[0]

            active_defense, enemy_log = enemy_turn(player_id, enemy_id, events, active_defense)
            log += enemy_log

            ge.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            hp_after = ge.c.fetchone()[0]

            if hp_after <= 0:
                ge.c.execute("UPDATE players SET deaths = deaths + 1 WHERE id = ?", (player_id,))
                ge.c.execute("UPDATE player_stats SET current_hp = max_hp WHERE player_id = ?", (player_id,))
                ge.c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
                ge.conn.commit()
                _handle_death(player_id)
                return "lose", 0
                return "lose", 0

            # ---- COMBO tracking ---- #
            if hp_after < hp_before:
                combo = 0
            else:
                combo += 1
                if combo >= 3:
                    ge.c.execute("SELECT base_hit, bonus_hit FROM player_stats WHERE player_id = ?", (player_id,))
                    ps = ge.c.fetchone()
                    chain_dmg = max(1, ps["base_hit"] + ps["bonus_hit"])
                    ge.c.execute("UPDATE enemies SET base_hp = base_hp - ? WHERE id = ?", (chain_dmg, enemy_id))
                    ge.conn.commit()
                    log.append(f"QUERY CHAIN! bonus strike for {chain_dmg} damage.")
                    combo = 0

        # ---- USE POTION ---- #
        elif 2 <= action <= len(potions) + 1:
            pot_row = potions[action - 2]
            result  = ge.apply_potion(player_id, pot_row["item"])

            if pot_row["amount"] <= 1:
                ge.c.execute("DELETE FROM inventory WHERE rowid = ?", (pot_row["rowid"],))
            else:
                ge.c.execute(
                    "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                    (pot_row["rowid"],)
                )
            ge.conn.commit()

            log = []
            if result.get("heal"):
                log.append(f"restored {result['heal']} hp.")
            if result.get("bonus_hit"):
                log.append(f"attack surges +{result['bonus_hit']} hit.")
            if result.get("bonus_crit"):
                log.append(f"crit +{result['bonus_crit']}.")
            if result.get("defense"):
                active_defense += result["defense"]
                log.append(f"barrier active: {active_defense} reduction.")

        # ---- FLEE ---- #
        elif action == flee_option:
            ge.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (enemy_id,))
            ehit = ge.c.fetchone()[0]
            flee_dmg = max(0, ehit // 2 - random.randint(0, 3))
            ge.c.execute(
                "UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
                (flee_dmg, player_id)
            )
            ge.c.execute("DELETE FROM status_effects WHERE player_id = ?", (player_id,))
            ge.conn.commit()
            clear_screen()
            typewrite(f"  you flee — taking {flee_dmg} damage on the way out.", delay=0.02)
            input("\npress enter...")
            return "flee", active_defense


def show_npc(player_id, events):
    ge.c.execute("SELECT kills, deaths FROM players WHERE id = ?", (player_id,))
    row = ge.c.fetchone()
    kills  = row["kills"]
    deaths = row["deaths"]

    clear_screen()
    print("  [ ARCHIVIST ]")
    print()

    # Event reactions take priority
    if events.get("blood_moon"):
        typewrite("  the moon runs red. i have not seen this in many cycles.", delay=0.02)
    elif events.get("flood_omnya"):
        typewrite("  the waters rise. some paths are lost to us now.", delay=0.02)
    elif events.get("monster_rush"):
        typewrite("  they come in waves. do not let them surround you.", delay=0.02)
    elif events.get("solar_eclipse"):
        typewrite("  the light dims. The Indexer's power swells in the dark.", delay=0.02)
    elif events.get("fateful_day"):
        typewrite("  the markets overflow today. rare things surface rarely.", delay=0.02)
    # Kill/death reactions
    elif kills == 0:
        typewrite("  you have not yet drawn blood. the index waits.", delay=0.02)
    elif deaths > kills:
        typewrite(f"  {deaths} deaths. {kills} kills. the corruption is winning.", delay=0.02)
    elif kills >= 50:
        typewrite(f"  {kills} processes terminated. the schema remembers.", delay=0.02)
    elif kills >= 20:
        typewrite(f"  you have cut a path through {kills} enemies. keep going.", delay=0.02)
    elif deaths == 0:
        typewrite(f"  {kills} kills. no deaths. impressive uptime.", delay=0.02)
    else:
        typewrite(f"  {kills} kills. {deaths} deaths. the balance shifts.", delay=0.02)

    print()
    input("  press enter...")


def enable_cbreak():
    tty.setcbreak(fd)

def disable_cbreak():
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
disable_cbreak()

def skip():
    return select.select([sys.stdin], [], [], 0)[0]

def skiping():
    disable_cbreak()
    new_run(player_id)

def show_ending(player_id):
    enable_cbreak()
    ge.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
    username = ge.c.fetchone()["username"]

    clear_screen()
    print("you can skip with [esc]", "\n" *5)
    time.sleep(0.5)
    if skip(): 
        skiping()
        return
    typewrite("  all OVERFLOW bosses have been terminated.", delay=0.03)
    time.sleep(0.6)
    if skip(): 
        skiping()
        return
    typewrite("  the deep layers fall silent.", delay=0.03)
    time.sleep(0.8)
    if skip(): 
        skiping()
        return
    typewrite("  initiating schema migration...", delay=0.04)
    time.sleep(0.5)
    if skip(): 
        skiping()
        return
    typewrite("  > DROP TABLE corruption;", delay=0.05)
    time.sleep(0.4)
    if skip(): 
        skiping()
        return
    typewrite("  > ALTER TABLE world ADD COLUMN order TEXT DEFAULT 'restored';", delay=0.04)
    time.sleep(0.4)
    if skip():
        skiping()
        return
    typewrite("  > COMMIT;", delay=0.06)
    time.sleep(0.8)
    if skip(): 
        skiping()
        return
    typewrite("  migration complete.", delay=0.04)
    time.sleep(0.6)
    if skip(): 
        skiping()
        return
    typewrite(f"  process {username} has fulfilled its purpose.", delay=0.03)
    time.sleep(0.4)
    if skip():
        skiping()
        return
    typewrite("  the Schema holds.", delay=0.05)
    time.sleep(1.0)
    disable_cbreak()


    input("\n  press enter...")

def new_run(player_id):
    clear_screen()
    ge.c.execute("SELECT username FROM players WHERE id = ?", (player_id,))
    username = ge.c.fetchone()["username"]
    ge.clear_user(player_id)
    typewrite(f"great work {username}...", delay=0.4)
    if skip():
        disable_cbreak()
        return
    typewrite("...", delay=0.5)
    if skip():
        disable_cbreak()
        return
    typewrite("..hm..", delay=0.5)
    if skip():
        disable_cbreak()
        return
    typewrite("there's no need for you now..")
    if skip():
        disable_cbreak()
        return
    print("\n" * 2)
    if skip():
        disable_cbreak()
        return
    typewrite(f"DELETE data FROM users WHERE name = {username}")
    if skip():
        disable_cbreak()
        return
    typewrite("1..2..3..done!", delay=0.5)
    input("\n  press enter to start again!")

def print_run_stats(player_id):
    data = ge.fetch_runs_stats(player_id)
    
    if not data:
        print("no runs yet")
        return

    print("==================================================")
    print("--------------------------------------------------")

    for row in data:
        print(f"run #{row['id']}")
        print(f"kills: {row['kills']} | bytes: {row['bytes_earned']} | nodes: {row['nodes_cleared']}")
        print(f"outcome: {row['outcome']} | seed: {row['seed']}")
        print("--------------------------------------------------")

    print("==================================================")



def run_tutorial():
    clear_screen()
    typewrite("  [ TUTORIAL — TRAINING SEQUENCE ]", delay=0.03)
    typewrite("  this is a simulated run. no progress will be saved.", delay=0.02)
    print()
    input("  press enter to begin...")

    # ------------------------------------------------------------------ #
    #  PAGE 1 — Classes and stats
    # ------------------------------------------------------------------ #
    clear_screen()
    print("  [ CLASSES ]")
    print()
    typewrite("  there are three classes:", delay=0.02)
    print()
    typewrite("  THE EXECUTOR  — high HP, strong hits. built to endure.", delay=0.02)
    typewrite("  THE INDEXER   — low HP, high crit. lands devastating strikes.", delay=0.02)
    typewrite("  THE TRIGGER   — balanced. adapts to any situation.", delay=0.02)
    print()
    typewrite("  your stats:", delay=0.02)
    print()
    print("  HP     — how much damage you can take before falling.")
    print("  HIT    — base damage output per attack.")
    print("  CRIT   — chance to deal 2x damage. also reduces trap damage.")
    print("  bytes   — used to buy gear and potions at shops.")
    print()
    input("  press enter to continue...")

    # ------------------------------------------------------------------ #
    #  PAGE 2 — Encounter types
    # ------------------------------------------------------------------ #
    clear_screen()
    print("  [ ENCOUNTER TYPES ]")
    print()
    print("  each node in a run is one of these:")
    print()
    print("  TRANSACTION      — a shop. buy gear, potions, or sell items.")
    print("  QUERY            — standard combat. defeat the enemy to proceed.")
    print("  STORED_PROCEDURE — a dungeon. multiple rooms, guaranteed loot at the end.")
    print("  DEADLOCK         — a dungeon where enemies hit twice as hard.")
    print("  CONSTRAINT       — triggers a world event, then combat.")
    print("  OVERFLOW         — a boss. much stronger. drops unique loot.")
    print("  REST             — a checkpoint. heal, change gear, use potions.")
    print()
    typewrite("  clearing all OVERFLOW bosses triggers the ending.", delay=0.02)
    print()
    input("  press enter to continue...")

    # ------------------------------------------------------------------ #
    #  PAGE 3 — Combat mechanics (simulated fight)
    # ------------------------------------------------------------------ #
    clear_screen()
    print("  [ COMBAT ]")
    print()
    typewrite("  let's walk through a simulated fight.", delay=0.02)
    print()
    input("  press enter to continue...")

    # Simulate a combat screen
    clear_screen()
    print("  [ Cached Queries ]  — QUERY")
    print()
    print("  [ ENEMY: Null Pointer ]")
    print("  HP: [████████████████████] 80/80")
    print()
    print("  [ YOU ]   [████████████████████] 120/120")
    print()
    print("  (1) attack")
    print("  (2) use Minor Restore  x1")
    print("  (3) flee")
    print()
    typewrite("  (1) attack — deals HIT damage. chance to CRIT (2x) based on your crit stat.", delay=0.02)
    print()
    input("  press enter to continue...")

    clear_screen()
    print("  [ COMBAT — COMBO SYSTEM ]")
    print()
    typewrite("  if you take no damage for 3 turns in a row:", delay=0.02)
    typewrite("  a QUERY CHAIN fires — a free bonus strike.", delay=0.02)
    print()
    print("  [ COMBO: 2/3 ]  ← this counter builds each clean turn")
    print()
    typewrite("  taking any damage resets the combo to 0.", delay=0.02)
    print()
    input("  press enter to continue...")

    clear_screen()
    print("  [ COMBAT — ELEMENTS ]")
    print()
    typewrite("  weapons and enemies each have an element:", delay=0.02)
    print()
    print("  QUERY  →  beats  LOCK")
    print("  LOCK   →  beats  OVERFLOW")
    print("  OVERFLOW → beats  NULL")
    print("  NULL   →  beats  QUERY")
    print()
    typewrite("  hitting an enemy with its weakness deals 1.5x damage.", delay=0.02)
    typewrite("  this shows as [EFFECTIVE] in the combat log.", delay=0.02)
    print()
    input("  press enter to continue...")

    clear_screen()
    print("  [ COMBAT — STATUS EFFECTS ]")
    print()
    typewrite("  enemies have a 15% chance to inflict a status on hit:", delay=0.02)
    print()
    print("  DEADLOCK    — your next turn is skipped entirely.")
    print("  CORRUPTION  — burns 5% of your max HP each turn.")
    print("  SEGFAULT    — drains a random amount of HIT or CRIT.")
    print()
    typewrite("  statuses expire after 2-3 turns.", delay=0.02)
    typewrite("  they clear on combat end regardless.", delay=0.02)
    print()
    input("  press enter to continue...")

    # ------------------------------------------------------------------ #
    #  PAGE 4 — Items and gear
    # ------------------------------------------------------------------ #
    clear_screen()
    print("  [ ITEMS AND GEAR ]")
    print()
    typewrite("  weapons and armors each have:", delay=0.02)
    print()
    print("  CLASS TYPE     — matching your class gives bonus stats.")
    print("  HIT MULTIPLIER — multiplies your base HIT stat when equipped.")
    print("  BONUS HP       — adds directly to your max HP.")
    print("  BONUS HIT      — flat addition to your hit stat.")
    print("  BONUS CRIT     — flat addition to your crit stat.")
    print("  ELEMENT        — determines effectiveness vs enemy types.")
    print()
    typewrite("  gear scales with your level — higher level runs drop stronger items.", delay=0.02)
    print()
    typewrite("  potions restore a % of your max HP or boost stats temporarily.", delay=0.02)
    print()
    input("  press enter to continue...")

    # ------------------------------------------------------------------ #
    #  PAGE 5 — Events
    # ------------------------------------------------------------------ #
    clear_screen()
    print("  [ WORLD EVENTS ]")
    print()
    typewrite("  CONSTRAINT nodes trigger world events that affect the entire run:", delay=0.02)
    print()
    print("  BLOOD MOON    — all enemies deal double damage.")
    print("  SOLAR ECLIPSE — The Indexer's crit stat doubles.")
    print("  FLOOD OF OMNYA — CONSTRAINT paths become impassable.")
    print("  MONSTER RUSH  — enemies strike twice each turn.")
    print("  FATEFUL DAY   — shops stock rare, high-quality gear.")
    print()
    typewrite("  events expire after 10 combat encounters.", delay=0.02)
    typewrite("  multiple events can be active at once.", delay=0.02)
    print()
    input("  press enter to continue...")

    # ------------------------------------------------------------------ #
    #  DONE
    # ------------------------------------------------------------------ #
    clear_screen()
    typewrite("  training sequence complete.", delay=0.03)
    print()
    typewrite("  the index awaits.", delay=0.03)
    print()
    input("  press enter to return to menu...")

# ------------------------------------------------------------------ #
#  DUNGEON  (STORED_PROCEDURE / DEADLOCK)                             #
# ------------------------------------------------------------------ #

DUNGEON_ROOM_COUNT  = 3   # non-boss rooms before the final chamber
TRAP_DAMAGE_PERCENT = random.random()


def run_dungeon(player_id, node_name, enc_type, events, run_id=None):
    """Multi-room dungeon crawl for STORED_PROCEDURE (2) and DEADLOCK (3) nodes.

    Layout:
      Rooms 1..DUNGEON_ROOM_COUNT — each has a random encounter:
        * combat     (most common)
        * trap       — roll crit to reduce damage; fail = full hit
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
            ge.c.execute("SELECT base_crit + bonus_crit AS crit FROM player_stats WHERE player_id = ?",
                         (player_id,))
            crit = ge.c.fetchone()["crit"]
            ge.c.execute("SELECT max_hp FROM player_stats WHERE player_id = ?", (player_id,))
            max_hp = ge.c.fetchone()["max_hp"]

            trap_dmg_full = max(5, int(max_hp * TRAP_DAMAGE_PERCENT))
            # crit check: each point of crit is a 0.5% chance to halve damage (cap 60%)
            dodge_chance = min(0.60, crit * 0.005)
            dodged = random.random() < dodge_chance
            trap_dmg = trap_dmg_full // 2 if dodged else trap_dmg_full

            typewrite("  CONSTRAINT VIOLATION — a trap fires.", delay=0.02)
            if dodged:
                typewrite(f"  your crit lets you sidestep the worst of it: -{trap_dmg} hp.", delay=0.02)
            else:
                typewrite(f"  you walk straight into it: -{trap_dmg} hp.", delay=0.02)

            ge.c.execute(
                "UPDATE player_stats SET current_hp = MAX(1, current_hp - ?) WHERE player_id = ?",
                (trap_dmg, player_id)
            )
            ge.conn.commit()

            # Check if trap would have killed — keep player at 1 hp but warn
            ge.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            if ge.c.fetchone()["current_hp"] <= 1:
                typewrite("  barely alive.", delay=0.02)

            input("\npress enter to continue...")

        # ---- REST ROOM ---- #
        elif room_type == "rest":
            ge.c.execute("SELECT max_hp, current_hp FROM player_stats WHERE player_id = ?", (player_id,))
            row = ge.c.fetchone()
            heal_amt = max(5, int(row["max_hp"] * 0.12))
            ge.c.execute(
                "UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?",
                (heal_amt, player_id)
            )
            ge.conn.commit()
            typewrite("  a brief respite — you catch your breath.", delay=0.02)
            typewrite(f"  +{heal_amt} hp restored.", delay=0.02)
            input("\npress enter to continue...")

        # ---- COMBAT ROOM ---- #
        else:
            enemy_id = ge.generate_enemy(player_id, is_boss=False)

            # DEADLOCK: mirror enemy — double the hit stat to simulate two attackers
            if is_deadlock and not is_final:
                ge.c.execute("UPDATE enemies SET base_hit = base_hit * 2 WHERE id = ?", (enemy_id,))
                ge.conn.commit()
                typewrite("  two forms emerge — they move as one.", delay=0.02)
                print()

            ge.apply_event_combat_modifiers(enemy_id, events)
            result, active_defense = run_combat(player_id, enemy_id, events, active_defense, run_id=run_id)

            if result == "lose":
                return False

            if result == "flee":
                typewrite("  you retreat from the dungeon.", delay=0.02)
                input("\npress enter...")
                return False

            # Tick the event counter after each combat encounter
            was_reset = ge.tick_event_counter()
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

    ge.c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
    player_level = ge.c.fetchone()["level"]
    _, loot_name, _ = ge.generate_gear(player_level)
    ge.add_item(player_id, loot_name, 1)
    ge.conn.commit()
    typewrite(f"  guaranteed loot: {loot_name}", delay=0.02)

    input("\npress enter...")
    return True


# ------------------------------------------------------------------ #
#  SHOP                                                              #
# ------------------------------------------------------------------ #

SHOP_STOCK_SIZE = random.randint(1,4)


def run_shop(player_id, node_name, events, path_id=None, run_seed=None):
    fateful_day = events["fateful_day"]

    # Try to load a previously saved stock for this shop
    saved = ge.load_shop_stock(path_id) if path_id else None

    if saved:
        # Reconstruct gear_stock and potion_stock from saved rows
        potion_names = {p[0] for p in ge.get_potion_pool()}
        potion_pool_map = {p[0]: p for p in ge.get_potion_pool()}
        gear_stock   = []
        potion_stock = []
        weapon_pool  = []
        armor_pool   = []
        for item_type, item_name in saved:
            if item_type == "weapon":
                ge.c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
                row = ge.c.fetchone()
                if row:
                    gear_stock.append(row)
                    weapon_pool.append(row)
            elif item_type == "armor":
                ge.c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
                row = ge.c.fetchone()
                if row:
                    gear_stock.append(row)
                    armor_pool.append(row)
            elif item_type == "potion" and item_name in potion_pool_map:
                potion_stock.append(potion_pool_map[item_name])
    else:
        # Roll fresh stock, using a shop-specific RNG derived from run seed + path_id
        shop_rng = random.Random((run_seed or 0) ^ (path_id or 0))

        ge.c.execute("SELECT level FROM players WHERE id = ?", (player_id,))
        player_level = ge.c.fetchone()["level"]

        weapon_pool = []
        armor_pool  = []
        for _ in range(SHOP_STOCK_SIZE * 2):
            _, name, _ = ge.generate_gear(player_level, "weapon")
            ge.c.execute("SELECT * FROM weapons WHERE name = ?", (name,))
            row = ge.c.fetchone()
            if row is not None:
                weapon_pool.append(row)
        for _ in range(SHOP_STOCK_SIZE * 2):
            _, name, _ = ge.generate_gear(player_level, "armor")
            ge.c.execute("SELECT * FROM armors WHERE name = ?", (name,))
            row = ge.c.fetchone()
            if row is not None:
                armor_pool.append(row)

        # Fallback: pull existing gear from DB if pools are empty (weapon cap hit)
        if not weapon_pool:
            ge.c.execute("SELECT * FROM weapons ORDER BY RANDOM() LIMIT ?", (SHOP_STOCK_SIZE * 2,))
            weapon_pool = list(ge.c.fetchall())
        if not armor_pool:
            ge.c.execute("SELECT * FROM armors ORDER BY RANDOM() LIMIT ?", (SHOP_STOCK_SIZE * 2,))
            armor_pool = list(ge.c.fetchall())

        combined = weapon_pool + armor_pool
        if fateful_day:
            def item_score(i):
                return i["bonus_hp"] + i["bonus_hit"] + i["bonus_crit"] + 1
            scores     = [item_score(i) for i in combined]
            gear_stock = shop_rng.choices(combined, weights=scores, k=min(SHOP_STOCK_SIZE, len(combined)))
        else:
            gear_stock = shop_rng.sample(combined, min(SHOP_STOCK_SIZE, len(combined)))

        all_potions  = ge.get_potion_pool()
        if fateful_day:
            pw = [p[7] for p in all_potions]
        else:
            pw = [1 / (p[7] + 1) * 100 for p in all_potions]
        potion_stock = shop_rng.choices(all_potions, weights=pw, k=SHOP_STOCK_SIZE)

        # Persist the rolled stock
        if path_id:
            stock_to_save = []
            for item in gear_stock:
                kind = "weapon" if item in weapon_pool else "armor"
                stock_to_save.append((kind, item["name"]))
            for pot in potion_stock:
                stock_to_save.append(("potion", pot[0]))
            ge.save_shop_stock(path_id, stock_to_save)

    def gear_price(item):
        # hit_mult only applies to weapons
        hm = item["hit_mult"] if "hit_mult" in item and item in weapon_pool else 0
        return max(10, item["bonus_hp"] + item["bonus_hit"] + item["bonus_crit"] * 2 + hm * 3)

    def gear_sell_price(item):
        """Sell value is roughly 40% of buy price."""
        is_weapon = "hit_mult" in item.keys()
        hm = item["hit_mult"] if is_weapon else 0
        buy = max(10, item["bonus_hp"] + item["bonus_hit"] + item["bonus_crit"] * 2 + hm * 3)
        return max(1, int(buy * 0.4))

    def show_gear_stats(item, price, bytes):
        kind = "WEAPON" if item in weapon_pool else "ARMOR"
        affordable = "buy" if bytes >= price else "can't afford"
        print(f"  [{kind}] {item['name']}")
        print(f"  Class:          {item['class_type']}")
        if kind == "WEAPON":
            print(f"  Hit Multiplier: {item['hit_mult']}")
        print(f"  Bonus HP:       {item['bonus_hp']}")
        print(f"  Bonus Hit:      {item['bonus_hit']}")
        print(f"  Bonus crit:     {item['bonus_crit']}")
        print(f"  Element:        {item['element']}")
        print(f"  Price:          {price}b  [{affordable}]")

    def show_potion_stats(pot, bytes):
        pname, ptype, pheal, pbhit, pbcrit, pbdef, pdur, pprice = pot
        affordable = "buy" if bytes >= pprice else "can't afford"
        print(f"  [POTION] {pname}  ({ptype})")
        if pheal: print(f"  Heal:    +{pheal} hp")
        if pbhit: print(f"  Attack:  +{pbhit} hit  (lasts {pdur} rounds)")
        if pbcrit: print(f"  crit:  +{pbcrit} crit  (lasts {pdur} rounds)")
        if pbdef: print(f"  Barrier: +{pbdef} dmg reduction  (lasts {pdur} rounds)")
        print(f"  Price:   {pprice}g  [{affordable}]")

    in_shop = True
    while in_shop:
        clear_screen()

        ge.c.execute("SELECT bytes FROM player_stats WHERE player_id = ?", (player_id,))
        bytes = ge.c.fetchone()["bytes"]

        ge.c.execute("SELECT rowid, item, amount FROM inventory WHERE player_id = ?", (player_id,))
        inv_items = ge.c.fetchall()

        gear_end   = len(gear_stock)
        potion_end = gear_end + len(potion_stock)
        sell_end   = potion_end + len(inv_items)

        print(f"[ {node_name} ] — TRANSACTION")
        if fateful_day:
            print("  * FATEFUL DAY — rare stock available *")
        print(f"  bytes: {bytes}")
        print()

        print("  [ FOR SALE — GEAR ]")
        if gear_stock:
            for i, item in enumerate(gear_stock, 1):
                kind  = "WPN" if item in weapon_pool else "ARM"
                price = gear_price(item)
                tag   = "" if bytes >= price else " (can't afford)"
                print(f"  ({i}) [{kind}] {item['name']}  —  {item['class_type']}  —  {price}b{tag}")
        else:
            print("  (no gear in stock)")
        print()

        print("  [ FOR SALE — POTIONS ]")
        for j, pot in enumerate(potion_stock, gear_end + 1):
            pname, ptype, pheal, pbhit, pbcrit, pbdef, pdur, pprice = pot
            effects = []
            if pheal: effects.append(f"%{pheal}hp")
            if pbhit: effects.append(f"%{pbhit}hit")
            if pbcrit: effects.append(f"%{pbcrit}crit")
            if pbdef: effects.append(f"+{pbdef}barrier")
            tag = "" if bytes >= pprice else " (can't afford)"
            print(f"  ({j}) [POT] {pname}  —  {', '.join(effects)}  —  {pprice}b{tag}")
        print()

        print("  [ SELL ]")
        if inv_items:
            equipped_weapon, equipped_armor = get_equipped(player_id)
            for k, inv_row in enumerate(inv_items, potion_end + 1):
                ge.c.execute("SELECT * FROM weapons WHERE name = ?", (inv_row["item"],))
                wdata = ge.c.fetchone()
                ge.c.execute("SELECT * FROM armors WHERE name = ?", (inv_row["item"],))
                adata = ge.c.fetchone()
                idata = wdata or adata
                sv    = gear_sell_price(idata) if idata else 5
                equipped_tag = ""
                if inv_row["item"] == equipped_weapon:
                    equipped_tag = "  [EQUIPPED — WEAPON]"
                elif inv_row["item"] == equipped_armor:
                    equipped_tag = "  [EQUIPPED — ARMOR]"
                print(f"  ({k}) {inv_row['item']}  x{inv_row['amount']}  —  sell for {sv}b{equipped_tag}")
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
            show_gear_stats(item, price, bytes)
            print()
            print("  (1) buy")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                if bytes < price:
                    typewrite("  not enough bytes.", delay=0.02)
                    input("\npress enter...")
                else:
                    ge.c.execute("UPDATE player_stats SET bytes = bytes - ? WHERE player_id = ?",
                                 (price, player_id))
                    ge.add_item(player_id, item["name"], 1)
                    if item in weapon_pool:
                        ge.c.execute("UPDATE weapons SET found = 1 WHERE id = ?", (item["id"],))
                    else:
                        ge.c.execute("UPDATE armors  SET found = 1 WHERE id = ?", (item["id"],))
                    ge.conn.commit()
                    gear_stock.remove(item)
                    typewrite(f"  bought {item['name']} for {price}b.", delay=0.02)
                    input("\npress enter...")

        elif gear_end < choice <= potion_end:
            pot    = potion_stock[choice - gear_end - 1]
            pprice = pot[7]
            clear_screen()
            show_potion_stats(pot, bytes)
            print()
            print("  (1) buy")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                if bytes < pprice:
                    typewrite("  not enough bytes.", delay=0.02)
                    input("\npress enter...")
                else:
                    ge.c.execute("UPDATE player_stats SET bytes = bytes - ? WHERE player_id = ?",
                                 (pprice, player_id))
                    ge.add_item(player_id, pot[0], 1)
                    ge.conn.commit()
                    pot_idx = choice - gear_end - 1
                    potion_stock.pop(pot_idx)
                    if path_id:
                        ge.remove_shop_stock_item(path_id, pot[0])
                    typewrite(f"  bought {pot[0]} for {pprice}b.", delay=0.02)
                    input("\npress enter...")

        elif potion_end < choice <= sell_end:
            inv_row = inv_items[choice - potion_end - 1]
            ge.c.execute("SELECT * FROM weapons WHERE name = ?", (inv_row["item"],))
            wdata = ge.c.fetchone()
            ge.c.execute("SELECT * FROM armors WHERE name = ?", (inv_row["item"],))
            adata = ge.c.fetchone()
            idata = wdata or adata
            sv    = gear_sell_price(idata) if idata else 5

            clear_screen()
            if idata:
                show_gear_stats(idata, sv, bytes)
            else:
                print(f"  {inv_row['item']}")
            print(f"  Sell value: {sv}b")
            print()
            print("  (1) sell")
            print("  (2) back")
            try:
                confirm = int(input("> "))
            except ValueError:
                confirm = 2

            if confirm == 1:
                equipped_weapon, equipped_armor = get_equipped(player_id)

                # If selling the equipped item, unequip it first
                if inv_row["item"] == equipped_weapon:
                    ge.c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
                elif inv_row["item"] == equipped_armor:
                    ge.c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))

                # Remove from inventory (and clean up gear table if last copy)
                if inv_row["amount"] <= 1:
                    ge.remove_gear_item_by_rowid(player_id, inv_row["rowid"], inv_row["item"])
                else:
                    ge.c.execute(
                        "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                        (inv_row["rowid"],)
                    )
                    ge.conn.commit()

                ge.c.execute("UPDATE player_stats SET bytes = bytes + ? WHERE player_id = ?",
                            (sv, player_id))
                ge.conn.commit()

                # Rebuild stats in case we unequipped something
                ge.rebuild_stats(player_id)

                typewrite(f"  sold {inv_row['item']} for {sv}b.", delay=0.02)
                input("\npress enter...")


# ------------------------------------------------------------------ #
#  EVENTS                                                              #
# ------------------------------------------------------------------ #

def load_events():
    ge.c.execute("SELECT * FROM events LIMIT 1")
    row = ge.c.fetchone()
    if row:
        return dict(row)
    return {
        "blood_moon": 0, "solar_eclipse": 0, "flood_omnya": 0,
        "monster_rush": 0, "fateful_day": 0, "encounters_since_reset": 0,
    }


def apply_solar_eclipse(player_id, events, remove=False):
    if not events["solar_eclipse"]:
        return
    ge.c.execute("SELECT class_id FROM players WHERE id = ?", (player_id,))
    class_id = ge.c.fetchone()[0]
    ge.c.execute("SELECT name FROM class WHERE id = ?", (class_id,))
    class_name = ge.c.fetchone()[0]
    if class_name != "The Indexer":
        return
    if remove:
        ge.c.execute("UPDATE player_stats SET bonus_crit = bonus_crit / 2 WHERE player_id = ?",
                     (player_id,))
    else:
        ge.c.execute("UPDATE player_stats SET bonus_crit = bonus_crit * 2 WHERE player_id = ?",
                     (player_id,))
    ge.conn.commit()


def print_active_events(events):
    labels = {
        "blood_moon":    "BLOOD MOON    — enemies strike with doubled power",
        "solar_eclipse": "SOLAR ECLIPSE — The Indexer's crit surges",
        "flood_omnya":   "FLOOD OF OMNYA — some paths are inaccessible",
        "monster_rush":  "MONSTER RUSH  — enemies attack twice per round",
        "fateful_day":   "FATEFUL DAY   — rare loot floods the markets",
    }
    active = [v for k, v in labels.items() if events.get(k)]
    if active:
        remaining = ge.EVENT_EXPIRY_ENCOUNTERS - events.get("encounters_since_reset", 0)
        print(f"  [ ACTIVE EVENTS ]  (expire in ~{remaining} encounters)")
        for e in active:
            print(f"  * {e}")
        print()


def run_constraint_encounter(player_id, node_name, events, run_id=None):
    """CONSTRAINT node — fire a world event, then a combat encounter with modifiers applied."""
    clear_screen()
    typewrite(f"  [ {node_name} ] — CONSTRAINT", delay=0.02)
    print()

    # Fire an event
    result = ge.trigger_constraint_event(events)
    if result:
        key, name = result
        # Find the description from CONSTRAINT_EVENTS
        desc = next((e[2] for e in ge.CONSTRAINT_EVENTS if e[0] == key), "")
        typewrite(f"  EVENT TRIGGERED: {name}", delay=0.03)
        typewrite(f"  {desc}", delay=0.02)
        print()
        # Reload events so the combat sees the new flag
        events = load_events()

        # Solar eclipse may need to be applied immediately for The Indexer
        if key == "solar_eclipse":
            apply_solar_eclipse(player_id, events, remove=False)
    else:
        typewrite("  the database hums. no new events stir.", delay=0.02)
    input("\npress enter to face the encounter...")

    enemy_id = ge.generate_enemy(player_id)
    ge.apply_event_combat_modifiers(enemy_id, events)
    result_combat, _ = run_combat(player_id, enemy_id, events, run_id=run_id)

    # Tick the encounter counter — events may expire
    was_reset = ge.tick_event_counter()
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
        ge.c.execute(
            "SELECT rowid, item, amount FROM inventory WHERE player_id = ?",
            (player_id,)
        )
        items = ge.c.fetchall()
        equipped_weapon, equipped_armor = get_equipped(player_id)

        total_pages = max(1, (len(items) + INV_PAGE_SIZE - 1) // INV_PAGE_SIZE)
        page        = max(0, min(page, total_pages - 1))
        page_items  = items[page * INV_PAGE_SIZE : (page + 1) * INV_PAGE_SIZE]

        if not items:
            print("  inventory empty")
        else:
            print(f"  [ INVENTORY ]  page {page + 1}/{total_pages}")
            print()
            page_start = page * INV_PAGE_SIZE
            for display_num, row in enumerate(page_items, page_start + 1):
                tag = " [EQUIPPED]" if row["item"] in (equipped_weapon, equipped_armor) else ""
                print(f"  ({display_num})  {row['item']}  x{row['amount']}{tag}")

        print()
        nav = []
        if page > 0:             nav.append("(p) prev")
        if page < total_pages-1: nav.append("(n) next")
        nav.append("(0) back")
        print("  " + "   ".join(nav))
        print("  enter item number to inspect")
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

        # Map display number back to item (1-based across all pages)
        item_index = choice - 1
        if not (0 <= item_index < len(items)):
            continue
        selected_item = items[item_index]

        _inspect_item(player_id, selected_item, items)


def _inspect_item(player_id, selected_item, items):
    """Show item detail with equip/unequip and throw (with confirm) actions."""
    while True:
        equipped_weapon, equipped_armor = get_equipped(player_id)
        item_name = selected_item["item"]

        ge.c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
        weapon_data = ge.c.fetchone()
        ge.c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
        armor_data = ge.c.fetchone()

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
            potion_names = {p[0] for p in ge.get_potion_pool()}
            if item_name in potion_names:
                result = ge.apply_potion(player_id, item_name)
                if selected_item["amount"] <= 1:
                    ge.c.execute("DELETE FROM inventory WHERE rowid = ?", (selected_item["rowid"],))
                else:
                    ge.c.execute(
                        "UPDATE inventory SET amount = amount - 1 WHERE rowid = ?",
                        (selected_item["rowid"],)
                    )
                ge.conn.commit()
                clear_screen()
                if result.get("heal"):
                    typewrite(f"  restored {result['heal']} hp.", delay=0.02)
                if result.get("bonus_crit"):
                    typewrite(f"  crit +{result['bonus_crit']}.", delay=0.02)
                if result.get("defense"):
                    typewrite(f"  barrier +{result['defense']} (only active in combat).", delay=0.02)
                input("\npress enter...")
                return

            elif weapon_data:
                if is_equipped:
                    ge.rebuild_stats(player_id)
                    ge.c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
                    ge.conn.commit()
                else:
                    if equipped_weapon:
                        ge.c.execute("SELECT * FROM weapons WHERE name = ?", (equipped_weapon,))
                        current_data = ge.c.fetchone()
                        clear_screen()
                        print("  [ CURRENTLY EQUIPPED ]")
                        print_item_stats(current_data, equipped_weapon)
                        print()
                        print("  [ REPLACING WITH ]")
                        print_item_stats(weapon_data, item_name)
                        print()
                        print("  (1) yes, replace  (2) no, keep current")
                        if input("> ").strip() != "1":
                            return
                        ge.rebuild_stats(player_id)

                    ge.c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (item_name, player_id))
                    ge.rebuild_stats(player_id)
                    ge.conn.commit()
                return

            elif armor_data:
                if is_equipped:
                    ge.rebuild_stats(player_id)
                    ge.c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
                    ge.conn.commit()
                else:
                    if equipped_armor:
                        ge.c.execute("SELECT * FROM armors WHERE name = ?", (equipped_armor,))
                        current_data = ge.c.fetchone()
                        clear_screen()
                        print("  [ CURRENTLY EQUIPPED ]")
                        print_item_stats(current_data, equipped_armor)
                        print()
                        print("  [ REPLACING WITH ]")
                        print_item_stats(armor_data, item_name)
                        print()
                        print("  (1) yes, replace  (2) no, keep current")
                        if input("> ").strip() != "1":
                            return
                        ge.rebuild_stats(player_id)
                    ge.c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (item_name, player_id))
                    ge.rebuild_stats
                    ge.conn.commit()
                return

        elif action == "2":
            clear_screen()
            print(f"  throw away {item_name}?")
            print("  (1) yes, discard it")
            print("  (2) no, keep it")
            confirm = input("> ").strip()
            if confirm == "1":
                ge.remove_gear_item_by_rowid(player_id, selected_item["rowid"], item_name)
                typewrite(f"  {item_name} discarded.", delay=0.02)
                input("\npress enter...")
                return

        elif action == "3":
            return


# ------------------------------------------------------------------ #
#  ONE-TIME SETUP                                                      #
# ------------------------------------------------------------------ #
# ------------------------------------------------------------------ #
#  CHEAT CODES                                                         #
# ------------------------------------------------------------------ #

CHEAT_CODES = {
    "import antigravity":      {"desc": "it works on my machine.",                              "bytes": 0,    "hp": 0,   "xp": 0,   "items": [("Major Restore", 3)]},
    "print('hello world')":    {"desc": "the classic first program. starter energy.",           "bytes": 500,  "hp": 0,   "xp": 0,   "items": []},
    "pip install everything":  {"desc": "bloated inventory. potions everywhere.",               "bytes": 50,   "hp": 0,   "xp": 0,   "items": [("Minor Restore",3),("Minor Surge",2),("Minor Clarity",2),("Minor Barrier",2)]},
    "undefined is not a function": {"desc": "classic js error. gives you clarity.",            "bytes": 0,    "hp": 0,   "xp": 0,   "items": [("Clarity", 2), ("Grand Elixir", 1)]},
    "npm install":             {"desc": "node_modules materializes. +999 bytes.",               "bytes": 999,  "hp": 0,   "xp": 0,   "items": []},
    "nan === nan":             {"desc": "false. but you get a surge anyway.",                   "bytes": 0,    "hp": 0,   "xp": 0,   "items": [("Major Surge", 3)]},
    "segfault":                {"desc": "core dumped. hp fully restored.",                      "bytes": 0,    "hp": 9999,"xp": 0,   "items": []},
    "malloc":                  {"desc": "memory allocated. don't forget to free().",            "bytes": 750,  "hp": 0,   "xp": 0,   "items": []},
    "undefined behavior":      {"desc": "anything can happen. full heal + loot.",               "bytes": 100,  "hp": 9999,"xp": 0,   "items": [("Vital Surge",2),("Major Barrier",1)]},
    "java -jar":               {"desc": "compiling... please wait... +500 xp.",                "bytes": 0,    "hp": 0,   "xp": 500,  "items": []},
    "nullpointerexception":    {"desc": "defeated by null. full restore as compensation.",      "bytes": 0,    "hp": 9999,"xp": 0,   "items": [("Major Restore", 5)]},
    "drop table":              {"desc": "dropped the table. gained everything on it.",          "bytes": 1000, "hp": 9999,"xp": 1000, "items": []},
    "select *":                {"desc": "selected everything. you get everything.",             "bytes": 300,  "hp": 9999,"xp": 300,  "items": [("Grand Elixir",2),("Major Barrier",2)]},
    "commit":                  {"desc": "changes saved. +200 bytes, full heal.",               "bytes": 200,  "hp": 9999,"xp": 0,   "items": []},
    "borrow checker":          {"desc": "the compiler approves. massive stat surge.",           "bytes": 0,    "hp": 0,   "xp": 0,   "items": [("Major Surge",3),("Major Clarity",3)]},
    "rewrite it in rust":      {"desc": "it is faster now. +1500 bytes.",                      "bytes": 1500, "hp": 0,   "xp": 0,   "items": []},
    "<?php":                   {"desc": "you opened a php file. +999 bytes hazard pay.",        "bytes": 999,  "hp": 0,   "xp": 0,   "items": []},
    "if err != nil":           {"desc": "handle every error. earned a full restore.",           "bytes": 0,    "hp": 9999,"xp": 0,   "items": [("Vital Clarity", 3)]},
    "D-melan":                 {"desc": "name recognized. full restore, big bytes, hidden loot.","bytes": 2000,"hp": 9999,"xp": 999,  "items": [("Grand Elixir",3),("Major Barrier",3),("Major Surge",3)]},
    "cs50":                    {"desc": "this is cs50. welcome. +500 xp and a week of potions.","bytes": 500,  "hp": 0,   "xp": 500,  "items": [("Restore",5),("Surge",3),("Clarity",3),("Barrier",2)]},
}


def apply_cheat(player_id, code):
    cheat = CHEAT_CODES.get(code.strip()) or CHEAT_CODES.get(code.strip().lower())
    if not cheat:
        return False

    clear_screen()
    typewrite("  // CHEAT ACTIVATED", delay=0.02)
    typewrite(f"  > {code}", delay=0.02)
    print()
    typewrite(f"  {cheat['desc']}", delay=0.02)
    print()

    if cheat["bytes"]:
        ge.c.execute("UPDATE player_stats SET bytes = bytes + ? WHERE player_id = ?", (cheat["bytes"], player_id))
        typewrite(f"  +{cheat['bytes']} bytes", delay=0.01)

    if cheat["hp"]:
        ge.c.execute("UPDATE player_stats SET current_hp = MIN(current_hp + ?, max_hp) WHERE player_id = ?", (cheat["hp"], player_id))
        typewrite("  HP restored", delay=0.01)

    if cheat["xp"]:
        ge.c.execute("UPDATE players SET experience = experience + ? WHERE id = ?", (cheat["xp"], player_id))
        typewrite(f"  +{cheat['xp']} xp", delay=0.01)
        ge.c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
        row = ge.c.fetchone()
        while row["experience"] >= ge.experience_needed_for_next_level(row["level"]):
            ge.level_up(player_id)
            ge.c.execute("SELECT level, experience FROM players WHERE id = ?", (player_id,))
            row = ge.c.fetchone()

    for item_name, amount in cheat["items"]:
        ge.add_item(player_id, item_name, amount)
        typewrite(f"  +{amount}x {item_name}", delay=0.01)

    ge.conn.commit()
    input("\npress enter...")
    return True



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
            print("(3) tutorial")
            print("(4) reset database")
            print("(5) quit")
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
                run_tutorial()

            elif choice == "4":
                os.remove("game_data.db")
                ge.reconnect()
                initialize_game()
            
            elif choice == "5":
                print("connection closed.")
                quit()

        # ---- PLAY ---- #
        while play:
            clear_screen()
            unlocked_sets = ge.get_unlocked_gear_sets(player_id)
            total_clears  = ge.get_total_clears(player_id)
            lives         = ge.get_lives(player_id)
            life_icons    = "♥ " * lives + "♡ " * (3 - lives)

            print(f"  lives: {life_icons.strip()}   clears: {total_clears}")
            print()
            print("(0) adventure")
            print("(1) inventory")
            print("(2) equipped items and stats")
            print("(3) see last runs stats")
            print("(4) speak to the Archivist")
            if unlocked_sets:
                print("(6) gear sets")
            print("(5) back to menu")
            choice = input("> ")

            if choice == "0":
                adventuring = True
                play = False

            elif choice == "1":
                show_inventory_screen(player_id)

            elif choice == "2":
                clear_screen()
                equipped_weapon, equipped_armor = get_equipped(player_id)
                ge.c.execute("SELECT * FROM weapons WHERE name = ?", (equipped_weapon,))
                weapon_data = ge.c.fetchone()
                ge.c.execute("SELECT * FROM armors WHERE name = ?", (equipped_armor,))
                armor_data = ge.c.fetchone()

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
                print_run_stats(player_id)
                input("\npress enter to go back...")

            elif choice == "4":
                events = load_events()
                show_npc(player_id, events)

            elif choice == "6":
                show_gear_sets_screen(player_id)

            elif choice == "5":
                play = False
                menu = True

            else:
                apply_cheat(player_id, choice)

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
                run_id, current_node_id, seed = ge.init_run(player_id, custom_seed)
                random.seed(custom_seed)
            else:
                run_id, current_node_id, seed = ge.init_run(player_id)
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
                6:  "REST",
            }

            run_lost     = False
            path_running = True

            while path_running:
                clear_screen()
                node     = ge.get_path_node(current_node_id)
                enc_type = node["encounter_type"]

                print(f"[ {node['name']} ] — {ENCOUNTER_NAME.get(enc_type, '???')}")
                print(node["description"] or "")
                flavour = ge.get_node_flavour(enc_type)
                if flavour:
                    print()
                    typewrite(f"  {flavour}", delay=0.02)
                print()

                # Reload events before every node
                events = load_events()

                # ---- Dispatch encounter by type ---- #

                if enc_type == -1:
                    pass  # START — no encounter

                elif enc_type == 0:
                    ge.register_shop_visit(player_id, node["id"])
                    run_shop(player_id, node["name"], events, path_id=node["id"], run_seed=seed)

                elif enc_type in (1,):
                    # QUERY — standard combat
                    enemy_id = ge.generate_enemy(player_id)
                    ge.apply_event_combat_modifiers(enemy_id, events)
                    result, _ = run_combat(player_id, enemy_id, events, run_id=run_id)

                    if result == "lose":
                        ge.finish_run(run_id, "lose")
                        run_lost    = True
                        path_running = False
                        adventuring  = False
                        play         = True
                        break

                    was_reset = ge.tick_event_counter()
                    if was_reset:
                        events = load_events()
                        clear_screen()
                        typewrite("  the world settles — all active events have expired.", delay=0.02)
                        input("\npress enter...")

                elif enc_type in (2, 3):
                    # STORED_PROCEDURE / DEADLOCK — dungeon crawl
                    cleared = run_dungeon(player_id, node["name"], enc_type, events, run_id=run_id)
                    if not cleared:
                        ge.finish_run(run_id, "lose")
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
                            player_id, node["name"], events, run_id=run_id
                        )
                        if result_combat == "lose":
                            ge.finish_run(run_id, "lose")
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
                    enemy_id = ge.generate_enemy(player_id, is_boss=True)
                    ge.apply_event_combat_modifiers(enemy_id, events)
                    result, _ = run_combat(player_id, enemy_id, events, run_id=run_id)

                    if result == "lose":
                        ge.finish_run(run_id, "lose")
                        run_lost    = True
                        path_running = False
                        adventuring  = False
                        play         = True
                        break

                    # Boss kill — unique named loot
                    ge.c.execute("SELECT type FROM enemies WHERE id = ?", (enemy_id,))
                    boss_type = ge.c.fetchone()["type"]
                    boss_drops = ge.drop_boss_loot(player_id, boss_type)
                    if boss_drops:
                        clear_screen()
                        typewrite("  [ UNIQUE LOOT ]", delay=0.03)
                        for item_name, item_type in boss_drops:
                            typewrite(f"  {item_type.upper()}: {item_name}", delay=0.02)
                        input("\npress enter...")

                    # Check for ending
                    overflow_kills = ge.record_overflow_kill(player_id)
                    if overflow_kills >= ge.OVERFLOW_BOSSES_TOTAL:
                        ge.finish_run(run_id, "win")
                        total_clears = _handle_run_clear(player_id)
                        apply_solar_eclipse(player_id, events, remove=True)
                        ge.rebuild_stats(player_id)
                        # Show the ending cinematic only every 5 clears
                        if total_clears % 5 == 0:
                            show_ending(player_id)
                        else:
                            clear_screen()
                            typewrite("  all OVERFLOW bosses terminated.", delay=0.03)
                            typewrite(f"  total clears: {total_clears}", delay=0.02)
                            typewrite("  the schema holds... for now.", delay=0.03)
                            input("\npress enter to return to camp...")
                        path_running = False
                        adventuring  = False
                        play         = True
                        break
                elif enc_type == 6:
                    run_rest(player_id, node["name"])

                # Mark node finished
                ge.finish_node(node["id"])
                ge.record_run_node(run_id)

                # ---- Get next choices ---- #
                children = ge.get_path_children(node["id"])

                if not children:
                    clear_screen()
                    typewrite("run complete. returning to camp...", delay=0.03)
                    ge.finish_run(run_id, "win")
                    apply_solar_eclipse(player_id, events, remove=True)
                    ge.rebuild_stats(player_id)
                    _handle_run_clear(player_id)
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

                shops       = ge.get_visited_shops(player_id)
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
                    print(f"         ({shop_offset + 1}) {shops[0]['name']}")
                    print()

                print("  (0) flee — return to camp")
                print()

                try:
                    choice = int(input("> "))
                except ValueError:
                    continue

                if choice == 0:
                    ge.finish_run(run_id, "fled")
                    apply_solar_eclipse(player_id, events, remove=True)
                    ge.rebuild_stats(player_id)
                    path_running = False
                    adventuring  = False
                    play         = True

                elif 1 <= choice <= len(children):
                    chosen          = children[choice - 1]
                    current_node_id = chosen["id"]
                    ge.move_to_node(player_id, current_node_id)

                elif shops and shop_offset < choice <= shop_offset + len(shops):
                    chosen_shop     = shops[choice - shop_offset - 1]
                    current_node_id = chosen_shop["id"]
                    ge.move_to_node(player_id, current_node_id)

            if run_lost:
                clear_screen()
                stats = ge.get_run_stats(run_id)
                typewrite("  you have fallen. the run is over.", delay=0.03)
                print()
                print("  ══════════════════════════════")
                print("  [ RUN RECAP ]")
                print(f"  seed:          {stats['seed']}")
                print(f"  kills:         {stats['kills']}")
                print(f"  bytes earned:   {stats['bytes_earned']}")
                print(f"  nodes cleared: {stats['nodes_cleared']}")
                print("  ══════════════════════════════")
                apply_solar_eclipse(player_id, events, remove=True)
                ge.rebuild_stats(player_id)
                input("\npress enter...")

except KeyboardInterrupt:
    print("\nconnection closed.")
