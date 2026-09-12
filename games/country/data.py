"""Države koje NE želimo kao misterij, iako su suverene i članice UN-a.

Pool se inače određuje automatski: independent + unMember iz restcountries.
Sve države i dalje ulaze u bazu radi autocompletea; ovo je samo izbor misterija.
"""

EXCLUDE_CODES = {
    "VAT",  # Vatikan: nema podatka o populaciji i premalen za smislene tragove
}