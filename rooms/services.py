import secrets
from django.db import IntegrityError, transaction

from games.core.base import GameError
from games.core.registry import get_game

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

def get_player(code, session_key):
    """Vrati {"id", "nickname"} ili None ako ovaj browser nije u sobi."""
    if not session_key:
        return None
    player = PlayerSession.objects.filter(
        room__code=code, session_key=session_key
    ).first()
    if player is None:
        return None
    return {"id": player.pk, "nickname": player.nickname}


def _locked_room(code):
    # Na SQLiteu select_for_update ne radi ništa, ali na PostgreSQLu
    # zaključa redak. Kod ostaje isti kad promijenimo bazu.
    return Room.objects.select_for_update().get(code=code)


def start_game(code, game_type):
    game = get_game(game_type)
    if game is None:
        raise GameError("Unknown game.")
    with transaction.atomic():
        room = _locked_room(code)
        room.game_type = game.game_type
        room.game_state = game.create_state()
        room.save(update_fields=["game_type", "game_state", "updated_at"])


def end_game(code):
    with transaction.atomic():
        room = _locked_room(code)
        room.game_type = ""
        room.game_state = {}
        room.save(update_fields=["game_type", "game_state", "updated_at"])


def apply_action(code, player, action):
    with transaction.atomic():
        room = _locked_room(code)
        game = get_game(room.game_type)
        if game is None:
            raise GameError("No game is running.")
        room.game_state = game.handle_action(room.game_state, action, player)
        room.save(update_fields=["game_state", "updated_at"])


def build_room_payload(code, online_player_ids, viewer):
    """Sve što JEDAN igrač vidi o sobi. Nikad ne vraća puni game_state."""
    room = Room.objects.get(code=code)
    players = room.players.filter(pk__in=online_player_ids).order_by("joined_at")

    game_payload = None
    game = get_game(room.game_type)
    if game is not None:
        game_payload = {
            "type": game.game_type,
            "name": game.name,
            "emoji": game.emoji,
            "solved": game.is_solved(room.game_state),
            "state": game.get_public_state(room.game_state, viewer),
        }

    return {
        "code": room.code,
        "players": [{"id": p.pk, "nickname": p.nickname} for p in players],
        "game": game_payload,
    }