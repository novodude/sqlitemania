import database

run = True
menu = True
play = False
player_id = None


def loot_init():
    database.c.execute("SELECT COUNT(*) FROM weapons")
    count = database.c.fetchone()[0]
    if count < 100:
        for _ in range(100 - count):
            database.init_weapon()


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
        print("(2) equipped weapon")
        print("(3) quit to menu")
        choice = input("> ")

        if choice == "1":
            database.c.execute(
                "SELECT item, amount FROM inventory WHERE player_id = ?",
                (player_id,)
            )
            items = database.c.fetchall()
            if not items:
                print("inventory empty")
            for i in items:
                print(i["item"], "x", i["amount"])

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
