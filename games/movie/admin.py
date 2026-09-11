from django.contrib import admin

from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "vote_count", "is_target_pool")
    list_filter = ("is_target_pool",)
    search_fields = ("title",)