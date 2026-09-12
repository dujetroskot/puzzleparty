from django.contrib import admin

from .models import Country


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "continent", "capital", "population", "in_pool")
    list_filter = ("continent", "in_pool")
    search_fields = ("name", "code")