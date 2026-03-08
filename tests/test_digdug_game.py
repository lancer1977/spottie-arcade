import pytest

from src import digdug_selfplay


def test_digdug_digging_removes_dirt_and_awards_points(monkeypatch: pytest.MonkeyPatch):
    game = digdug_selfplay.DigDugGame()

    # Ensure we won't pump an enemy instead of moving.
    game.enemies = []

    # Put the player next to a dirt tile and force the next move onto it.
    game.player = (5, 5)
    target = (6, 5)
    game.dirt.add(target)

    monkeypatch.setattr(game, "choose_player_step", lambda: target)

    game.move_player()

    assert game.player == target
    assert target not in game.dirt
    assert game.score == 5


def test_digdug_pumping_enemy_defeats_after_two_pumps_and_awards_points():
    game = digdug_selfplay.DigDugGame()

    # Create a clean, deterministic arena.
    game.rocks = set()
    game.walls = set()

    game.player = (5, 5)
    game.facing = digdug_selfplay.RIGHT

    # Put one enemy in direct line of sight.
    game.enemies = [(7, 5)]
    game.enemy_pump = {0: 0}

    assert game.score == 0

    pumped = game.pump_if_possible()
    assert pumped is True
    assert game.enemy_pump[0] == 1
    assert game.enemies == [(7, 5)]
    assert game.score == 0

    pumped = game.pump_if_possible()
    assert pumped is True

    # After two pumps the enemy is removed and points are awarded.
    assert game.enemies == []
    assert game.score == 200


def test_digdug_player_defeat_when_enemy_touches_player():
    game = digdug_selfplay.DigDugGame()

    game.player = (10, 10)
    game.enemies = [(10, 10)]

    game.resolve_collisions()

    assert game.alive is False
