import random

from games.core.base import GameError, GameMode
from games.core.registry import register_game


@register_game
class SharedCounterGame(GameMode):
    game_type = "demo"
    name = "Shared Counter"
    emoji = "🧪"
    description = "Realtime test"
    client_script = "js/games/demo.js"

    def create_state(self):
        return {"count": 0, "last_player": None, "secret": random.randint(5, 15)}

    def handle_action(self, state, action, player):
        if action.get("type") != "increment":
            raise GameError("Unknown action.")
        if self.is_solved(state):
            raise GameError("Already solved. Start a new round.")
        state["count"] += 1
        state["last_player"] = player["nickname"]
        return state

    def is_solved(self, state):
        return state["count"] >= state["secret"]

    def get_public_state(self, state, viewer):
        public = {"count": state["count"], "last_player": state["last_player"]}
        if self.is_solved(state):
            public["secret"] = state["secret"]
        return public