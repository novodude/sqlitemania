import database

run = True
menu = True
play = False
inventory = False
selecting_item = False
player_id = None


def loot_init():
    database.c.execute("SELECT COUNT(*) FROM weapons")
    count = database.c.fetchone()[0]
    if count < 100:
        for _ in range(100 - count):
            database.init_weapon()
    database.c.execute("SELECT COUNT(*) FROM armors")
    count = database.c.fetchone()[0]
    if count < 100:
        for _ in range(100 - count):
            database.init_armor()


def new_game():
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
    database.c.execute("SELECT id, username FROM players")
    usernames = database.c.fetchall()
    print("players:")
    for username in usernames:
        print(f"({username["id"]}) {username["username"]}")
    user_id = input("choose number: ")
    database.c.execute(
        "SELECT id FROM players WHERE id = ?",
        (user_id,)
    )
    row = database.c.fetchone()
    if not row:
        print("save not found")
        return None
    return row["id"]


database.init_db()
database.init_classes()
loot_init()


while run:
    while menu:
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

    while play:
        print("(1) inventory")
        print("(2) equipped items")
        print("(3) quit to menu")
        choice = input("> ")

        if choice == "1":
            inventory = True
            while inventory:
                database.c.execute(
                    "SELECT rowid, item, amount FROM inventory WHERE player_id = ?",
                    (player_id,)
                )
                items = database.c.fetchall()

                database.c.execute(
                    "SELECT equipped_weapon FROM players WHERE id = ?",
                    (player_id,)
                )
                row_1 = database.c.fetchone()
                equipped_weapon = row_1[0] if row_1 else None

                database.c.execute(
                    "SELECT equipped_armor FROM players WHERE id = ?",
                    (player_id,)
                )
                row_2 = database.c.fetchone()
                equipped_armor = row_2[0] if row_2 else None
                if not items:
                    print("inventory empty")

                for rowid, item, amount in items:
                    if item == equipped_weapon or item == equipped_armor:
                        print(rowid, item, "x", amount, "[EQUIPPED]")
                    else:
                        print(rowid, item, "x", amount)
                print("(0) to exist")
                print("choose item by number")
                choice = int(input("> "))
                if choice == 0: play = True; inventory = False
                if choice: selecting_item = True; inventory = False
                while selecting_item:
                    selected_item = next((i for i in items if i["rowid"] == choice), None)
                    if selected_item:
                        item_name = selected_item["item"]
                        database.c.execute("SELECT * FROM weapons WHERE name = ?", (item_name,))
                        weapon_data = database.c.fetchone()
                        database.c.execute("SELECT * FROM armors WHERE name = ?", (item_name,))
                        armor_data = database.c.fetchone()

                        print("====================")
                        print(selected_item["rowid"], selected_item["item"])

                        if weapon_data:
                            print("| Class:", weapon_data["class_type"], "\t", "|")
                            print("| Hit Multiplier:", weapon_data["hit_mult"], "\t", "|")
                            print("| Bonus HP:", weapon_data["bonus_hp"], "\t", "|")
                            print("| Bonus Hit:", weapon_data["bonus_hit"], "\t", "|")
                            print("| Bonus Wisdom:", weapon_data["bonus_wisdom"], "\t", "|")
                            
                        print("====================")
                    else:
                        print("Item not found")
                    is_equipped = (
                        item_name == equipped_weapon
                        or item_name == equipped_armor
                    )

                    if is_equipped:
                        print("(1) unequip")
                    else:
                        print("(1) use/equip")
                    print("(2) throw")
                    print("(3) go back")
                    print("choose action:")
                    choice = input("> ")
                    if choice == "1":

                        if weapon_data:
                            if equipped_weapon:
                                database.c.execute("UPDATE players SET equipped_weapon = NULL WHERE id = ?", (player_id,))
                                database.conn.commit()
                            else:
                                database.c.execute("UPDATE players SET equipped_weapon = ? WHERE id = ?", (item_name, player_id))
                                database.conn.commit()
                        elif armor_data:
                            if equipped_armor:
                                database.c.execute("UPDATE players SET equipped_armor = NULL WHERE id = ?", (player_id,))
                                database.conn.commit()
                            else:
                                database.c.execute("UPDATE players SET equipped_armor = ? WHERE id = ?", (item_name, player_id))
                                database.conn.commit()

                        selecting_item = False
                        inventory = True
                    elif choice == "2":
                        database.c.execute("DELETE FROM inventory WHERE rowid = ?", (selected_item["rowid"],))
                        database.conn.commit()
                        selecting_item = False
                        inventory = True
                    elif choice == "3":
                        selecting_item = False
                        inventory = True
        elif choice == "2":
            database.c.execute(
                "SELECT equipped_weapon FROM players WHERE id = ?",
                (player_id,)
            )
            weapon = database.c.fetchone()["equipped_weapon"]
            print("equipped:", weapon)

        elif choice == "3":
            play = False
            menu = True
