import random
from datetime import datetime, timedelta, timezone

from games.core.base import GameError, GameMode
from games.core.registry import register_game

from .pairs import PAIRS

ROUND_CHOICES = [1, 3, 5]
DEFAULT_ROUNDS = 3
GUESS_SECONDS = 60
MAX_CLUE_LENGTH = 40

# (najveća udaljenost od mete, bodovi)
SCORE_BANDS = [(0, 200), (3, 100), (10, 75), (20, 50), (30, 25), (50, 5)]

# Meta nikad skroz uz rub, da trag uvijek bude smislen.
TARGET_MIN, TARGET_MAX = 0, 100

SETUP, CLUE, GUESS, REVEAL, FINISHED = "setup", "clue", "guess", "reveal", "finished"


def _now():
    return datetime.now(timezone.utc)


def _iso(moment):
    return moment.isoformat()


def _parse(text):
    return datetime.fromisoformat(text)


def score_for(distance):
    for limit, points in SCORE_BANDS:
        if distance <= limit:
            return points
    return 0


@register_game
class WavelengthGame(GameMode):
    game_type = "wavelength"
    name = "Wavelength"
    emoji = "📡"
    description = "One word, one scale"
    client_script = "js/games/wavelength.js"

    # --- Životni ciklus ---

    def create_state(self):
        # Partija počinje izborom broja rundi, još ne znamo tko igra.
        return {
            "phase": SETUP,
            "rounds": DEFAULT_ROUNDS,
            "order": [],          # id-evi igrača, redoslijed davatelja
            "names": {},          # id -> nickname
            "turn": 0,            # koja podrunda po redu
            "totals": {},         # id -> ukupni bodovi
            "used_pairs": [],
            "sub": None,          # trenutna podrunda
        }

    def is_solved(self, state):
        return state["phase"] == FINISHED

    # --- Pomoćno ---

    def _remember(self, state, player):
        state["names"][str(player["id"])] = player["nickname"]

    def _giver(self, state):
        if not state["order"]:
            return None
        return state["order"][state["turn"] % len(state["order"])]

    def _total_turns(self, state):
        return state["rounds"] * len(state["order"])

    def _pick_pair(self, state, rng):
        available = [pair for pair in PAIRS if list(pair) not in state["used_pairs"]]
        if not available:
            state["used_pairs"] = []
            available = PAIRS
        pair = rng.choice(available)
        state["used_pairs"].append(list(pair))
        return pair

    def _start_turn(self, state):
        rng = random.Random()
        left, right = self._pick_pair(state, rng)
        state["phase"] = CLUE
        state["sub"] = {
            "pair": [left, right],
            "target": rng.randint(TARGET_MIN, TARGET_MAX),
            "giver": self._giver(state),
            "clue": "",
            "ends_at": None,
            "guesses": {},   # id -> {"value": int, "locked": bool}
            "scores": {},    # id -> bodovi, puni se u reveal fazi
        }

    # --- Akcije ---

    def handle_action(self, state, action, player):
        self._remember(state, player)
        kind = action.get("type")

        if kind == "sync":
            return self._maybe_close(state)
        if kind == "set_rounds":
            return self._set_rounds(state, action.get("rounds"))
        if kind == "start":
            return self._start_game(state)
        if kind == "submit_clue":
            return self._submit_clue(state, action.get("clue"), player)
        if kind == "move":
            return self._move(state, action.get("value"), player, lock=False)
        if kind == "lock":
            return self._move(state, action.get("value"), player, lock=True)
        if kind == "next":
            return self._next_turn(state)
        if kind == "restart":
            return self._restart(state)
        raise GameError("Unknown action.")

    def _set_rounds(self, state, rounds):
        if state["phase"] != SETUP:
            raise GameError("The game already started.")
        if rounds not in ROUND_CHOICES:
            raise GameError("Invalid number of rounds.")
        state["rounds"] = rounds
        return state

    def _start_game(self, state):
        if state["phase"] != SETUP:
            raise GameError("The game already started.")
        if len(state["names"]) < 2:
            raise GameError("You need at least 2 players.")
        # Redoslijed se fiksira sad i ne mijenja se do kraja partije.
        state["order"] = sorted(state["names"], key=lambda key: state["names"][key].lower())
        state["totals"] = {key: 0 for key in state["order"]}
        state["turn"] = 0
        self._start_turn(state)
        return state

    def _submit_clue(self, state, clue, player):
        if state["phase"] != CLUE:
            raise GameError("Not the right time for a clue.")
        if str(player["id"]) != state["sub"]["giver"]:
            raise GameError("You are not giving the clue.")
        clue = (clue or "").strip()[:MAX_CLUE_LENGTH]
        if not clue:
            raise GameError("Write a clue first.")
        state["sub"]["clue"] = clue
        state["sub"]["ends_at"] = _iso(_now() + timedelta(seconds=GUESS_SECONDS))
        state["phase"] = GUESS
        return state

    def _move(self, state, value, player, lock):
        if state["phase"] != GUESS:
            raise GameError("Not guessing right now.")
        key = str(player["id"])
        if key == state["sub"]["giver"]:
            raise GameError("You gave the clue, you can't guess.")
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
            raise GameError("Invalid position.")

        entry = state["sub"]["guesses"].get(key)
        if entry and entry["locked"]:
            raise GameError("You already locked in.")
        state["sub"]["guesses"][key] = {"value": value, "locked": lock}
        return self._maybe_close(state)

    def _maybe_close(self, state):
        """Završi fazu pogađanja ako su svi zaključali ili je vrijeme isteklo."""
        if state["phase"] != GUESS:
            return state

        sub = state["sub"]
        guessers = [key for key in state["order"] if key != sub["giver"]]
        everyone_locked = all(
            sub["guesses"].get(key, {}).get("locked") for key in guessers
        )
        expired = sub["ends_at"] and _now() >= _parse(sub["ends_at"])
        if not (everyone_locked or expired):
            return state

        # Tko nije zaključao, računa mu se zadnja pozicija klizača.
        total = 0
        for key in guessers:
            value = sub["guesses"].get(key, {}).get("value", 50)
            sub["guesses"][key] = {"value": value, "locked": True}
            points = score_for(abs(value - sub["target"]))
            sub["scores"][key] = points
            state["totals"][key] = state["totals"].get(key, 0) + points
            total += points

        # Davatelj dobiva prosjek onoga što su njegovi pogađači postigli.
        giver_points = round(total / len(guessers)) if guessers else 0
        sub["scores"][sub["giver"]] = giver_points
        state["totals"][sub["giver"]] = state["totals"].get(sub["giver"], 0) + giver_points

        state["phase"] = REVEAL
        return state

    def _next_turn(self, state):
        if state["phase"] != REVEAL:
            raise GameError("The round isn't over yet.")
        state["turn"] += 1
        if state["turn"] >= self._total_turns(state):
            state["phase"] = FINISHED
            state["sub"] = None
        else:
            self._start_turn(state)
        return state

    def _restart(self, state):
        if state["phase"] != FINISHED:
            raise GameError("The game isn't over yet.")
        fresh = self.create_state()
        fresh["names"] = state["names"]
        fresh["rounds"] = state["rounds"]
        return fresh

    # --- Prikaz ---

    def _scoreboard(self, state):
        return sorted(
            (
                {
                    "id": key,
                    "nickname": state["names"].get(key, "?"),
                    "total": state["totals"].get(key, 0),
                }
                for key in state["order"]
            ),
            key=lambda row: -row["total"],
        )

    def get_public_state(self, state, viewer):
        key = str(viewer["id"])
        public = {
            "phase": state["phase"],
            "rounds": state["rounds"],
            "round_choices": ROUND_CHOICES,
            "turn": state["turn"] + 1,
            "total_turns": self._total_turns(state),
            "scoreboard": self._scoreboard(state),
        }

        if state["phase"] == SETUP:
            public["players"] = sorted(state["names"].values(), key=str.lower)
            return public

        if state["phase"] == FINISHED:
            return public

        sub = state["sub"]
        is_giver = key == sub["giver"]
        public["sub"] = {
            "pair": sub["pair"],
            "giver": state["names"].get(sub["giver"], "?"),
            "is_giver": is_giver,
            "clue": sub["clue"],
            "ends_at": sub["ends_at"],
            # Metu vidi samo davatelj, i to tek nakon što svi vide rezultat.
            "target": sub["target"] if (is_giver or state["phase"] == REVEAL) else None,
            "my_guess": sub["guesses"].get(key),
            "locked_count": sum(1 for item in sub["guesses"].values() if item["locked"]),
            "guesser_count": max(0, len(state["order"]) - 1),
        }

        if state["phase"] == REVEAL:
            # Tek sad se otkriva tko je gdje stavio klizač.
            public["sub"]["results"] = sorted(
                (
                    {
                        "nickname": state["names"].get(player_key, "?"),
                        "value": sub["guesses"].get(player_key, {}).get("value"),
                        "points": sub["scores"].get(player_key, 0),
                        "is_giver": player_key == sub["giver"],
                    }
                    for player_key in state["order"]
                ),
                key=lambda row: -row["points"],
            )
        return public