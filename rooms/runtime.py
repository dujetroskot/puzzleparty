"""Stanje koje živi samo u memoriji ovog procesa.

Radi dok server ima jedan proces (runserver, jednostavan deploy).
Za više procesa ovo se seli u Redis.
"""
import asyncio
from collections import defaultdict

_connections = defaultdict(dict)   # room_code -> {channel_name: player_id}
_locks = defaultdict(asyncio.Lock)  # room_code -> Lock


def add_connection(code, channel_name, player_id):
    _connections[code][channel_name] = player_id


def remove_connection(code, channel_name):
    _connections[code].pop(channel_name, None)
    if not _connections[code]:
        del _connections[code]


def online_player_ids(code):
    # set() jer isti igrač može imati otvorena dva taba.
    return set(_connections.get(code, {}).values())


def room_lock(code):
    return _locks[code]