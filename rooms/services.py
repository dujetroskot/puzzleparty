import secrets

from django.db import IntegrityError

from .models import PlayerSession, Room

# Bez I i O da se ne miješaju s 1 i 0 kad netko diktira kod.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 4


def generate_room_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(raw):
    return raw.strip().upper()


def create_room():
    # Ako slučajno pogodimo postojeći kod, unique constraint baci
    # IntegrityError i jednostavno probamo drugi.
    for _ in range(10):
        try:
            return Room.objects.create(code=generate_room_code())
        except IntegrityError:
            continue
    raise RuntimeError("Could not generate a unique room code.")


def join_room(room, session_key, nickname):
    player, _ = PlayerSession.objects.update_or_create(
        room=room,
        session_key=session_key,
        defaults={"nickname": nickname},
    )
    return player