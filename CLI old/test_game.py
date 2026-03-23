"""
test_game.py — SQLite Mania test suite
Runs against an isolated in-memory database — never touches game_data.db.
"""

import sqlite3
import random
import sys
import os
import pytest

# ------------------------------------------------------------------ #
#  Patch database.py to use an in-memory DB before importing          #
# ------------------------------------------------------------------ #

import unittest.mock as mock
import json

# ------------------------------------------------------------------ #
#  Wire database.py to an in-memory SQLite connection                 #
# ------------------------------------------------------------------ #

_mem_conn = sqlite3.connect(":memory:")
_mem_conn.row_factory = sqlite3.Row
_mem_c = _mem_conn.cursor()

with mock.patch("sqlite3.connect", return_value=_mem_conn):
    import database as db

db.conn = _mem_conn
db.c    = _mem_c

# Stub typewrite used inside init_run (database.py calls it directly)
# We patch it as a no-op at the db module level
db_typewrite_patcher = mock.patch("builtins.print")
db_typewrite_patcher.start()
db_typewrite_patcher.stop()


def _armor_json_side_effect(f):
    """Return list for armor files, dict for weapon files."""
    try:
        name = f.name if hasattr(f, "name") else str(f)
    except Exception:
        name = ""
    if "armor" in name:
        return ["Iron Vest", "Steel Coat", "Chain Mail"]
    return {"first_name": ["Alpha", "Beta", "Gamma"], "second_name": ["Blade", "Shard", "Edge"]}


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _gear_open_mock():
    """Context manager that returns the right mock file for weapon/armor JSON."""
    return mock.patch("builtins.open", mock.mock_open(read_data='["Iron Vest","Steel Coat","Chain Mail"]'))


def _gear_json_mock():
    """Patch json.load to return list for armor, dict for weapon."""
    call_count = {"n": 0}
    def side_effect(f):
        # generate_gear opens the file then calls json.load(f)
        # We detect armor vs weapon by checking db's current gear_type context
        # Simplest: always return a dict that works for both
        return {"first_name": ["Alpha", "Beta", "Gamma"],
                "second_name": ["Blade", "Shard", "Edge"],
                0: "Iron Vest", 1: "Steel Coat", 2: "Chain Mail"}
    return mock.patch("json.load", side_effect=side_effect)


def setup_db():
    """Full DB init — run before each test that needs it."""
    # Must set PRAGMA outside any transaction for it to take effect
    old_isolation = db.conn.isolation_level
    db.conn.isolation_level = None  # autocommit mode
    db.conn.execute("PRAGMA foreign_keys = OFF")
    db.conn.isolation_level = old_isolation

    tables = [r[0] for r in db.c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    for t in tables:
        db.conn.execute(f"DROP TABLE IF EXISTS [{t}]")
    for t in [r[0] for r in db.c.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    ).fetchall()]:
        db.conn.execute(f"DROP TRIGGER IF EXISTS [{t}]")
    db.conn.commit()

    db.conn.isolation_level = None
    db.conn.execute("PRAGMA foreign_keys = ON")
    db.conn.isolation_level = old_isolation

    with mock.patch("builtins.print"):
        db.init_db()
        db.init_classes()
        _patch_and_generate_loot()
        db.init_map()
        db.init_node_flavour()


def _patch_and_generate_loot():
    """Generate starter loot with correct per-type JSON mocks."""
    original_generate = db.generate_gear

    def patched_generate(player_level=1, gear_type="random"):
        import random as _random
        if gear_type == "random":
            gear_type = _random.choice(["weapon", "armor"])
        if gear_type == "armor":
            with mock.patch("builtins.open", mock.mock_open(read_data='["Iron Vest","Steel Coat","Chain Mail"]')):
                with mock.patch("json.load", return_value=["Iron Vest", "Steel Coat", "Chain Mail"]):
                    return original_generate(player_level, gear_type)
        else:
            with mock.patch("builtins.open", mock.mock_open(read_data='')):
                with mock.patch("json.load", return_value={"first_name": ["Alpha","Beta","Gamma"], "second_name": ["Blade","Shard","Edge"]}):
                    return original_generate(player_level, gear_type)

    with mock.patch.object(db, "generate_gear", side_effect=patched_generate):
        db.loot_init()


