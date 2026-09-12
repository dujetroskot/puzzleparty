"""Dohvat podataka o državama iz javnih datasetova na GitHubu.

restcountries API je ugašen 2026. i v5 traži ključ, pa idemo na izvor:
mledoze/countries je isti dataset koji je restcountries posluživao.
Populacija dolazi zasebno jer je mledoze ne sadrži.
"""
import csv
import io

import requests

COUNTRIES_URL = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"
POPULATION_URL = "https://raw.githubusercontent.com/datasets/population/main/data/population.csv"


class SourceError(Exception):
    pass


def _download(url):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SourceError(f"Download failed: {url} ({exc})") from exc
    return response


def fetch_countries():
    data = _download(COUNTRIES_URL).json()
    if not isinstance(data, list):
        raise SourceError("Country dataset has an unexpected shape.")
    return {item["cca3"]: item for item in data if item.get("cca3")}


def fetch_populations():
    """{cca3: population} iz najnovije dostupne godine za svaku državu."""
    text = _download(POPULATION_URL).content.decode("utf-8")
    latest = {}
    for row in csv.DictReader(io.StringIO(text)):
        code, value = row.get("Country Code"), row.get("Value")
        if not code or not value:
            continue
        year = int(row["Year"])
        if code not in latest or year > latest[code][0]:
            latest[code] = (year, int(float(value)))
    return {code: population for code, (_year, population) in latest.items()}