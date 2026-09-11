"""Deterministička pravila usporedbe. Nema baze, mreže ni AI-ja.

Strelica ("hint") pokazuje gdje je TARGET u odnosu na pokušaj:
"down" = target je stariji / kraći, "up" = target je noviji / duži.
"""

YEAR_CLOSE = 2      # ± godina za žuto
RUNTIME_CLOSE = 10  # ± minuta za žuto


def _compare_number(guess, target, close):
    if guess is None or target is None:
        return {"value": guess, "status": "unknown", "hint": None}
    if guess == target:
        return {"value": guess, "status": "correct", "hint": None}
    return {
        "value": guess,
        "status": "close" if abs(guess - target) <= close else "wrong",
        "hint": "up" if target > guess else "down",
    }


def _compare_list(guess_values, target_values):
    target_set = set(target_values)
    items = [{"value": value, "match": value in target_set} for value in guess_values]
    if guess_values and set(guess_values) == target_set:
        status = "correct"
    elif any(item["match"] for item in items):
        status = "partial"
    else:
        status = "wrong"
    return {"status": status, "items": items}


def compare_movies(guess, target):
    same_language = guess["original_language"] == target["original_language"]
    return {
        "movie": {"id": guess["tmdb_id"], "title": guess["title"]},
        "correct": guess["tmdb_id"] == target["tmdb_id"],
        "year": _compare_number(guess["year"], target["year"], YEAR_CLOSE),
        "runtime": _compare_number(guess["runtime"], target["runtime"], RUNTIME_CLOSE),
        "genres": _compare_list(guess["genres"], target["genres"]),
        "directors": _compare_list(guess["directors"], target["directors"]),
        "cast": _compare_list(guess["cast"], target["cast"]),
        "countries": _compare_list(guess["countries"], target["countries"]),
        "language": {
            "value": guess["original_language"].upper(),
            "status": "correct" if same_language else "wrong",
        },
    }