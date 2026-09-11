from .base import GameMode

_registry = {}


def register_game(cls):
    if not issubclass(cls, GameMode):
        raise TypeError(f"{cls.__name__} must inherit from GameMode.")
    if not cls.game_type:
        raise ValueError(f"{cls.__name__} must define game_type.")
    if cls.game_type in _registry:
        raise ValueError(f"Game type '{cls.game_type}' is already registered.")
    _registry[cls.game_type] = cls()
    return cls


def get_game(game_type):
    return _registry.get(game_type)


def all_games():
    return list(_registry.values())