def make_player(username="testuser", class_name="The Executor"):
    with mock.patch("builtins.print"):
        return db.init_player(username, class_name)


def make_enemy(player_id, is_boss=False):
    return db.generate_enemy(player_id, is_boss=is_boss)


# ------------------------------------------------------------------ #
#  Test: DB initialisation                                             #
# ------------------------------------------------------------------ #

class TestDBInit:
    def setup_method(self):
        setup_db()

    def test_tables_exist(self):
        tables = [r[0] for r in db.c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        for t in ["players", "player_stats", "class", "weapons", "armors",
                  "enemies", "runs", "path", "inventory", "events",
                  "status_effects", "shop_stock", "visited_shops",
                  "boss_loot", "meta", "node_flavour", "map"]:
            assert t in tables, f"missing table: {t}"

    def test_events_row_exists(self):
        row = db.c.execute("SELECT * FROM events LIMIT 1").fetchone()
        assert row is not None

    def test_classes_seeded(self):
        rows = db.c.execute("SELECT name FROM class").fetchall()
        names = {r["name"] for r in rows}
        assert {"The Executor", "The Indexer", "The Trigger"} == names

    def test_loot_init_generates_gear(self):
        w = db.c.execute("SELECT COUNT(*) FROM weapons").fetchone()[0]
        a = db.c.execute("SELECT COUNT(*) FROM armors").fetchone()[0]
        assert w >= 20
        assert a >= 20

    def test_map_populated(self):
        count = db.c.execute("SELECT COUNT(*) FROM map").fetchone()[0]
        assert count > 0

    def test_node_flavour_populated(self):
        count = db.c.execute("SELECT COUNT(*) FROM node_flavour").fetchone()[0]
        assert count > 0


# ------------------------------------------------------------------ #
#  Test: Player creation                                               #
# ------------------------------------------------------------------ #

class TestPlayerCreation:
    def setup_method(self):
        setup_db()

    def test_player_created(self):
        pid = make_player("novo")
        row = db.c.execute("SELECT * FROM players WHERE id = ?", (pid,)).fetchone()
        assert row is not None
        assert row["username"] == "novo"

    def test_player_stats_created(self):
        pid = make_player("novo2")
        stats = db.c.execute("SELECT * FROM player_stats WHERE player_id = ?", (pid,)).fetchone()
        assert stats is not None
        assert stats["current_hp"] > 0
        assert stats["max_hp"] > 0

    def test_current_hp_equals_max_hp_on_creation(self):
        pid = make_player("novo5")
        stats = db.c.execute("SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (pid,)).fetchone()
        assert stats["current_hp"] == stats["max_hp"]

    def test_duplicate_username_raises(self):
        make_player("dupeuser")
        with pytest.raises(Exception, match="UNIQUE constraint failed"):
            make_player("dupeuser")

    def test_invalid_class_raises(self):
        with pytest.raises(ValueError):
            db.init_player("badclass", "The Nonexistent")

    def test_executor_has_highest_hp(self):
        pid_exec = make_player("exec1", "The Executor")
        pid_idx  = make_player("idx1",  "The Indexer")
        exec_hp = db.c.execute("SELECT base_hp FROM player_stats WHERE player_id = ?", (pid_exec,)).fetchone()[0]
        idx_hp  = db.c.execute("SELECT base_hp FROM player_stats WHERE player_id = ?", (pid_idx,)).fetchone()[0]
        assert exec_hp > idx_hp

    def test_indexer_has_highest_crit(self):
        pid_exec = make_player("exec2", "The Executor")
        pid_idx  = make_player("idx2",  "The Indexer")
        exec_crit = db.c.execute("SELECT base_crit FROM player_stats WHERE player_id = ?", (pid_exec,)).fetchone()[0]
        idx_crit  = db.c.execute("SELECT base_crit FROM player_stats WHERE player_id = ?", (pid_idx,)).fetchone()[0]
        assert idx_crit > exec_crit


# ------------------------------------------------------------------ #
#  Test: Enemy generation                                              #
# ------------------------------------------------------------------ #

class TestEnemyGeneration:
    def setup_method(self):
        setup_db()
        self.pid = make_player("fighter")

    def test_enemy_created(self):
        eid = make_enemy(self.pid)
        row = db.c.execute("SELECT * FROM enemies WHERE id = ?", (eid,)).fetchone()
        assert row is not None

    def test_enemy_type_is_known_profile(self):
        eid = make_enemy(self.pid)
        row = db.c.execute("SELECT type FROM enemies WHERE id = ?", (eid,)).fetchone()
        assert row["type"] in db.ENEMY_PROFILES

    def test_boss_has_overflow_prefix(self):
        eid = make_enemy(self.pid, is_boss=True)
        row = db.c.execute("SELECT type FROM enemies WHERE id = ?", (eid,)).fetchone()
        assert row["type"].startswith("OVERFLOW —")

    def test_boss_has_more_hp_than_normal(self):
        eid_normal = make_enemy(self.pid)
        eid_boss   = make_enemy(self.pid, is_boss=True)
        normal_hp = db.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (eid_normal,)).fetchone()[0]
        boss_hp   = db.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (eid_boss,)).fetchone()[0]
        assert boss_hp > normal_hp

    def test_enemy_hp_above_minimum(self):
        for _ in range(10):
            eid = make_enemy(self.pid)
            hp = db.c.execute("SELECT base_hp FROM enemies WHERE id = ?", (eid,)).fetchone()[0]
            assert hp >= 40

    def test_enemy_hit_above_minimum(self):
        for _ in range(10):
            eid = make_enemy(self.pid)
            hit = db.c.execute("SELECT base_hit FROM enemies WHERE id = ?", (eid,)).fetchone()[0]
            assert hit >= 8


