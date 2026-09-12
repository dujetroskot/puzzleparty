"""Definicije tragova: cijena, oznaka i kako se vrijednost izračuna.

Vrijednosti se izračunaju JEDNOM pri kreiranju runde i spreme u privatni
state. Tako "susjedna država" ostaje ista kroz cijelu rundu.
"""
import random

CLUES = [
    {"key": "continent", "label": "Continent", "emoji": "🌍", "price": 100},
    {"key": "population", "label": "Population", "emoji": "👥", "price": 100},
    {"key": "area", "label": "Area", "emoji": "📐", "price": 100},
    {"key": "neighbour_count", "label": "Number of neighbours", "emoji": "🧭", "price": 150},
    {"key": "currency", "label": "Currency", "emoji": "💰", "price": 150},
    {"key": "language", "label": "Language", "emoji": "🗣", "price": 250},
    {"key": "neighbour", "label": "A neighbouring country", "emoji": "🤝", "price": 250},
    {"key": "capital", "label": "Capital city", "emoji": "🏙", "price": 350},
]

CLUE_BY_KEY = {clue["key"]: clue for clue in CLUES}


def _round_number(value):
    """1 značajna decimala, da trag ne bude gotov Google upit."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} million".replace(".0 ", " ")
    if value >= 1_000:
        return f"{value / 1_000:.0f} thousand"
    return str(int(value))


def build_values(country, rng=None):
    """Izračunaj tekst svakog traga za zadanu državu."""
    rng = rng or random.Random()
    neighbours = country.neighbour_names()
    return {
        "continent": country.continent or "Unknown",
        "population": f"about {_round_number(country.population)} people",
        "area": f"about {_round_number(country.area)} km²",
        "neighbour_count": (
            f"{len(neighbours)} land neighbour{'s' if len(neighbours) != 1 else ''}"
        ),
        "currency": ", ".join(country.currencies) or "Unknown",
        "language": ", ".join(country.languages) or "Unknown",
        # Nasumičan susjed, ali odabran jednom za cijelu rundu.
        "neighbour": rng.choice(neighbours) if neighbours else "No land neighbours",
        "capital": country.capital or "Unknown",
    }