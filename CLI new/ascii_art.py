# ascii_art.py
# Enemy and boss ASCII art — glitchy/corrupted database theme
# Each entry is a list of strings, one per line

ENEMY_ART = {

    "Corrupted Index": [
        r"  ╔═[ERR]═╗  ",
        r"  ║ ▓░▓░▓ ║  ",
        r"  ║ ░[◉]░ ║  ",
        r"  ║ ▓░▓░▓ ║  ",
        r"  ╚══╦═╦══╝  ",
        r"   ░╔╩═╩╗░   ",
        r"   ▓║   ║▓   ",
        r"  ░╔╩╗ ╔╩╗░  ",
        r"  ▓║ ║ ║ ║▓  ",
        r"  ░╚═╝ ╚═╝░  ",
    ],

    "Null Pointer": [
        r"   \  NULL /    ",
        r"    \/0x0\/     ",
        r"    ░░╔═╗░░     ",
        r"    ░░║∅║░░     ",
        r"  ───░╚═╝░───   ",
        r"    ░/ | \░     ",
        r"   ░/ /|\ \░    ",
        r"  ░/_/ | \_\░   ",
        r"      _|_        ",
        r"    ░[___]░      ",
    ],

    "Stack Overflow": [
        r"  [■][■][■][■]  ",
        r"  [■][■][■][■]  ",
        r"  [■][◉][■][■]  ",
        r"  [■][■][■][■]  ",
        r">>STACK FULL!<< ",
        r"  [▓][▓][▓][▓]  ",
        r"  [▓][▓][▓][▓]  ",
        r"   ▓▓▓▓▓▓▓▓▓▓   ",
        r"   \________/    ",
        r"    |      |     ",
    ],

    "Deadlock Wraith": [
        r"  ░░░≈≈≈░░░    ",
        r" ░╔══╗ ╔══╗░   ",
        r" ░║ WAIT  ║░   ",
        r" ░╚══╝ ╚══╝░   ",
        r" ░ ≈[LOCK]≈░   ",
        r"  ░≈≈╔═╗≈≈░   ",
        r"  ░░░║⊗║░░░   ",
        r"   ░░╚═╝░░     ",
        r"  ░/░░░░░\░     ",
        r" ░/░░░░░░░\░    ",
    ],

    "Zombie Process": [
        r"   <DEFUNCT>    ",
        r"  ╔═[PID:??]╗   ",
        r"  ║ ☠  ☠    ║   ",
        r"  ║   ___   ║   ",
        r"  ║  /   \  ║   ",
        r"  ╚═════════╝     ",
        r"   /‾‾‾‾‾‾‾\     ",
        r"  / ░ ░ ░ ░ \    ",
        r" |░░░░░░░░░░░|   ",
        r"  \_░_░_░_░_/    ",
    ],

}