# ------------------------------------------------------------------ #
#  Test: XP curve                                                      #
# ------------------------------------------------------------------ #

class TestXPCurve:
    def test_level_1_xp(self):
        assert db.experience_needed_for_next_level(1) == 100

    def test_curve_is_increasing(self):
        prev = db.experience_needed_for_next_level(1)
        for level in range(2, 15):
            curr = db.experience_needed_for_next_level(level)
            assert curr > prev, f"XP curve not increasing at level {level}"
            prev = curr

    def test_level_below_1_returns_100(self):
        assert db.experience_needed_for_next_level(0) == 100

    def test_level_up_increments_level(self):
        setup_db()
        pid = make_player("leveler")
        needed = db.experience_needed_for_next_level(1)
        db.c.execute("UPDATE players SET experience = ? WHERE id = ?", (needed, pid))
        db.conn.commit()
        db.level_up(pid)
        row = db.c.execute("SELECT level FROM players WHERE id = ?", (pid,)).fetchone()
        assert row["level"] == 2

    def test_level_up_increases_stats(self):
        setup_db()
        pid = make_player("leveler2")
        before = db.c.execute("SELECT base_hp, base_hit FROM player_stats WHERE player_id = ?", (pid,)).fetchone()
        needed = db.experience_needed_for_next_level(1)
        db.c.execute("UPDATE players SET experience = ? WHERE id = ?", (needed, pid))
        db.conn.commit()
        with mock.patch("builtins.print"):
            db.level_up(pid)
        after = db.c.execute("SELECT base_hp, base_hit FROM player_stats WHERE player_id = ?", (pid,)).fetchone()
        assert after["base_hp"] > before["base_hp"]
        assert after["base_hit"] > before["base_hit"]

    def test_level_up_without_enough_xp_raises(self):
        setup_db()
        pid = make_player("leveler3")
        with pytest.raises(ValueError):
            db.level_up(pid)


# ------------------------------------------------------------------ #
#  Test: Potions                                                        #
# ------------------------------------------------------------------ #

