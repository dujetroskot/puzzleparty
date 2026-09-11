from django.db import models


class Room(models.Model):
    code = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Koja se igra trenutno igra ("movie", "crossword", "country") ili "" za lobby.
    game_type = models.CharField(max_length=32, blank=True)

    # PUNI state igre, uključujući tajne podatke (npr. target film).
    # Klijentu nikad ne šaljemo ovo direktno, nego samo get_public_state().
    game_state = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.code


class PlayerSession(models.Model):
    room = models.ForeignKey(Room, related_name="players", on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    nickname = models.CharField(max_length=24)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "session_key"], name="unique_player_per_room"
            )
        ]

    def __str__(self):
        return f"{self.nickname} @ {self.room.code}"