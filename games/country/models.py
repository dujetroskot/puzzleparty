from django.db import models


class Country(models.Model):
    # ISO 3166-1 alpha-3, npr. "HRV". Koristimo ga kao stabilan identifikator.
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100, db_index=True)
    official_name = models.CharField(max_length=200, blank=True)

    continent = models.CharField(max_length=40, blank=True)
    subregion = models.CharField(max_length=60, blank=True)
    capital = models.CharField(max_length=100, blank=True)
    population = models.BigIntegerField(default=0)
    area = models.FloatField(default=0)  # km²

    borders = models.JSONField(default=list)     # lista cca3 kodova susjeda
    currencies = models.JSONField(default=list)  # nazivi valuta
    languages = models.JSONField(default=list)

    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    landlocked = models.BooleanField(default=False)

    # SVG path silueta. Puni se kasnije, igra radi i bez toga.
    shape_path = models.TextField(blank=True)

    # True = igra ovu državu smije odabrati kao misterij.
    in_pool = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def neighbour_names(self):
        if not self.borders:
            return []
        found = Country.objects.filter(code__in=self.borders).values_list("name", flat=True)
        return sorted(found)

    def __str__(self):
        return self.name