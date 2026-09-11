from django.contrib import admin

from .models import PlayerSession, Room


class PlayerInline(admin.TabularInline):
    model = PlayerSession
    extra = 0


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("code", "game_type", "created_at")
    inlines = [PlayerInline]