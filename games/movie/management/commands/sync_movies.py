from django.core.management.base import BaseCommand

from games.movie import tmdb
from games.movie.models import Movie


class Command(BaseCommand):
    help = "Download well-known movies from TMDB into the local target pool."

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=10, help="20 movies per page")

    def handle(self, *args, pages, **options):
        added = 0
        for page in range(1, pages + 1):
            for item in tmdb.discover_well_known(page):
                try:
                    data = tmdb.fetch_movie(item["id"])
                except tmdb.TMDBError as exc:
                    self.stderr.write(f"Skipping {item['id']}: {exc}")
                    continue

                # Film bez ovih podataka bio bi loš target.
                if not all([data["year"], data["runtime"], data["directors"], data["cast"]]):
                    continue

                tmdb_id = data.pop("tmdb_id")
                Movie.objects.update_or_create(
                    tmdb_id=tmdb_id, defaults={**data, "is_target_pool": True}
                )
                added += 1
            self.stdout.write(f"Page {page}/{pages} done")

        self.stdout.write(self.style.SUCCESS(f"{added} movies in target pool."))