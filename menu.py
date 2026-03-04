#!/usr/bin/env python3
"""Root launcher menu for spottie-arcade games."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

GAMES = {
    "1": ("Snake (self-running)", SRC / "snake_selfplay.py"),
    "2": ("Pac-Man (self-running)", SRC / "pacman_selfplay.py"),
    "3": ("Dig Dug (self-running)", SRC / "digdug_selfplay.py"),
}


def clear_screen() -> None:
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def run_game(path: Path) -> None:
    if not path.exists():
        print(f"\nGame file not found: {path}")
        input("Press Enter to continue...")
        return

    print(f"\nLaunching: {path.name}")
    print("Use Ctrl+C in the game window to stop and return to this menu.\n")
    subprocess.run([sys.executable, str(path)], check=False)
    input("\nGame exited. Press Enter to return to menu...")


def main() -> None:
    while True:
        clear_screen()
        print("=== Spottie Arcade ===")
        for key, (name, _) in GAMES.items():
            print(f"{key}. {name}")
        print("q. Quit")

        choice = input("\nChoose a game: ").strip().lower()

        if choice == "q":
            print("Goodbye.")
            return

        selected = GAMES.get(choice)
        if selected is None:
            print("\nInvalid choice.")
            input("Press Enter to try again...")
            continue

        _, path = selected
        run_game(path)


if __name__ == "__main__":
    main()
