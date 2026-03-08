import pytest

from src import pacman_selfplay


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def test_pacman_maze_parsing_builds_walls_and_pellets_sets():
    game = pacman_selfplay.PacmanGame()

    # A couple of known tiles from MAZE_RAW.
    assert (0, 0) in game.walls
    # Note: Pac-Man's spawn may land on a pellet tile and the game clears spawn tiles.
    assert (2, 1) in game.pellets
    assert (1, 3) in game.power_pellets

    # Ensure no overlaps.
    assert game.walls.isdisjoint(game.pellets)
    assert game.walls.isdisjoint(game.power_pellets)


def test_pacman_ghost_mode_cycles_scatter_then_chase_then_scatter():
    game = pacman_selfplay.PacmanGame()

    game.frightened_ticks = 0
    game.steps = 0
    assert game.ghost_mode() == "scatter"

    game.steps = pacman_selfplay.SCATTER_TICKS
    assert game.ghost_mode() == "chase"

    game.steps = pacman_selfplay.GHOST_MODE_CYCLE_TICKS
    assert game.ghost_mode() == "scatter"


def test_pacman_frightened_mode_overrides_base_schedule(monkeypatch: pytest.MonkeyPatch):
    game = pacman_selfplay.PacmanGame()

    # Force deterministic choice of the "best" frightened move.
    monkeypatch.setattr(pacman_selfplay.random, "random", lambda: 0.0)

    game.pacman = (10, 10)
    game.ghosts = [(10, 9)]
    game.frightened_ticks = 10

    old = game.ghosts[0]
    game.move_ghost(0)
    new = game.ghosts[0]

    assert game.ghost_mode() == "frightened"
    assert manhattan(new, game.pacman) >= manhattan(old, game.pacman)


def test_pacman_scatter_mode_moves_toward_scatter_corner(monkeypatch: pytest.MonkeyPatch):
    game = pacman_selfplay.PacmanGame()

    # Force deterministic choice to take the BFS step.
    monkeypatch.setattr(pacman_selfplay.random, "random", lambda: 0.0)

    game.frightened_ticks = 0
    game.steps = 0  # scatter

    game.ghosts = [(pacman_selfplay.WIDTH // 2, pacman_selfplay.HEIGHT // 2)]
    goal = game.ghost_scatter_goal(0)

    old = game.ghosts[0]
    expected = game.bfs_next_step(old, {goal})
    assert expected is not None

    game.move_ghost(0)
    assert game.ghosts[0] == expected


def test_pacman_chase_mode_uses_bfs_step_toward_pacman(monkeypatch: pytest.MonkeyPatch):
    game = pacman_selfplay.PacmanGame()

    # Force deterministic choice to take the BFS step.
    monkeypatch.setattr(pacman_selfplay.random, "random", lambda: 0.0)

    game.frightened_ticks = 0
    game.steps = pacman_selfplay.SCATTER_TICKS  # chase

    game.pacman = (1, 1)
    game.ghosts = [(pacman_selfplay.WIDTH - 2, pacman_selfplay.HEIGHT - 2)]

    old = game.ghosts[0]
    expected = game.bfs_next_step(old, {game.pacman})
    assert expected is not None

    game.move_ghost(0)
    assert game.ghosts[0] == expected


def test_pacman_win_condition_triggers_when_all_pellets_collected():
    game = pacman_selfplay.PacmanGame()

    game.pellets.clear()
    game.power_pellets.clear()
    game.step()

    assert game.won is True


def test_pacman_lose_condition_triggers_when_ghost_catches_pacman():
    game = pacman_selfplay.PacmanGame()

    game.frightened_ticks = 0
    game.pacman = (5, 5)
    game.ghosts = [(5, 5)]

    game.resolve_collisions()
    assert game.alive is False
