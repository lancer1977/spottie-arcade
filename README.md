# Spottie ANSI Arcade

[![Tests](https://github.com/lancer1977/spottie-arcade/actions/workflows/tests.yml/badge.svg)](https://github.com/lancer1977/spottie-arcade/actions/workflows/tests.yml)

`cc-ansi-arcade` is a compact terminal project that runs three autonomous games with zero external UI framework dependencies.  
Everything renders in ANSI text, with lightweight game loops and algorithmic AI decisions per frame.

## Features

- Launch menu (`menu.py`) for quickly switching between simulations.
- Self-play Snake, Pac-Man, and Dig Dug variants in `src/`.
- Deterministic frame rendering through ANSI cursor control.
- Auto-reset after game end for continuous demonstrations.

## Repository structure

- `menu.py` — launcher entrypoint and process orchestration.
- `src/snake_selfplay.py` — autonomous snake simulation.
- `src/pacman_selfplay.py` — autonomous Pac-Man style simulation.
- `src/digdug_selfplay.py` — autonomous Dig Dug simulation.
- `LICENSE` — MIT licensing terms.

## How it works (high level)

Each game is built as a small autonomous loop:

1. Build internal state (board, entities, score, timers).
2. Compute AI move(s) for actors (player bots and enemies).
3. Advance simulation by one step.
4. Resolve collisions and win/lose conditions.
5. Render one ANSI text frame in-place and pause for frame timing.
6. Restart automatically when a round ends.

## Quick start

```bash
cd /home/lancer1977/code/cc-ansi-arcade
python3 menu.py
```

Menu options:

- `1` — Snake (self-running)
- `2` — Pac-Man (self-running)
- `3` — Dig Dug (self-running)
- `q` — Quit

You can also run any single simulation directly:

```bash
python3 src/snake_selfplay.py
python3 src/pacman_selfplay.py
python3 src/digdug_selfplay.py
```

Quit running games with `Ctrl+C`.

## Requirements

- Python 3.10+ (uses standard library only).
- Terminal with ANSI support (`\x1b[2J`, cursor hide/show sequences).

## Documentation references

Long-form notes, design decisions, and future improvements are documented in the vault:

- `/home/lancer1977/vaults/polyhydra/20_Projects/ansi-arcade/README.md`

## Game implementation notes

- **Snake**  
  Uses BFS for shortest-path movement toward food and flood-fill fallback for survivability.
- **Pac-Man**  
  Uses maze tile parsing, tunnel wrapping, ghost chase behavior, and frightened mode.
- **Dig Dug**  
  Uses BFS/digging behavior plus basic line-of-sight beam logic to model enemy pumping.

## Changelog notes

- Added structured launcher menu.
- Added autonomous gameplay loops for three classic-inspired games.
- Centralized documentation into repository README + vault notes.
