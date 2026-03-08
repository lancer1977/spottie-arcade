def test_smoke_imports():
    # Ensure the core modules at least import (helps CI catch syntax/runtime errors early).
    import src.snake_selfplay  # noqa: F401
    import src.pacman_selfplay  # noqa: F401
    import src.digdug_selfplay  # noqa: F401


def test_smoke_true():
    assert True
