import sqlite3 as sql
import json
import database
sql.connect("game_data.db")

run = True
menu = True
play = False

database.init_db()
database.init_classes()

def loot_init():
    weapons = 0
    while weapons <= 100:
        database.init_weapon()
        weapons += 1
     



def player_setting():
    username = input("username: ")
    choose_class = input("(1) Warrior (2) Mage (3) Rogue\n type: ")
    if choose_class == "1":
        class_name = "Warrior"
    elif choose_class == "2":
        class_name = "Mage"
    elif choose_class == "3":
        class_name = "Rogue"
    else:
        class_name = "NaN"

    while class_name == "NaN":
        print("invald type")
        choose_class = input("(1) Melee (2) Range (3) Magic\n type: ")
    database.init_player(username=username, class_name=class_name)
    


while run:
    while menu:
        print("(1) new game")
        print("(2) load game")
        print("(3) quit game")
        choice = input("-> ")
        if choice == "1":
            player_setting()
            menu = False
            run = True
        elif choice == "2":
            pass
        elif choice == "3":
            quit()



    while play:
        pass
