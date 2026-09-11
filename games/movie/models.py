from django.db import models


class Movie(models.Model):
    tmdb_id = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=255)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    runtime = models.PositiveSmallIntegerField(null=True, blank=True)
    genres = models.JSONField(default=list)
    directors = models.JSONField(default=list)
    cast = models.JSONField(default=list)        # top 5 prema TMDB redoslijedu
    countries = models.JSONField(default=list)
    original_language = models.CharField(max_length=8, blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    vote_count = models.PositiveIntegerField(default=0)

    # True = dovoljno poznat da ga igra smije odabrati kao tajni film.
    is_target_pool = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Polja koja igra koristi. Sve ostalo je interno za cache.
    GAME_FIELDS = (
        "tmdb_id", "title", "year", "runtime", "genres", "directors",
        "cast", "countries", "original_language", "poster_path",
    )

    def to_dict(self):
        return {name: getattr(self, name) for name in self.GAME_FIELDS}

    def __str__(self):
        return f"{self.title} ({self.year})"