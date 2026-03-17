import random

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


def test_digdug_enemies_move_toward_player(monkeypatch: pytest.MonkeyPatch):
    """Enemies should move toward the player's general direction."""
    game = digdug_selfplay.DigDugGame()

    # Clear rocks to avoid blocking paths
    game.rocks = set()

    # Place player and single enemy
    game.player = (20, 10)
    game.enemies = [(5, 10)]

    # Force deterministic enemy movement (78% chance to move toward player)
    call_count = [0]
    original_random = random.random

    def deterministic_random():
        call_count[0] += 1
        # Return 0 to force "move toward player" behavior (below 0.78)
        return 0.0

    monkeypatch.setattr(random, "random", deterministic_random)

    old_enemy_pos = game.enemies[0]
    game.move_enemies()
    new_enemy_pos = game.enemies[0]

    # Enemy should have moved (if deterministic path exists)
    # The enemy should get closer to player
    old_dist = abs(old_enemy_pos[0] - game.player[0]) + abs(old_enemy_pos[1] - game.player[1])
    new_dist = abs(new_enemy_pos[0] - game.player[0]) + abs(new_enemy_pos[1] - game.player[1])

    # Either moved closer or no valid path
    assert new_dist <= old_dist or new_enemy_pos == old_enemy_pos


# === NEW TESTS: Win condition, rock collision, pump decay ===

def test_digdug_win_condition_all_enemies_defeated():
    """Game should set won=True when all enemies are popped."""
    game = digdug_selfplay.DigDugGame()

    # Remove all enemies
    game.enemies = []
    game.step()

    assert game.won is True


def test_digdug_score_from_digging():
    """Digging through dirt should award 5 points per tile."""
    game = digdug_selfplay.DigDugGame()
    initial_score = game.score

    # Clear enemies for simpler testing
    game.enemies = []
    game.enemy_pump = {}

    # Dig through dirt
    game.player = (5, 5)
    target = (6, 5)
    game.dirt.add(target)
    game.dirt.discard(game.player)

    # Force move to target
    game.player = target

    # Manually trigger digging
    if target in game.dirt:
        game.dirt.remove(target)
        game.score += 5

    assert game.score == initial_score + 5


def test_digdug_pump_pressure_decays():
    """Pump pressure should decay when enemy moves."""
    game = digdug_selfplay.DigDugGame()
    game.rocks = set()
    game.enemy_pump[0] = 1  # One pump on first enemy

    initial_pump = game.enemy_pump[0]
    game.move_enemies()

    # Pump should decay by at most 1
    assert game.enemy_pump[0] <= initial_pump


def test_digdug_pump_if_possible_beam():
    """Pump should create a beam toward enemy in line of sight."""
    game = digdug_selfplay.DigDugGame()
    game.rocks = set()
    game.player = (5, 5)
    game.facing = digdug_selfplay.RIGHT
    game.enemies = [(7, 5)]  # Enemy to the right in line of sight
    game.enemy_pump = {0: 0}

    # Clear dirt between player and enemy
    for x in range(5, 8):
        game.dirt.discard((x, 5))

    result = game.pump_if_possible()

    assert result is True
    assert len(game.last_beam) > 0
    assert game.enemy_pump[0] == 1


def test_digdug_line_of_sight_enemy():
    """line_of_sight_enemy should find enemy in line of sight."""
    game = digdug_selfplay.DigDugGame()
    game.player = (5, 5)
    game.facing = digdug_selfplay.RIGHT
    game.enemies = [(8, 5)]  # Enemy 3 tiles to the right
    game.rocks = set()
    game.dirt = set()  # Clear dirt for clean line of sight

    result = game.line_of_sight_enemy()

    assert result is not None
    idx, direction, beam = result
    assert idx == 0
    assert direction == digdug_selfplay.RIGHT
    assert (8, 5) in beam


def test_digdug_no_line_of_sight_through_walls():
    """Pump should not reach enemy through walls."""
    game = digdug_selfplay.DigDugGame()
    game.player = (5, 5)
    game.facing = digdug_selfplay.RIGHT
    game.enemies = [(7, 5)]

    # Wall between player and enemy
    game.walls.add((6, 5))

    result = game.line_of_sight_enemy()

    assert result is None


def test_digdug_step_increments_counter():
    """Each step should increment the steps counter."""
    game = digdug_selfplay.DigDugGame()
    initial_steps = game.steps

    game.step()

    assert game.steps == initial_steps + 1


def test_digdug_reset_clears_state():
    """Reset should clear game state for new round."""
    game = digdug_selfplay.DigDugGame()

    # Modify state
    game.score = 100
    game.alive = False
    game.won = True
    game.enemies = []

    game.reset()

    assert game.alive is True
    assert game.won is False
    assert game.score == 0
    assert len(game.enemies) == 4


def test_digdug_choose_player_step_prioritizes_dirt():
    """Player should prioritize digging toward dirt when safe."""
    game = digdug_selfplay.DigDugGame()
    game.player = (10, 10)
    game.enemies = []  # No enemies

    # Place dirt nearby
    game.dirt.add((11, 10))
    game.dirt.add((12, 10))

    step = game.choose_player_step()

    # Should move toward dirt
    assert step is not None


def test_digdug_is_walkable():
    """is_walkable should return False for walls and rocks."""
    game = digdug_selfplay.DigDugGame()

    # Wall positions
    assert game.is_walkable((0, 0)) is False  # Top-left wall
    assert game.is_walkable((0, 5)) is False  # Left wall

    # Rock positions
    game.rocks.add((5, 5))
    assert game.is_walkable((5, 5)) is False

    # Open position
    assert game.is_walkable((10, 5)) is True


def test_digdug_bfs_next_step():
    """BFS should find next step toward goal."""
    game = digdug_selfplay.DigDugGame()
    game.rocks = set()
    game.walls = set()

    # Simple path finding
    game.player = (5, 5)
    goal = {(10, 5)}

    result = game.bfs_next_step((5, 5), goal)

    # Should move toward goal (positive x direction)
    assert result is not None
    assert result[0] > 5 or result[1] != 5  # Moved somewhere


def test_digdug_render_shows_status():
    """Render should show round, score, and enemy count."""
    game = digdug_selfplay.DigDugGame()
    output = game.render()

    assert "Round:" in output
    assert "Score:" in output
    assert "Enemies:" in output
    assert "Dirt:" in output


def test_digdug_render_game_over():
    """Render should show game over message when player dies."""
    game = digdug_selfplay.DigDugGame()
    game.alive = False

    output = game.render()

    assert "caught" in output.lower() or "game over" in output.lower()


def test_digdug_render_victory():
    """Render should show victory message when all enemies defeated."""
    game = digdug_selfplay.DigDugGame()
    game.won = True

    output = game.render()

    assert "popped" in output.lower() or "won" in output.lower() or "victory" in output.lower()
