import requests
from django.conf import settings

API_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p"
CAST_LIMIT = 5
COUNTRY_SHORT_NAMES = {"United States of America": "USA", "United Kingdom": "UK"}


class TMDBError(Exception):
    """TMDB nije dostupan ili je vratio grešku."""


class TMDBNotFound(TMDBError):
    """Film s tim ID-em ne postoji."""


def _get(path, **params):
    token = settings.TMDB_READ_TOKEN
    if not token:
        raise TMDBError("TMDB_READ_TOKEN is not set in .env")
    try:
        response = requests.get(
            f"{API_URL}{path}",
            params={"language": "en-US", **params},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise TMDBError(f"TMDB request failed: {exc}") from exc
    if response.status_code == 404:
        raise TMDBNotFound(path)
    if not response.ok:
        raise TMDBError(f"TMDB returned {response.status_code}")
    return response.json()


def poster_url(path, size="w185"):
    # Slike su javne i ne trebaju token, pa ih browser smije učitati direktno.
    return f"{IMAGE_URL}/{size}{path}" if path else None


def _year(date_string):
    if date_string and date_string[:4].isdigit():
        return int(date_string[:4])
    return None


def search_movies(query, limit=8):
    data = _get("/search/movie", query=query, include_adult="false", page=1)
    return [
        {
            "id": item["id"],
            "title": item.get("title") or item.get("original_title", ""),
            "year": _year(item.get("release_date")),
            "poster": poster_url(item.get("poster_path"), "w92"),
        }
        for item in data.get("results", [])[:limit]
    ]


def fetch_movie(tmdb_id):
    # append_to_response=credits: detalji + glumci + ekipa u jednom pozivu.
    data = _get(f"/movie/{tmdb_id}", append_to_response="credits")
    credits = data.get("credits") or {}
    cast = sorted(credits.get("cast", []), key=lambda person: person.get("order", 999))
    directors = [p["name"] for p in credits.get("crew", []) if p.get("job") == "Director"]
    return {
        "tmdb_id": data["id"],
        "title": data.get("title") or data.get("original_title", ""),
        "year": _year(data.get("release_date")),
        "runtime": data.get("runtime") or None,
        "genres": [genre["name"] for genre in data.get("genres", [])],
        "directors": list(dict.fromkeys(directors)),  # makne duplikate, čuva redoslijed
        "cast": [person["name"] for person in cast[:CAST_LIMIT]],
        "countries": [
            COUNTRY_SHORT_NAMES.get(c["name"], c["name"])
            for c in data.get("production_countries", [])
        ],
        "original_language": data.get("original_language", ""),
        "poster_path": data.get("poster_path") or "",
        "vote_count": data.get("vote_count") or 0,
    }


def discover_well_known(page):
    data = _get(
        "/discover/movie",
        sort_by="vote_count.desc",
        include_adult="false",
        include_video="false",
        page=page,
    )
    return data.get("results", [])