class TestPotions:
    def setup_method(self):
        setup_db()
        self.pid = make_player("potion_user")
        # Damage player to half HP so heals have room
        db.c.execute("UPDATE player_stats SET current_hp = max_hp / 2 WHERE player_id = ?", (self.pid,))
        db.conn.commit()

    def test_restore_heals_percentage_of_max_hp(self):
        stats_before = db.c.execute(
            "SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (self.pid,)
        ).fetchone()
        result = db.apply_potion(self.pid, "Minor Restore")
        assert result.get("heal") is not None
        expected_heal = max(1, int(stats_before["max_hp"] * 15 / 100))
        assert result["heal"] == expected_heal

    def test_heal_does_not_exceed_max_hp(self):
        # Set HP to almost full
        db.c.execute("UPDATE player_stats SET current_hp = max_hp - 1 WHERE player_id = ?", (self.pid,))
        db.conn.commit()
        db.apply_potion(self.pid, "Major Restore")
        stats = db.c.execute("SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()
        assert stats["current_hp"] <= stats["max_hp"]

    def test_surge_adds_bonus_hit(self):
        before = db.c.execute("SELECT bonus_hit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()[0]
        result = db.apply_potion(self.pid, "Minor Surge")
        after  = db.c.execute("SELECT bonus_hit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()[0]
        assert after > before
        stats = db.c.execute("SELECT base_hit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()
        expected = max(1, int(stats["base_hit"] * 8 / 100))
        assert result.get("bonus_hit") == expected

    def test_clarity_adds_bonus_crit(self):
        before = db.c.execute("SELECT bonus_crit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()[0]
        result = db.apply_potion(self.pid, "Minor Clarity")
        after  = db.c.execute("SELECT bonus_crit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()[0]
        assert after > before
        stats = db.c.execute("SELECT base_crit FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()
        expected = max(1, int(stats["base_crit"] * 8 / 100))
        assert result.get("bonus_crit") == expected

    def test_barrier_returns_defense_value(self):
        result = db.apply_potion(self.pid, "Minor Barrier")
        assert result.get("defense") == 200

    def test_unknown_potion_returns_empty(self):
        result = db.apply_potion(self.pid, "Nonexistent Brew")
        assert result == {}


# ------------------------------------------------------------------ #
#  Test: Status effects                                                #
# ------------------------------------------------------------------ #

class TestStatusEffects:
    def setup_method(self):
        setup_db()
        self.pid = make_player("status_victim")

    def test_apply_status(self):
        db.apply_status(self.pid, "DEADLOCK", 2)
        statuses = db.get_statuses(self.pid)
        assert any(s["effect"] == "DEADLOCK" for s in statuses)

    def test_tick_decrements_duration(self):
        db.apply_status(self.pid, "CORRUPTION", 3)
        db.tick_statuses(self.pid)
        statuses = db.get_statuses(self.pid)
        remaining = [s for s in statuses if s["effect"] == "CORRUPTION"]
        assert remaining[0]["duration"] == 2

    def test_tick_removes_expired_status(self):
        db.apply_status(self.pid, "SEGFAULT", 1)
        db.tick_statuses(self.pid)
        statuses = db.get_statuses(self.pid)
        assert not any(s["effect"] == "SEGFAULT" for s in statuses)

    def test_corruption_deals_dot_damage(self):
        stats_before = db.c.execute(
            "SELECT current_hp, max_hp FROM player_stats WHERE player_id = ?", (self.pid,)
        ).fetchone()
        db.apply_status(self.pid, "CORRUPTION", 2)
        log = db.tick_statuses(self.pid)
        stats_after = db.c.execute(
            "SELECT current_hp FROM player_stats WHERE player_id = ?", (self.pid,)
        ).fetchone()
        assert stats_after["current_hp"] < stats_before["current_hp"]
        assert any("CORRUPTION" in line for line in log)

    def test_corruption_does_not_kill(self):
        # Set HP to 1, CORRUPTION should clamp to 1
        db.c.execute("UPDATE player_stats SET current_hp = 1 WHERE player_id = ?", (self.pid,))
        db.conn.commit()
        db.apply_status(self.pid, "CORRUPTION", 2)
        db.tick_statuses(self.pid)
        hp = db.c.execute("SELECT current_hp FROM player_stats WHERE player_id = ?", (self.pid,)).fetchone()[0]
        assert hp >= 1

    def test_multiple_statuses_can_stack(self):
        db.apply_status(self.pid, "DEADLOCK", 2)
        db.apply_status(self.pid, "CORRUPTION", 2)
        statuses = db.get_statuses(self.pid)
        effects = {s["effect"] for s in statuses}
        assert "DEADLOCK" in effects
        assert "CORRUPTION" in effects


# ------------------------------------------------------------------ #
#  Test: Run lifecycle                                                  #
# ------------------------------------------------------------------ #

class TestRunLifecycle:
    def setup_method(self):
        setup_db()
        self.pid = make_player("runner")

    def _init_run(self):
        with mock.patch("builtins.print"):
            return db.init_run(self.pid, custom_seed=12345)

    def test_init_run_returns_ids(self):
        run_id, root_id, seed = self._init_run()
        assert run_id is not None
        assert root_id is not None
        assert seed == 12345

    def test_run_row_created(self):
        run_id, _, _ = self._init_run()
        row = db.c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row is not None
        assert row["seed"] == 12345

    def test_record_run_kill(self):
        run_id, _, _ = self._init_run()
        db.record_run_kill(run_id)
        db.record_run_kill(run_id)
        row = db.c.execute("SELECT kills FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["kills"] == 2

    def test_record_run_bytes(self):
        run_id, _, _ = self._init_run()
        db.record_run_bytes(run_id, 50)
        db.record_run_bytes(run_id, 30)
        row = db.c.execute("SELECT bytes_earned FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["bytes_earned"] == 80

    def test_record_run_node(self):
        run_id, _, _ = self._init_run()
        db.record_run_node(run_id)
        db.record_run_node(run_id)
        row = db.c.execute("SELECT nodes_cleared FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["nodes_cleared"] == 2

    def test_finish_run_sets_outcome(self):
        run_id, _, _ = self._init_run()
        db.finish_run(run_id, "win")
        row = db.c.execute("SELECT outcome FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["outcome"] == "win"

    def test_get_run_stats(self):
        run_id, _, _ = self._init_run()
        db.record_run_kill(run_id)
        stats = db.get_run_stats(run_id)
        assert stats["kills"] == 1
        assert stats["seed"] == 12345


# ------------------------------------------------------------------ #
#  Test: generate_path tree structure                                  #
# ------------------------------------------------------------------ #

class TestGeneratePath:
    def setup_method(self):
        setup_db()
        self.pid = make_player("pathfinder")

    def _make_run(self):
        with mock.patch("builtins.print"):
            return db.init_run(self.pid, custom_seed=42)

    def test_root_node_exists(self):
        run_id, root_id, _ = self._make_run()
        row = db.c.execute("SELECT * FROM path WHERE id = ?", (root_id,)).fetchone()
        assert row is not None
        assert row["encounter_type"] == -1  # START

    def test_depth1_has_shop(self):
        run_id, root_id, _ = self._make_run()
        children = db.c.execute(
            "SELECT * FROM path WHERE parent_id = ?", (root_id,)
        ).fetchall()
        enc_types = [c["encounter_type"] for c in children]
        assert 0 in enc_types, "depth 1 should always have a shop (type 0)"

    def test_depth4_all_bosses(self):
        run_id, root_id, _ = self._make_run()
        depth4 = db.c.execute(
            "SELECT * FROM path WHERE run_id = ? AND depth = 4", (run_id,)
        ).fetchall()
        assert len(depth4) > 0
        for node in depth4:
            assert node["encounter_type"] == 5, "all depth-4 nodes should be OVERFLOW (5)"

    def test_same_seed_produces_same_tree(self):
        pid2 = make_player("pathfinder2")
        with mock.patch("builtins.print"):
            run_id1, root_id1, _ = db.init_run(self.pid, custom_seed=999)
            run_id2, root_id2, _ = db.init_run(pid2,      custom_seed=999)

        def get_structure(run_id):
            rows = db.c.execute(
                "SELECT depth, branch, encounter_type FROM path WHERE run_id = ? ORDER BY id",
                (run_id,)
            ).fetchall()
            return [(r["depth"], r["branch"], r["encounter_type"]) for r in rows]

        assert get_structure(run_id1) == get_structure(run_id2)

    def test_no_boss_nodes_in_middle_depths(self):
        run_id, root_id, _ = self._make_run()
        middle = db.c.execute(
            "SELECT * FROM path WHERE run_id = ? AND depth IN (1,2,3)", (run_id,)
        ).fetchall()
        for node in middle:
            assert node["encounter_type"] != 5, f"boss found in depth {node['depth']}"


# ------------------------------------------------------------------ #
#  Test: Shop stock persistence                                        #
# ------------------------------------------------------------------ #

class TestShopStock:
    def setup_method(self):
        setup_db()
        # shop_stock.path_id has a FK to path — insert minimal run+path rows
        self.pid = make_player("shopkeeper")
        with mock.patch("builtins.print"):
            self.run_id, self.root_id, _ = db.init_run(self.pid, custom_seed=1)
        # Use root_id as a valid path_id for stock tests
        self.path_id_a = self.root_id
        # Insert a second path node for the overwrite test
        db.c.execute("""
            INSERT INTO path (run_id, parent_id, depth, branch, name, description, encounter_type, level_range)
            VALUES (?, ?, 1, 0, 'TestShop', 'desc', 0, 0)
        """, (self.run_id, self.root_id))
        db.conn.commit()
        self.path_id_b = db.c.lastrowid

    def test_save_and_load_stock(self):
        stock = [("weapon", "Alpha Blade"), ("potion", "Minor Restore")]
        db.save_shop_stock(path_id=self.path_id_a, stock=stock)
        loaded = db.load_shop_stock(path_id=self.path_id_a)
        assert loaded is not None
        assert loaded[0]["item_type"] == "weapon"
        assert loaded[0]["item_name"] == "Alpha Blade"
        assert loaded[1]["item_name"] == "Minor Restore"

    def test_save_does_not_overwrite(self):
        stock1 = [("weapon", "Alpha Blade")]
        stock2 = [("armor",  "Iron Vest")]
        db.save_shop_stock(path_id=self.path_id_b, stock=stock1)
        db.save_shop_stock(path_id=self.path_id_b, stock=stock2)
        loaded = db.load_shop_stock(path_id=self.path_id_b)
        assert loaded[0]["item_name"] == "Alpha Blade"

    def test_load_returns_none_for_unknown_path(self):
        result = db.load_shop_stock(path_id=9999)
        assert result is None


# ------------------------------------------------------------------ #
#  Test: Events system                                                 #
# ------------------------------------------------------------------ #

class TestEvents:
    def setup_method(self):
        setup_db()

    def _get_events(self):
        row = db.c.execute("SELECT * FROM events LIMIT 1").fetchone()
        return dict(row)

    def test_trigger_constraint_event(self):
        events = self._get_events()
        result = db.trigger_constraint_event(events)
        assert result is not None
        key, name = result
        assert key in {e[0] for e in db.CONSTRAINT_EVENTS}

    def test_tick_event_counter_increments(self):
        db.tick_event_counter()
        row = db.c.execute("SELECT encounters_since_reset FROM events LIMIT 1").fetchone()
        assert row[0] == 1

    def test_events_reset_after_threshold(self):
        # Trigger an event
        events = self._get_events()
        db.trigger_constraint_event(events)
        # Tick up to the threshold
        for _ in range(db.EVENT_EXPIRY_ENCOUNTERS):
            db.tick_event_counter()
        row = db.c.execute("SELECT * FROM events LIMIT 1").fetchone()
        assert row["encounters_since_reset"] == 0
        assert row["blood_moon"] == 0

    def test_no_duplicate_event_triggered(self):
        # Activate all events manually
        db.c.execute("""
            UPDATE events SET blood_moon=1, solar_eclipse=1, flood_omnya=1,
                              monster_rush=1, fateful_day=1
        """)
        db.conn.commit()
        events = self._get_events()
        result = db.trigger_constraint_event(events)
        assert result is None  # nothing left to trigger


# ------------------------------------------------------------------ #
#  Test: generate_gear scaling                                         #
# ------------------------------------------------------------------ #

class TestGearGeneration:
    def setup_method(self):
        setup_db()

    def _gen(self, level, gear_type="weapon"):
        original = db.generate_gear
        if gear_type == "armor":
            with mock.patch("builtins.open", mock.mock_open(read_data='["Iron Vest","Steel Coat"]')):
                with mock.patch("json.load", return_value=["Iron Vest", "Steel Coat", "Chain Mail"]):
                    return original(level, gear_type)
        else:
            with mock.patch("builtins.open", mock.mock_open(read_data='')):
                with mock.patch("json.load", return_value={"first_name": ["Alpha","Beta"], "second_name": ["Blade","Shard"]}):
                    return original(level, gear_type)

    def test_generates_weapon(self):
        rowid, name, gtype = self._gen(1, "weapon")
        assert gtype == "weapon"
        row = db.c.execute("SELECT * FROM weapons WHERE id = ?", (rowid,)).fetchone()
        assert row is not None

    def test_generates_armor(self):
        rowid, name, gtype = self._gen(1, "armor")
        assert gtype == "armor"
        row = db.c.execute("SELECT * FROM armors WHERE id = ?", (rowid,)).fetchone()
        assert row is not None

    def test_higher_level_produces_higher_stats_on_average(self):
        random.seed(42)
        stats_l1 = []
        stats_l10 = []
        for _ in range(20):
            rid, _, _ = self._gen(1, "weapon")
            row = db.c.execute("SELECT bonus_hp + bonus_hit + bonus_crit AS total FROM weapons WHERE id = ?", (rid,)).fetchone()
            stats_l1.append(row["total"])
        for _ in range(20):
            rid, _, _ = self._gen(10, "weapon")
            row = db.c.execute("SELECT bonus_hp + bonus_hit + bonus_crit AS total FROM weapons WHERE id = ?", (rid,)).fetchone()
            stats_l10.append(row["total"])
        assert sum(stats_l10) / len(stats_l10) > sum(stats_l1) / len(stats_l1)

    def test_gear_has_element(self):
        rid, _, _ = self._gen(1, "weapon")
        row = db.c.execute("SELECT element FROM weapons WHERE id = ?", (rid,)).fetchone()
        assert row["element"] in ["QUERY", "LOCK", "OVERFLOW", "NULL"]


# ------------------------------------------------------------------ #
#  Test: Element / weakness system                                     #
# ------------------------------------------------------------------ #

class TestElementSystem:
    def test_weakness_cycle_is_complete(self):
        elements = set(db.ELEMENT_WEAKNESS.keys())
        targets  = set(db.ELEMENT_WEAKNESS.values())
        assert elements == targets  # every element is both a beater and a target

    def test_enemy_element_map_covers_all_profiles(self):
        for enemy_type in db.ENEMY_PROFILES:
            assert enemy_type in db.ENEMY_ELEMENT, f"{enemy_type} missing from ENEMY_ELEMENT"

    def test_no_element_beats_itself(self):
        for elem, target in db.ELEMENT_WEAKNESS.items():
            assert elem != target


# ------------------------------------------------------------------ #
#  Test: Meta / first launch                                           #
# ------------------------------------------------------------------ #

class TestMeta:
    def setup_method(self):
        setup_db()

    def test_is_first_launch_true_initially(self):
        assert db.is_first_launch() is True

    def test_mark_intro_shown(self):
        db.mark_intro_shown()
        assert db.is_first_launch() is False

    def test_mark_intro_shown_idempotent(self):
        db.mark_intro_shown()
        db.mark_intro_shown()  # should not raise
        assert db.is_first_launch() is False


# ------------------------------------------------------------------ #
#  Test: overflow_kills / ending trigger                               #
# ------------------------------------------------------------------ #

class TestOverflowKills:
    def setup_method(self):
        setup_db()
        self.pid = make_player("endgamer")

    def test_record_overflow_kill_increments(self):
        total = db.record_overflow_kill(self.pid)
        assert total == 1
        total = db.record_overflow_kill(self.pid)
        assert total == 2

    def test_overflow_bosses_total_is_5(self):
        assert db.OVERFLOW_BOSSES_TOTAL == 5

    def test_ending_threshold_reached(self):
        for _ in range(db.OVERFLOW_BOSSES_TOTAL):
            total = db.record_overflow_kill(self.pid)
        assert total >= db.OVERFLOW_BOSSES_TOTAL


# ------------------------------------------------------------------ #
#  Test: node flavour                                                  #
# ------------------------------------------------------------------ #

class TestNodeFlavour:
    def setup_method(self):
        setup_db()

    def test_returns_line_for_known_type(self):
        for enc_type in [0, 1, 2, 3, 4, 5, 6]:
            line = db.get_node_flavour(enc_type)
            assert isinstance(line, str) and len(line) > 0

    def test_returns_empty_for_unknown_type(self):
        line = db.get_node_flavour(99)
        assert line == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