BOSS_ART = {

    "The Warlord": [
        r"      ╔▓▓▓▓▓╗       ",
        r"    ╔═╬▓╔═╗▓╬═╗     ",
        r"    ║▓▓║◈║◈║▓▓║     ",
        r"    ╚═╦╬▓▓▓╬╦═╝     ",
        r"    ══╬╬═╬═╬╬══     ",
        r"      ║╔═╧═╗║       ",
        r"      ║║▓▓▓║║       ",
        r"    ╔═╩╩═══╩╩═╗     ",
        r"    ║░▓░▓░▓░▓░║     ",
        r"    ╚═════════╝    ",
        r"    /█\     /█\    ",
        r"   /███\   /███\   ",
    ],

    "The Tyrant": [
        r"    ░▒▓[TYRANT]▓▒░   ",
        r"   ╔══╗  ╔═╗  ╔══╗  ",
        r"   ║◉◉║  ║▓║  ║◉◉║  ",
        r"   ╚═╦╝╔═╩═╩═╗╚╦═╝  ",
        r"  ═══╬═╬▓▓▓▓▓╬═╬═══ ",
        r"     ║ ╚═════╝ ║   ",
        r"     ╠═[ACCESS]╣   ",
        r"     ║[DENIED] ║   ",
        r"     ╠═════════╣   ",
        r"    ╔╩╗       ╔╩╗  ",
        r"    ╚═╝       ╚═╝  ",
    ],

    "The Behemoth": [
        r" ╔═════════════════╗ ",
        r" ║▓▓╔══╗░░░╔══╗▓▓▓ ║ ",
        r" ║▓▓║◉◉║░░░║◉◉║▓▓▓ ║ ",
        r" ║▓▓╚══╩═══╩══╝▓▓▓ ║ ",
        r" ║▓▓░░░░___░░░░▓▓▓ ║ ",
        r" ╠═════════════════╣ ",
        r" ║░░[BEHEMOTH.EXE]░║ ",
        r" ╠═════════════════╣ ",
        r" ║█▓█▓█▓█▓█▓█▓█▓█▓ ║ ",
        r" ╚════╦══════╦═════╝ ",
        r"   ╔══╩╗    ╔╩══╗    ",
        r"   ╚═══╝    ╚═══╝    ",
    ],

    "The Archmage": [
        r"    ░░░░/\░░░░      ",
        r"   ░░░/╔══╗\░░░    ",
        r"   ░░║◈║▓▓║◈║░░    ",
        r"   ░░╚╦╚══╝╦╝░░    ",
        r" ≈≈≈≈╬╬════╬╬≈≈≈≈   ",
        r"   ░░║SELECT║░░    ",
        r"   ░░║  * ░ ║░░    ",
        r"   ░░║ FROM ║░░    ",
        r"   ░░║SOULS;║░░    ",
        r"  ░░░╚══════╝░░░   ",
        r"  ░░░░|░░░░|░░░░   ",
        r" ░░░░░|░░░░|░░░░░  ",
    ],

    "The Overseer": [
        r"  ┌─────────────┐   ",
        r"  │ OVERSEER.DB │   ",
        r"  │ ░░[STATUS]░░│   ",
        r"  │  ◉       ◉  │   ",
        r"  │  └──[▓]──┘  │   ",
        r"  │░░░░░░░░░░░░░│   ",
        r"  ├─────────────┤   ",
        r"  │ALL ROWS READ│   ",
        r"  │NO ESCAPE :) │   ",
        r"  ├─────────────┤   ",
        r"  │▓▓▓▓▓▓▓▓▓▓▓▓ │   ",
        r"  └─────────────┘   ",
    ],

}


def get_enemy_art(enemy_type: str) -> list:
    """Return ASCII art lines for a given enemy type string.
    Falls back to a generic glitch block if not found.
    """
    # Boss names start with "OVERFLOW — "
    if enemy_type.startswith("OVERFLOW — "):
        boss_name = enemy_type.replace("OVERFLOW — ", "")
        return BOSS_ART.get(boss_name, _fallback_boss())

    return ENEMY_ART.get(enemy_type, _fallback_enemy())


def _fallback_enemy():
    return [
        r"  ╔═[UNKNOWN]═╗  ",
        r"  ║ ?  ?  ?   ║  ",
        r"  ║  [ERROR]  ║  ",
        r"  ║ ?  ?  ?   ║  ",
        r"  ╚═══════════╝  ",
        r"    ░ ░ ░ ░ ░    ",
        r"   ░ ░ ░ ░ ░ ░   ",
        r"  ░ ░ ░ ░ ░ ░ ░  ",
        r"   ░_░_░_░_░_░   ",
        r"    ‾‾‾‾‾‾‾‾‾    ",
    ]


def _fallback_boss():
    return [
        r"  ╔══[OVERFLOW]══╗  ",
        r"  ║ ◉◉◉◉◉◉◉◉◉◉   ║  ",
        r"  ║ ◉╔════════╗◉ ║  ",
        r"  ║ ◉║ BOSS?? ║◉ ║  ",
        r"  ║ ◉╚════════╝◉ ║  ",
        r"  ╠══════════════╣  ",
        r"  ║▓▓▓▓▓▓▓▓▓▓▓▓▓ ║  ",
        r"  ╠══════════════╣  ",
        r"  ║░░░░░░░░░░░░░ ║  ",
        r"  ╚══════════════╝  ",
        r"   /██\      /██\   ",
        r"  /████\    /████\  ",
    ]


def print_enemy_art(enemy_type: str):
    """Print the ASCII art for the given enemy type."""
    for line in get_enemy_art(enemy_type):
        print(line)
