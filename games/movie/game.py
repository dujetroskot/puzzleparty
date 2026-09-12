from games.core.base import GameError, GameMode
from games.core.registry import register_game

from . import services, tmdb
from .comparison import compare_movies


@register_game
class MovieGame(GameMode):
    game_type = "movie"
    name = "Guess the Movie"
    emoji = "🎬"
    description = "Find the secret film"
    client_script = "js/games/movie.js"

    def create_state(self):
        target = services.random_target()
        if target is None:
            raise GameError("No movies yet. Run: python manage.py sync_movies")
        return {"target": target, "guesses": [], "solved": False, "revealed": False}

    def handle_action(self, state, action, player):
        if state["solved"] or state["revealed"]:
            raise GameError("This round is over. Start a new round.")
        kind = action.get("type")
        if kind == "guess":
            return self._guess(state, action.get("movie_id"), player)
        if kind == "reveal":
            state["revealed"] = True
            return state
        raise GameError("Unknown action.")

    def _guess(self, state, movie_id, player):
        # bool je u Pythonu podvrsta int-a, pa ga eksplicitno odbijamo.
        if not isinstance(movie_id, int) or isinstance(movie_id, bool) or movie_id <= 0:
            raise GameError("Invalid movie.")
        if any(guess["movie"]["id"] == movie_id for guess in state["guesses"]):
            raise GameError("That movie was already guessed.")

        try:
            movie = services.get_movie(movie_id)
        except tmdb.TMDBNotFound:
            raise GameError("Movie not found.")
        except tmdb.TMDBError:
            raise GameError("Couldn't reach TMDB. Try again.")

        feedback = compare_movies(movie, state["target"])
        feedback["movie"]["poster"] = tmdb.poster_url(movie["poster_path"], "w92")
        feedback["player"] = player["nickname"]
        state["guesses"].append(feedback)
        if feedback["correct"]:
            state["solved"] = True
        return state

    def is_solved(self, state):
        return state["solved"]

    def get_public_state(self, state, viewer):
        public = {
            "guesses": state["guesses"],
            "solved": state["solved"],
            "revealed": state["revealed"],
        }
        if state["solved"] or state["revealed"]:
            target = state["target"]
            public["answer"] = {
                "title": target["title"],
                "year": target["year"],
                "poster": tmdb.poster_url(target["poster_path"]),
            }
        return public