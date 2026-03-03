import time
import database


# --- Game state flags ---
run = True
menu = True
play = False
adventuring = False
in_fight = False
inventory = False
selecting_item = False
player_id = None


def clear_screen():
    """Push old output out of view."""
    print("\n" * 100)


def typewrite(text, delay=0.03):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()  # newline at the end

def new_game():
    """Prompt for a username and class, then create a new player in the database."""
    clear_screen()
    username = input("username: ")
    choose_class = input("(1) Warrior (2) Mage (3) Rogue\n> ")

    if choose_class == "1":
        class_name = "Warrior"
    elif choose_class == "2":
        class_name = "Mage"
    elif choose_class == "3":
        class_name = "Rogue"
    else:
        print("invalid class")
        return None

    return database.init_player(username, class_name)


def load_game():
    """List existing saves and let the player pick one by ID."""
    clear_screen()
    database.c.execute("SELECT id, username FROM players")
    usernames = database.c.fetchall()

    print("players:")
    for username in usernames:
        print(f"({username['id']}) {username['username']}")

    user_id = input("choose number: ")
    database.c.execute("SELECT id FROM players WHERE id = ?", (user_id,))
    row = database.c.fetchone()

    if not row:
        print("save not found")
        return None

    return row["id"]

def adventure():
    # calculate the 3 possible encounter types based on player level and class
    
    database.c.execute("SELECT level, class_type FROM players WHERE id = ?", (player_id,))
    row = database.c.fetchone()
    player_level = row["level"]
    player_class = row["class_type"]



def get_equipped(player_id):
    """Return (equipped_weapon_name, equipped_armor_name) for the given player."""
    database.c.execute("SELECT equipped_weapon FROM players WHERE id = ?", (player_id,))
    row = database.c.fetchone()
    equipped_weapon = row["equipped_weapon"] if row else None

    database.c.execute("SELECT equipped_armor FROM players WHERE id = ?", (player_id,))
    row = database.c.fetchone()
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


# --- One-time setup ---

typewrite("initializing database...", delay=0.01)
database.init_db()
typewrite("initializing classes...", delay=0.01)
database.init_classes()
typewrite("initializing loot tables...", delay=0.01)
typewrite("gived starter items...", delay=0.01)
database.loot_init()
typewrite("initializing map...", delay=0.01)
database.init_map()
print("ready!")

try:
    # ------------------------------------------------------------------ #
    #  MAIN LOOP                                                         #
    # ------------------------------------------------------------------ #
    while run:

        # ---- MENU ---- #
        while menu:
            clear_screen()
            print("(1) new game")
            print("(2) load game")
            print("(3) quit")
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
                quit()

        # ---- PLAY ---- #
        while play:
            clear_screen()  # clear before showing the play menu each iteration
            print("(0) adventure")
            print("(1) inventory")
            print("(2) equipped items")
            print("(3) quit to menu")
            choice = input("> ")

            # -- Adventure -- #
            if choice == "0":
                adventuring = True
                play = False

            # -- Inventory -- #
            elif choice == "1":
                inventory = True

                while inventory:
                    clear_screen()  # refresh inventory list on every loop iteration

                    # Fetch all items for this player
                    database.c.execute(
                        "SELECT rowid, item, amount FROM inventory WHERE player_id = ?",
                        (player_id,)
                    )
                    items = database.c.fetchall()

                    # Get currently equipped items
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
                        # Non-numeric input — just re-show the inventory
                        continue

                    if choice == 0:
                        # Exit inventory back to play menu
                        inventory = False
                        continue

                    # ---- Item selected ---- #
                    selecting_item = True
                    inventory = False

                    while selecting_item:
                        # Re-fetch equipped state in case it changed mid-session
                        equipped_weapon, equipped_armor = get_equipped(player_id)

                        selected_item = next((i for i in items if i["rowid"] == choice), None)

                        if not selected_item:
                            clear_screen()
                            print("Item not found.")
                            selecting_item = False
                            inventory = True
                            break

                        item_name = selected_item["item"]

                        # Look up item type in weapons and armors tables
                        database.c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
                        weapon_data = database.c.fetchone()
                        database.c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
                        armor_data = database.c.fetchone()

                        clear_screen()

                        # Display stats depending on item type
                        if weapon_data:
                            print_item_stats(weapon_data, f"WEAPON — {item_name}")
                        elif armor_data:
                            print_item_stats(armor_data, f"ARMOR  — {item_name}")
                        else:
                            print(f"(no stat data found for '{item_name}')")

                        is_equipped = item_name in (equipped_weapon, equipped_armor)

                        print("(1)", "unequip" if is_equipped else "use/equip")
                        print("(2) throw")
                        print("(3) go back")
                        print("choose action:")
                        action = input("> ")

                        if action == "1":
                            # Equip or unequip the selected item
                            if weapon_data:
                                if is_equipped:
                                    database.bonus_calc(database.BonusType.WEAPON, player_id=player_id, remove=True)
                                    database.c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
                                else:
                                    database.c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (item_name, player_id))
                                    database.bonus_calc(database.BonusType.WEAPON, player_id=player_id)
                                database.conn.commit()

                            elif armor_data:
                                if is_equipped:
                                    database.bonus_calc(database.BonusType.ARMOR, player_id=player_id, remove=True)
                                    database.c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
                                else:
                                    database.c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (item_name, player_id))
                                    database.bonus_calc(database.BonusType.ARMOR, player_id=player_id)
                                database.conn.commit()

                            selecting_item = False
                            inventory = True  # return to inventory list

                        elif action == "2":
                            # Throw / permanently discard the item
                            database.c.execute("DELETE FROM inventory WHERE rowid = ?", (selected_item["rowid"],))
                            database.conn.commit()
                            selecting_item = False
                            inventory = True  # return to inventory list

                        elif action == "3":
                            # Go back to inventory list without doing anything
                            selecting_item = False
                            inventory = True

            # -- Equipped items summary -- #
            elif choice == "2":
                clear_screen()

                equipped_weapon, equipped_armor = get_equipped(player_id)

                database.c.execute("SELECT * FROM weapons WHERE name = ?", (equipped_weapon,))
                weapon_data = database.c.fetchone()
                database.c.execute("SELECT * FROM armors WHERE name = ?", (equipped_armor,))
                armor_data = database.c.fetchone()

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
                input("\npress enter to go back...")

            # -- Quit to menu -- #
            elif choice == "3":
                play = False
                menu = True

        while adventuring:
            clear_screen()
            typewrite("adventuring...")
            print("\n" * 3)
            


            
            

except KeyboardInterrupt:
    # Ctrl+C pressed — exit cleanly without a traceback
    print("\nGoodbye!")
