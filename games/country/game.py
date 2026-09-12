import random
from datetime import datetime, timedelta, timezone

from games.core.base import GameError, GameMode
from games.core.registry import register_game

from . import geo
from .clues import CLUE_BY_KEY, CLUES, build_values
from .models import Country

START_POINTS = 1000
MAX_CLUES = 5
ROUND_SECONDS = 300          # 5 minuta
GRACE_SECONDS = 60           # produžetak nakon što netko prvi riješi
WRONG_PENALTIES = [50, 100, 200, 400]  # raste, dalje ostaje 400
FIRST_BONUS = 50
UNSOLVED_MULTIPLIER = 0.15


def _now():
    return datetime.now(timezone.utc)


def _iso(moment):
    return moment.isoformat()


def _parse(text):
    return datetime.fromisoformat(text)


@register_game
class CountryGame(GameMode):
    game_type = "country"
    name = "Country Detective"
    emoji = "🕵️"
    description = "Buy clues, find the country"
    client_script = "js/games/country.js"

    # --- Životni ciklus ---

    def create_state(self):
        country = Country.objects.filter(in_pool=True).order_by("?").first()
        if country is None:
            raise GameError("No countries yet. Run: python manage.py sync_countries")
        return {
            "country": {
                "code": country.code,
                "name": country.name,
                "latitude": country.latitude,
                "longitude": country.longitude,
            },
            "clue_values": build_values(country, random.Random()),
            "ends_at": _iso(_now() + timedelta(seconds=ROUND_SECONDS)),
            "first_solver": None,
            "players": {},
        }

    def is_solved(self, state):
        # "Solved" za lobby znači da je runda gotova.
        return self._is_over(state)

    def _is_over(self, state):
        return _now() >= _parse(state["ends_at"])

    def _entry(self, state, player):
        """Dohvati (ili stvori) zapis ovog igrača."""
        key = str(player["id"])
        entry = state["players"].get(key)
        if entry is None:
            entry = {
                "nickname": player["nickname"],
                "clues": [],
                "guesses": [],
                "solved": False,
                "solved_at": None,
            }
            state["players"][key] = entry
        entry["nickname"] = player["nickname"]
        return entry

    # --- Akcije ---

    def handle_action(self, state, action, player):
        kind = action.get("type")
        if kind == "sync":
            # Klijentov timer je istekao; samo izazovi ponovni broadcast.
            return state
        if self._is_over(state):
            raise GameError("The round is over.")

        entry = self._entry(state, player)
        if entry["solved"]:
            raise GameError("You already solved it.")

        if kind == "buy_clue":
            return self._buy(state, entry, action.get("clue"))
        if kind == "guess":
            return self._guess(state, entry, action.get("code"), player)
        raise GameError("Unknown action.")

    def _buy(self, state, entry, key):
        clue = CLUE_BY_KEY.get(key)
        if clue is None:
            raise GameError("Unknown clue.")
        if key in entry["clues"]:
            raise GameError("You already bought that clue.")
        if len(entry["clues"]) >= MAX_CLUES:
            raise GameError(f"You can only buy {MAX_CLUES} clues.")
        if self._points(entry) < clue["price"]:
            raise GameError("Not enough points.")
        entry["clues"].append(key)
        return state

    def _guess(self, state, entry, code, player):
        if not isinstance(code, str) or len(code) != 3:
            raise GameError("Invalid country.")
        code = code.upper()
        if any(guess["code"] == code for guess in entry["guesses"]):
            raise GameError("You already guessed that country.")

        guessed = Country.objects.filter(code=code).first()
        if guessed is None:
            raise GameError("Unknown country.")

        target = state["country"]
        correct = code == target["code"]
        result = {"code": code, "name": guessed.name, "correct": correct}
        if not correct:
            km = geo.distance_km(
                guessed.latitude, guessed.longitude, target["latitude"], target["longitude"]
            )
            result.update(
                distance=km,
                arrow=geo.arrow(
                    guessed.latitude, guessed.longitude,
                    target["latitude"], target["longitude"],
                ),
            )
        entry["guesses"].append(result)

        if correct:
            entry["solved"] = True
            entry["solved_at"] = _iso(_now())
            if state["first_solver"] is None:
                state["first_solver"] = str(player["id"])
                # Ostali dobiju još malo vremena, da im prvi ne prekine rundu.
                deadline = _now() + timedelta(seconds=GRACE_SECONDS)
                if deadline < _parse(state["ends_at"]):
                    state["ends_at"] = _iso(deadline)
        return state

    # --- Bodovi ---

    def _spent(self, entry):
        return sum(CLUE_BY_KEY[key]["price"] for key in entry["clues"])

    def _penalty(self, entry):
        wrong = sum(1 for guess in entry["guesses"] if not guess["correct"])
        return sum(
            WRONG_PENALTIES[min(index, len(WRONG_PENALTIES) - 1)] for index in range(wrong)
        )

    def _points(self, entry):
        """Bodovi koje igrač trenutno ima na raspolaganju."""
        return max(0, START_POINTS - self._spent(entry) - self._penalty(entry))

    def _score(self, state, key, entry):
        if entry["solved"]:
            score = self._points(entry)
            if state["first_solver"] == key:
                score += FIRST_BONUS
            return score
        if not entry["guesses"]:
            # Nije ni pokušao.
            return 0
        return int(self._points(entry) * UNSOLVED_MULTIPLIER)

    # --- Prikaz ---

    def get_public_state(self, state, viewer):
        over = self._is_over(state)
        key = str(viewer["id"])
        entry = state["players"].get(key)
        owned = set(entry["clues"]) if entry else []

        clues = [
            {
                **{field: clue[field] for field in ("key", "label", "emoji", "price")},
                # Vrijednost postoji SAMO ako ju je ovaj igrač kupio.
                "value": state["clue_values"][clue["key"]] if clue["key"] in owned else None,
            }
            for clue in CLUES
        ]

        public = {
            "ends_at": state["ends_at"],
            "finished": over,
            "max_clues": MAX_CLUES,
            "start_points": START_POINTS,
            "clues": clues,
            "me": {
                "points": self._points(entry) if entry else START_POINTS,
                "clues_used": len(entry["clues"]) if entry else 0,
                "guesses": entry["guesses"] if entry else [],
                "solved": bool(entry and entry["solved"]),
            },
            # Tijekom runde: samo koliko su drugi kupili, ne i ŠTO.
            "players": [
                {
                    "nickname": item["nickname"],
                    "clues_used": len(item["clues"]),
                    "guesses": len(item["guesses"]),
                    "solved": item["solved"],
                }
                for item in state["players"].values()
            ],
        }

        if over:
            public["answer"] = state["country"]["name"]
            public["results"] = sorted(
                (
                    {
                        "nickname": item["nickname"],
                        "score": self._score(state, player_key, item),
                        "solved": item["solved"],
                        "clues": item["clues"],  # tek sad otkrivamo tko je što kupio
                        "wrong": sum(1 for g in item["guesses"] if not g["correct"]),
                    }
                    for player_key, item in state["players"].items()
                ),
                key=lambda row: -row["score"],
            )
        return public