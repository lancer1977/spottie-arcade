#!/usr/bin/env python3
"""
ANSI Snake that plays itself and restarts after game over.

Controls: Ctrl+C to quit.
"""

from __future__ import annotations

import random
import sys
import time
from collections import deque


# Board dimensions (play area only; border is drawn around it)
WIDTH = 24
HEIGHT = 16

# Timing
TICK_SECONDS = 0.06
RESTART_DELAY_SECONDS = 1.2


UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = (UP, DOWN, LEFT, RIGHT)


def add(p: tuple[int, int], d: tuple[int, int]) -> tuple[int, int]:
    return p[0] + d[0], p[1] + d[1]


def in_bounds(p: tuple[int, int]) -> bool:
    return 0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT


def neighbors(p: tuple[int, int]):
    for d in DIRS:
        q = add(p, d)
        if in_bounds(q):
            yield q


class SnakeGame:
    def __init__(self) -> None:
        self.round_id = 0
        self.reset()

    def reset(self) -> None:
        self.round_id += 1
        cx, cy = WIDTH // 2, HEIGHT // 2
        # Head at index 0
        self.snake: deque[tuple[int, int]] = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.direction = RIGHT
        self.alive = True
        self.score = 0
        self.steps = 0
        self.food = self.spawn_food()

    def spawn_food(self) -> tuple[int, int]:
        occupied = set(self.snake)
        cells = [(x, y) for y in range(HEIGHT) for x in range(WIDTH) if (x, y) not in occupied]
        return random.choice(cells) if cells else (-1, -1)

    def compute_next_move(self) -> tuple[int, int]:
        """
        Strategy:
        1) BFS shortest path to food through safe cells.
        2) If unavailable, pick a move that maximizes space reachable from new head.
        """
        head = self.snake[0]
        body = list(self.snake)

        # Moving into current tail is safe if not eating this turn.
        static_blocked = set(body[:-1])

        path = self._bfs_path(head, self.food, static_blocked)
        if path:
            nxt = path[0]
            return nxt[0] - head[0], nxt[1] - head[1]

        # Fallback: choose best safe move by flood-fill free-space score.
        best_dir = self.direction
        best_space = -1
        for d in DIRS:
            nxt = add(head, d)
            if not in_bounds(nxt):
                continue
            if nxt in static_blocked:
                continue

            # Simulate one step (without growth)
            simulated = deque(self.snake)
            simulated.appendleft(nxt)
            if nxt != self.food:
                simulated.pop()

            blocked = set(list(simulated)[:-1])
            space = self._flood_count(nxt, blocked)

            if space > best_space:
                best_space = space
                best_dir = d

        return best_dir

    def _bfs_path(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        if goal in blocked:
            return []

        q = deque([start])
        parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

        while q:
            cur = q.popleft()
            if cur == goal:
                break
            for nb in neighbors(cur):
                if nb in blocked or nb in parent:
                    continue
                parent[nb] = cur
                q.append(nb)

        if goal not in parent:
            return []

        rev: list[tuple[int, int]] = []
        cur = goal
        while cur != start:
            rev.append(cur)
            cur = parent[cur]  # type: ignore[assignment]
        rev.reverse()
        return rev

    def _flood_count(self, start: tuple[int, int], blocked: set[tuple[int, int]]) -> int:
        q = deque([start])
        seen = {start}
        while q:
            cur = q.popleft()
            for nb in neighbors(cur):
                if nb in blocked or nb in seen:
                    continue
                seen.add(nb)
                q.append(nb)
        return len(seen)

    def step(self) -> None:
        if not self.alive:
            return

        self.steps += 1
        self.direction = self.compute_next_move()
        new_head = add(self.snake[0], self.direction)

        # Collision checks
        if not in_bounds(new_head):
            self.alive = False
            return

        body_without_tail = set(list(self.snake)[:-1])
        if new_head in body_without_tail:
            self.alive = False
            return

        self.snake.appendleft(new_head)
        if new_head == self.food:
            self.score += 1
            self.food = self.spawn_food()
            if self.food == (-1, -1):
                # Board filled: treat as finished and restart
                self.alive = False
        else:
            self.snake.pop()

    def build_grid(self) -> list[list[str]]:
        """Return the current board state as a 2D array of single-character strings."""
        grid = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]

        for i, (x, y) in enumerate(self.snake):
            grid[y][x] = "@" if i == 0 else "o"

        if self.food != (-1, -1):
            fx, fy = self.food
            grid[fy][fx] = "*"

        return grid

    def render(self) -> str:
        grid = self.build_grid()

        top = "+" + "-" * WIDTH + "+"
        lines = [top]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append(top)
        lines.append(
            f"Round: {self.round_id}  Score: {self.score}  Length: {len(self.snake)}  Steps: {self.steps}"
        )
        if not self.alive:
            lines.append("Game over. Restarting...")
        return "\n".join(lines)


def main() -> None:
    random.seed()
    game = SnakeGame()

    # ANSI setup: clear screen and hide cursor
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25l")
    sys.stdout.flush()

    try:
        while True:
            game.step()
            sys.stdout.write("\x1b[H")
            sys.stdout.write(game.render())
            sys.stdout.write("\n")
            sys.stdout.flush()

            if game.alive:
                time.sleep(TICK_SECONDS)
            else:
                time.sleep(RESTART_DELAY_SECONDS)
                game.reset()
    except KeyboardInterrupt:
        pass
    finally:
        # Show cursor again and move to next line
        sys.stdout.write("\x1b[?25h\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
