#!/usr/bin/env python3
"""
Self-running ANSI Pac-Man simulation.

- Pac-Man (C) automatically navigates toward pellets.
- Ghosts (G) chase Pac-Man with simple pathfinding and slight randomness.
- The game restarts automatically after win/lose.

Controls: Ctrl+C to quit.
"""

from __future__ import annotations

import random
import sys
import time
from collections import deque


MAZE_RAW = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o..##................##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

HEIGHT = len(MAZE_RAW)
WIDTH = len(MAZE_RAW[0])

TICK_SECONDS = 0.1125  # 25% slower (0.09 * 1.25)
RESTART_DELAY_SECONDS = 1.3

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = (UP, DOWN, LEFT, RIGHT)


def add(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a[0] + b[0], a[1] + b[1]


def in_bounds(p: tuple[int, int]) -> bool:
    return 0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT


class PacmanGame:
    def __init__(self) -> None:
        self.round_id = 0
        self.reset()

    def reset(self) -> None:
        self.round_id += 1
        self.score = 0
        self.steps = 0
        self.alive = True
        self.won = False

        self.walls: set[tuple[int, int]] = set()
        self.pellets: set[tuple[int, int]] = set()
        self.power_pellets: set[tuple[int, int]] = set()
        self.ghost_house: set[tuple[int, int]] = set()

        for y, row in enumerate(MAZE_RAW):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == ".":
                    self.pellets.add((x, y))
                elif ch == "o":
                    self.power_pellets.add((x, y))
                elif ch in "- ":
                    self.ghost_house.add((x, y))

        self.pacman = (WIDTH // 2, HEIGHT - 4)
        if self.pacman in self.walls:
            self.pacman = self._first_walkable()

        center = (WIDTH // 2, HEIGHT // 2)
        self.ghosts = [
            center,
            (center[0] - 2, center[1]),
            (center[0] + 2, center[1]),
            (center[0], center[1] + 2),
        ]
        self.ghost_dirs = [LEFT, RIGHT, UP, DOWN]

        self.frightened_ticks = 0

        # Ensure spawn spots are clear from pellets.
        self.pellets.discard(self.pacman)
        self.power_pellets.discard(self.pacman)
        for g in self.ghosts:
            self.pellets.discard(g)
            self.power_pellets.discard(g)

    def _first_walkable(self) -> tuple[int, int]:
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self.is_walkable((x, y)):
                    return (x, y)
        return (1, 1)

    def is_walkable(self, p: tuple[int, int]) -> bool:
        return in_bounds(p) and p not in self.walls

    def neighbors(self, p: tuple[int, int]):
        for d in DIRS:
            q = add(p, d)
            # Horizontal tunnel wrap
            if q[0] < 0:
                q = (WIDTH - 1, q[1])
            elif q[0] >= WIDTH:
                q = (0, q[1])
            if self.is_walkable(q):
                yield q

    def bfs_next_step(
        self,
        start: tuple[int, int],
        goals: set[tuple[int, int]],
        avoid: set[tuple[int, int]] | None = None,
    ) -> tuple[int, int] | None:
        if not goals:
            return None

        blocked = avoid or set()
        q = deque([start])
        parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        found_goal: tuple[int, int] | None = None

        while q:
            cur = q.popleft()
            if cur in goals:
                found_goal = cur
                break
            for nb in self.neighbors(cur):
                if nb in blocked or nb in parent:
                    continue
                parent[nb] = cur
                q.append(nb)

        if found_goal is None:
            return None

        cur = found_goal
        while parent[cur] != start and parent[cur] is not None:
            cur = parent[cur]
        return cur if parent[cur] is not None else found_goal

    def choose_pacman_target(self) -> tuple[int, int] | None:
        ghost_positions = set(self.ghosts)
        pacman_avoid = ghost_positions | self.ghost_house

        if self.frightened_ticks > 0:
            # Hunt ghosts when frightened mode is active.
            return self.bfs_next_step(self.pacman, ghost_positions, avoid=self.ghost_house)

        pellet_goals = self.pellets | self.power_pellets
        if not pellet_goals:
            return None

        # Avoid moving directly into ghost tiles while collecting.
        return self.bfs_next_step(self.pacman, pellet_goals, avoid=pacman_avoid)

    def move_pacman(self) -> None:
        target_step = self.choose_pacman_target()
        if target_step is None:
            options = [q for q in self.neighbors(self.pacman) if q not in self.ghosts and q not in self.ghost_house]
            if not options:
                options = [q for q in self.neighbors(self.pacman) if q not in self.ghost_house]
            if not options:
                return
            target_step = random.choice(options)

        self.pacman = target_step

        if self.pacman in self.pellets:
            self.pellets.remove(self.pacman)
            self.score += 10
        elif self.pacman in self.power_pellets:
            self.power_pellets.remove(self.pacman)
            self.score += 50
            self.frightened_ticks = 45

    def move_ghost(self, idx: int) -> None:
        g = self.ghosts[idx]

        options = list(self.neighbors(g))
        if not options:
            return

        if self.frightened_ticks > 0:
            # Run away-ish: maximize Manhattan distance from Pac-Man.
            best = max(options, key=lambda p: abs(p[0] - self.pacman[0]) + abs(p[1] - self.pacman[1]))
            # Randomness so ghosts don't all lock step.
            nxt = best if random.random() < 0.75 else random.choice(options)
        else:
            # Chase Pac-Man using BFS with some randomness.
            step = self.bfs_next_step(g, {self.pacman})
            if step is not None and random.random() < 0.82:
                nxt = step
            else:
                nxt = random.choice(options)

        self.ghosts[idx] = nxt

    def resolve_collisions(self) -> None:
        for i, g in enumerate(self.ghosts):
            if g != self.pacman:
                continue
            if self.frightened_ticks > 0:
                # Eat ghost: send it back to center.
                self.score += 200
                self.ghosts[i] = (WIDTH // 2, HEIGHT // 2)
            else:
                self.alive = False

    def step(self) -> None:
        if not self.alive or self.won:
            return

        self.steps += 1
        self.move_pacman()
        self.resolve_collisions()
        if not self.alive:
            return

        for i in range(len(self.ghosts)):
            self.move_ghost(i)
            self.resolve_collisions()
            if not self.alive:
                return

        if self.frightened_ticks > 0:
            self.frightened_ticks -= 1

        if not self.pellets and not self.power_pellets:
            self.won = True

    def render(self) -> str:
        grid = [list(row) for row in MAZE_RAW]

        # Convert maze chars to draw layer.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                ch = grid[y][x]
                if ch == "#":
                    grid[y][x] = "█"
                else:
                    grid[y][x] = " "

        for x, y in self.pellets:
            grid[y][x] = "."
        for x, y in self.power_pellets:
            grid[y][x] = "o"

        for x, y in self.ghosts:
            if in_bounds((x, y)):
                grid[y][x] = "g" if self.frightened_ticks > 0 else "G"

        px, py = self.pacman
        if in_bounds((px, py)):
            grid[py][px] = "C"

        lines = ["".join(row) for row in grid]
        lines.append(
            f"Round: {self.round_id}  Score: {self.score}  Pellets: {len(self.pellets) + len(self.power_pellets)}  Steps: {self.steps}"
        )
        if self.frightened_ticks > 0:
            lines.append(f"Frightened mode: {self.frightened_ticks}")
        if not self.alive:
            lines.append("Pac-Man was caught. Restarting...")
        elif self.won:
            lines.append("Board cleared! Restarting...")
        return "\n".join(lines)


def main() -> None:
    random.seed()
    game = PacmanGame()

    # ANSI setup: clear + home + hide cursor.
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25l")
    sys.stdout.flush()

    try:
        while True:
            game.step()
            sys.stdout.write("\x1b[H")
            sys.stdout.write(game.render())
            sys.stdout.write("\n")
            sys.stdout.flush()

            if game.alive and not game.won:
                time.sleep(TICK_SECONDS)
            else:
                time.sleep(RESTART_DELAY_SECONDS)
                game.reset()
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[?25h\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
