from . import tmdb
from .models import Movie


def get_movie(tmdb_id):
    """Film iz lokalne baze, a ako ga nema, dohvati s TMDB-a i spremi."""
    movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
    if movie is None:
        movie = Movie.objects.create(**tmdb.fetch_movie(tmdb_id))
    return movie.to_dict()


def random_target():
    movie = Movie.objects.filter(is_target_pool=True).order_by("?").first()
    return movie.to_dict() if movie else None