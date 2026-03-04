#!/usr/bin/env python3
"""
Self-running ANSI Dig Dug-style clone.

- Dig Dug (D) auto-digs through dirt.
- Enemies (E) chase Dig Dug.
- Dig Dug auto-pumps enemies in line of sight.
- Game restarts automatically on win/lose.

Controls: Ctrl+C to quit.
"""

from __future__ import annotations

import random
import sys
import time
from collections import deque


WIDTH = 30
HEIGHT = 18

TICK_SECONDS = 0.1125  # 25% slower (0.09 * 1.25)
RESTART_DELAY_SECONDS = 1.2

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = (UP, DOWN, LEFT, RIGHT)


def add(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a[0] + b[0], a[1] + b[1]


def in_bounds(p: tuple[int, int]) -> bool:
    return 0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT


class DigDugGame:
    def __init__(self) -> None:
        self.round_id = 0
        self.reset()

    def reset(self) -> None:
        self.round_id += 1
        self.alive = True
        self.won = False
        self.steps = 0
        self.score = 0

        self.walls: set[tuple[int, int]] = set()
        for x in range(WIDTH):
            self.walls.add((x, 0))
            self.walls.add((x, HEIGHT - 1))
        for y in range(HEIGHT):
            self.walls.add((0, y))
            self.walls.add((WIDTH - 1, y))

        self.rocks: set[tuple[int, int]] = set()
        for _ in range(10):
            p = (random.randint(2, WIDTH - 3), random.randint(2, HEIGHT - 3))
            self.rocks.add(p)

        self.dirt: set[tuple[int, int]] = {
            (x, y)
            for y in range(1, HEIGHT - 1)
            for x in range(1, WIDTH - 1)
            if (x, y) not in self.rocks
        }

        self.player = (WIDTH // 2, HEIGHT - 3)
        self.facing = UP
        self.last_beam: list[tuple[int, int]] = []

        self.enemies: list[tuple[int, int]] = []
        while len(self.enemies) < 4:
            p = (random.randint(2, WIDTH - 3), random.randint(2, 5))
            if p != self.player and p not in self.rocks and p not in self.enemies:
                self.enemies.append(p)

        self.enemy_pump: dict[int, int] = {i: 0 for i in range(len(self.enemies))}

        # Clear spawn tunnel around player
        for p in [self.player, add(self.player, LEFT), add(self.player, RIGHT), add(self.player, UP)]:
            self.dirt.discard(p)

    def is_walkable(self, p: tuple[int, int]) -> bool:
        return in_bounds(p) and p not in self.walls and p not in self.rocks

    def neighbors(self, p: tuple[int, int]):
        for d in DIRS:
            q = add(p, d)
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

    def line_of_sight_enemy(self) -> tuple[int, tuple[int, int], list[tuple[int, int]]] | None:
        """Return (enemy_index, direction, beam_cells) if an enemy is pumpable."""
        for d in (self.facing, UP, DOWN, LEFT, RIGHT):
            beam: list[tuple[int, int]] = []
            cur = self.player
            for _ in range(6):
                cur = add(cur, d)
                if not self.is_walkable(cur):
                    break
                beam.append(cur)
                for i, e in enumerate(self.enemies):
                    if e == cur:
                        return i, d, beam
        return None

    def pump_if_possible(self) -> bool:
        hit = self.line_of_sight_enemy()
        if hit is None:
            self.last_beam = []
            return False

        idx, d, beam = hit
        self.facing = d
        self.last_beam = beam
        self.enemy_pump[idx] = self.enemy_pump.get(idx, 0) + 1
        if self.enemy_pump[idx] >= 2:
            self.score += 200
            self.enemies.pop(idx)
            # Rebuild pump dictionary to match shifted indexes.
            self.enemy_pump = {i: self.enemy_pump.get(i if i < idx else i + 1, 0) for i in range(len(self.enemies))}
        return True

    def choose_player_step(self) -> tuple[int, int] | None:
        enemy_positions = set(self.enemies)

        # Prioritize nearby dirt to keep digging action active.
        if self.dirt:
            step = self.bfs_next_step(self.player, self.dirt, avoid=enemy_positions)
            if step is not None:
                return step

        # If no safe dirt path, move away from closest enemy.
        options = [q for q in self.neighbors(self.player) if q not in enemy_positions]
        if not options:
            options = list(self.neighbors(self.player))
        if not options:
            return None

        return max(options, key=lambda p: min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in self.enemies) if self.enemies else 0)

    def move_player(self) -> None:
        if self.pump_if_possible():
            return

        self.last_beam = []
        step = self.choose_player_step()
        if step is None:
            return

        dx = step[0] - self.player[0]
        dy = step[1] - self.player[1]
        self.facing = (dx, dy)

        self.player = step
        if self.player in self.dirt:
            self.dirt.remove(self.player)
            self.score += 5

    def move_enemies(self) -> None:
        if not self.enemies:
            return

        new_positions: list[tuple[int, int]] = []
        taken = set(self.rocks)

        for i, e in enumerate(self.enemies):
            options = [q for q in self.neighbors(e) if q not in taken]
            if not options:
                new_positions.append(e)
                taken.add(e)
                continue

            if random.random() < 0.78:
                nxt = min(options, key=lambda p: abs(p[0] - self.player[0]) + abs(p[1] - self.player[1]))
            else:
                nxt = random.choice(options)

            new_positions.append(nxt)
            taken.add(nxt)
            # Pump pressure decays while enemy keeps moving.
            self.enemy_pump[i] = max(0, self.enemy_pump.get(i, 0) - 1)

        self.enemies = new_positions

    def resolve_collisions(self) -> None:
        if any(e == self.player for e in self.enemies):
            self.alive = False

    def step(self) -> None:
        if not self.alive or self.won:
            return

        self.steps += 1
        self.move_player()
        self.resolve_collisions()
        if not self.alive:
            return

        self.move_enemies()
        self.resolve_collisions()
        if not self.alive:
            return

        if not self.enemies:
            self.won = True

    def render(self) -> str:
        grid = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]

        for x, y in self.walls:
            grid[y][x] = "█"
        for x, y in self.dirt:
            grid[y][x] = "·"
        for x, y in self.rocks:
            grid[y][x] = "O"
        for x, y in self.last_beam:
            if in_bounds((x, y)) and (x, y) not in self.walls and (x, y) not in self.rocks:
                grid[y][x] = "*"
        for x, y in self.enemies:
            grid[y][x] = "E"

        px, py = self.player
        grid[py][px] = "D"

        lines = ["".join(row) for row in grid]
        lines.append(
            f"Round: {self.round_id}  Score: {self.score}  Enemies: {len(self.enemies)}  Dirt: {len(self.dirt)}  Steps: {self.steps}"
        )
        if not self.alive:
            lines.append("Dig Dug got caught. Restarting...")
        elif self.won:
            lines.append("All enemies popped! Restarting...")
        return "\n".join(lines)


def main() -> None:
    random.seed()
    game = DigDugGame()

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
