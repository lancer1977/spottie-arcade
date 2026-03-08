from collections import deque

import pytest

from src import snake_selfplay


def test_snake_board_initialization_returns_valid_2d_array():
    game = snake_selfplay.SnakeGame()
    grid = game.build_grid()

    assert isinstance(grid, list)
    assert len(grid) == snake_selfplay.HEIGHT
    assert all(isinstance(row, list) for row in grid)
    assert all(len(row) == snake_selfplay.WIDTH for row in grid)

    # Ensure grid cells are single-character strings.
    assert all(isinstance(cell, str) and len(cell) == 1 for row in grid for cell in row)


def test_snake_movement_updates_snake_position_correctly(monkeypatch: pytest.MonkeyPatch):
    game = snake_selfplay.SnakeGame()

    # Force deterministic movement: one step to the RIGHT.
    monkeypatch.setattr(game, "compute_next_move", lambda: snake_selfplay.RIGHT)

    old_head = game.snake[0]
    game.step()

    expected_head = snake_selfplay.add(old_head, snake_selfplay.RIGHT)
    assert game.snake[0] == expected_head


def test_snake_collision_detection_wall(monkeypatch: pytest.MonkeyPatch):
    game = snake_selfplay.SnakeGame()

    # Put head at the left edge and force move LEFT (out of bounds).
    game.snake = deque([(0, 0), (1, 0), (2, 0)])
    game.food = (10, 10)
    monkeypatch.setattr(game, "compute_next_move", lambda: snake_selfplay.LEFT)

    game.step()

    assert game.alive is False


def test_snake_collision_detection_self(monkeypatch: pytest.MonkeyPatch):
    game = snake_selfplay.SnakeGame()

    # Create a shape where moving RIGHT causes head to hit body (excluding the tail).
    # Head at (2, 2). Body occupies (3,2) so RIGHT is a self-collision.
    game.snake = deque([(2, 2), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2)])
    game.food = (10, 10)
    monkeypatch.setattr(game, "compute_next_move", lambda: snake_selfplay.RIGHT)

    game.step()

    assert game.alive is False
