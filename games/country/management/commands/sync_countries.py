from django.core.management.base import BaseCommand

from games.country.data import EXCLUDE_CODES
from games.country.models import Country
from games.country.sources import SourceError, fetch_countries, fetch_populations


def parse(item, population):
    name = item.get("name") or {}
    latlng = item.get("latlng") or [0, 0]
    capitals = item.get("capital") or []
    currencies = item.get("currencies") or {}
    languages = item.get("languages") or {}
    return {
        "name": name.get("common", ""),
        "official_name": name.get("official", ""),
        "continent": item.get("region") or "",
        "subregion": item.get("subregion") or "",
        "capital": capitals[0] if capitals else "",
        "population": population,
        "area": item.get("area") or 0,
        "borders": item.get("borders") or [],
        "currencies": sorted(
            value.get("name", "") for value in currencies.values() if value.get("name")
        ),
        "languages": sorted(languages.values()),
        "latitude": latlng[0] if len(latlng) > 0 else 0,
        "longitude": latlng[1] if len(latlng) > 1 else 0,
        "landlocked": bool(item.get("landlocked")),
    }


def is_sovereign(item):
    # independent = nije tuđi teritorij, unMember = priznata država.
    # Zajedno izbacuju Grenland, Portoriko, Hong Kong, Novu Kaledoniju...
    return bool(item.get("independent")) and bool(item.get("unMember"))


class Command(BaseCommand):
    help = "Import country data from public datasets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-population",
            type=int,
            default=0,
            help="Keep only countries above this population in the game pool.",
        )

    def handle(self, *args, min_population, **options):
        self.stdout.write("Downloading datasets...")
        try:
            countries = fetch_countries()
            populations = fetch_populations()
        except SourceError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        saved = 0
        for code, item in countries.items():
            data = parse(item, populations.get(code, 0))
            if not data["name"]:
                continue
            in_pool = (
                is_sovereign(item)
                and code not in EXCLUDE_CODES
                and data["population"] >= max(min_population, 1)
            )
            Country.objects.update_or_create(code=code, defaults={**data, "in_pool": in_pool})
            saved += 1

        in_pool_count = Country.objects.filter(in_pool=True).count()
        self.stdout.write(
            self.style.SUCCESS(f"{saved} countries saved, {in_pool_count} in pool.")
        )