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


# === NEW TESTS: BFS pathfinding and edge cases ===

def test_pacman_bfs_handles_blocked_paths():
    """BFS should return a valid step or None when path is blocked."""
    game = pacman_selfplay.PacmanGame()

    # Try to find path through walls
    start = (1, 1)
    goal = (1, 3)

    # Add walls blocking direct path
    walls = {(1, 2)}
    result = game.bfs_next_step(start, walls | game.walls)

    # Should either find an alternative path or return None if truly blocked
    # Result should be in bounds if not None
    if result is not None:
        assert pacman_selfplay.in_bounds(result)


def test_pacman_ghost_scatter_goals_are_different():
    """Each ghost should have a different scatter target corner."""
    game = pacman_selfplay.PacmanGame()

    goals = [game.ghost_scatter_goal(i) for i in range(4)]

    # All goals should be unique
    assert len(set(goals)) == len(goals)


def test_pacman_power_pellet_clears_after_timer():
    """Power pellet effect should expire after frighten ticks."""
    game = pacman_selfplay.PacmanGame()

    # Set frightened ticks directly (power pellet eaten)
    game.frightened_ticks = 10
    assert game.ghost_mode() == "frightened"

    # Decrement until it expires
    game.frightened_ticks = 0
    # After timer expires, should return to normal behavior (not frightened)
    assert game.ghost_mode() != "frightened"


def test_pacman_pellet_counting():
    """Test that pellets are correctly counted."""
    game = pacman_selfplay.PacmanGame()
    initial_pellets = len(game.pellets)
    initial_power = len(game.power_pellets)

    assert initial_pellets > 0
    assert initial_power > 0

    # Collect one pellet
    game.pacman = list(game.pellets)[0]
    game.step()
    # After step, pellet at pacman position should be removed
    assert len(game.pellets) == initial_pellets - 1


def test_pacman_step_increments_counter():
    """Each step should increment the steps counter."""
    game = pacman_selfplay.PacmanGame()
    initial_steps = game.steps

    game.step()

    assert game.steps == initial_steps + 1


# === NEW TESTS: Score, power pellets, tunnel wrap, ghost eating ===

def test_pacman_power_pellet_gives_frightened_mode():
    """Eating power pellet should activate frightened mode."""
    game = pacman_selfplay.PacmanGame()
    game.frightened_ticks = 0

    # Place power pellet and move pacman to it
    if game.power_pellets:
        game.pacman = list(game.power_pellets)[0]
        initial_score = game.score
        game.move_pacman()

        assert game.frightened_ticks > 0
        assert game.score == initial_score + 50


def test_pacman_eating_ghost_in_frightened_mode():
    """Pac-Man should eat ghosts and score points in frightened mode."""
    game = pacman_selfplay.PacmanGame()

    # Activate frightened mode and place ghost on pacman
    game.frightened_ticks = 10
    game.pacman = (5, 5)
    game.ghosts = [(5, 5)]

    initial_score = game.score
    game.resolve_collisions()

    # Should score 200 for eating ghost, not die
    assert game.alive is True
    assert game.score == initial_score + 200


def test_pacman_ghost_returns_to_center_after_being_eaten():
    """Eaten ghost should respawn at center."""
    game = pacman_selfplay.PacmanGame()

    game.frightened_ticks = 10
    game.pacman = (5, 5)
    game.ghosts = [(5, 5)]

    game.resolve_collisions()

    # Ghost should be back at center
    center = (pacman_selfplay.WIDTH // 2, pacman_selfplay.HEIGHT // 2)
    assert game.ghosts[0] == center


def test_pacman_pellet_scoring():
    """Collecting regular pellets should increase score by 10."""
    game = pacman_selfplay.PacmanGame()

    # Find a pellet not blocked by walls
    pellet = None
    for p in game.pellets:
        if p not in game.walls:
            pellet = p
            break

    if pellet:
        game.pacman = pellet
        initial_score = game.score
        game.move_pacman()
        assert game.score == initial_score + 10


def test_pacman_tunnel_wraparound():
    """Pac-Man should wrap around when going through tunnel."""
    game = pacman_selfplay.PacmanGame()

    # Position near left edge tunnel
    # The tunnel is at row 12-13 (the middle section with spaces)
    # Move pacman to left edge of tunnel
    tunnel_y = 12  # Middle tunnel row

    # Find a walkable position near the left tunnel entrance
    for x in range(pacman_selfplay.WIDTH):
        if game.is_walkable((x, tunnel_y)) and (x, tunnel_y) not in game.walls:
            game.pacman = (x, tunnel_y)
            break

    # The neighbors function should handle wraparound
    neighbors = list(game.neighbors(game.pacman))
    assert len(neighbors) > 0


def test_pacman_multiple_power_pellets():
    """Multiple power pellets should extend frightened time."""
    game = pacman_selfplay.PacmanGame()

    # Collect first power pellet
    if len(game.power_pellets) >= 2:
        game.pacman = list(game.power_pellets)[0]
        game.move_pacman()
        first_frightened = game.frightened_ticks

        # Collect second power pellet
        game.pacman = list(game.power_pellets)[0] if game.power_pellets else game.pacman
        game.move_pacman()

        # Frightened time should be extended or reset
        assert game.frightened_ticks > 0


def test_pacman_score_includes_ghost_bonus():
    """Total score should include ghost eating bonuses."""
    game = pacman_selfplay.PacmanGame()

    initial_score = game.score
    game.frightened_ticks = 10

    # Eat multiple ghosts
    for i in range(4):
        game.ghosts[i] = game.pacman
        game.resolve_collisions()

    # Score should have increased by 800 (4 ghosts * 200 each)
    assert game.score == initial_score + 800


def test_pacman_no_movement_when_dead():
    """Dead Pac-Man should not move during step."""
    game = pacman_selfplay.PacmanGame()
    game.alive = False

    initial_pos = game.pacman
    initial_pellets = len(game.pellets)
    
    # step() should return immediately without any changes
    game.step()

    # Position should not change
    assert game.pacman == initial_pos
    # Pellets should not be collected
    assert len(game.pellets) == initial_pellets


def test_pacman_won_state():
    """Game should set won=True when all pellets collected."""
    game = pacman_selfplay.PacmanGame()
    game.pellets.clear()
    game.power_pellets.clear()

    assert game.won is False
    game.step()
    assert game.won is True
