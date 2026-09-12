from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from games.core.base import GameError

from . import runtime, services

# Consumer je async, a Django ORM je sync. Ovi omotači pokreću
# DB funkcije u zasebnom threadu da ne blokiraju server.
get_player = database_sync_to_async(services.get_player)
start_game = database_sync_to_async(services.start_game)
end_game = database_sync_to_async(services.end_game)
apply_action = database_sync_to_async(services.apply_action)
build_room_payload = database_sync_to_async(services.build_room_payload)

NOT_IN_ROOM = 4003


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.player = None
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"room_{self.code}"

        session_key = self.scope["session"].session_key
        self.player = await get_player(self.code, session_key)
        if self.player is None:
            # Accept pa close, da browser dobije naš kod i zna reloadati stranicu.
            await self.accept()
            await self.close(code=NOT_IN_ROOM)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        async with runtime.room_lock(self.code):
            runtime.add_connection(self.code, self.channel_name, self.player["id"])
            await self.broadcast_state()

    async def disconnect(self, close_code):
        if self.player is None:
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        async with runtime.room_lock(self.code):
            runtime.remove_connection(self.code, self.channel_name)
            await self.broadcast_state()

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            return
        handlers = {
            "start_game": self.on_start_game,
            "end_game": self.on_end_game,
            "action": self.on_action,
        }
        handler = handlers.get(content.get("type"))
        if handler is None:
            await self.send_error("Unknown message type.")
            return

        try:
            async with runtime.room_lock(self.code):
                await handler(content)
                await self.broadcast_state()
        except GameError as exc:
            await self.send_error(str(exc))

    # --- Poruke od klijenta ---

    async def on_start_game(self, content):
        await start_game(self.code, content.get("game_type"))

    async def on_end_game(self, content):
        await end_game(self.code)

    async def on_action(self, content):
        action = content.get("action")
        if not isinstance(action, dict):
            raise GameError("Invalid action.")
        await apply_action(self.code, self.player, action)

    # --- Slanje klijentima ---

    async def broadcast_state(self):
        # Šaljemo samo signal. Svaki consumer zatim sam sastavi
        # poruku za svog igrača, jer igre smiju imati skrivene informacije.
        await self.channel_layer.group_send(self.group_name, {"type": "room.changed"})

    async def room_changed(self, event):
        payload = await build_room_payload(
            self.code, runtime.online_player_ids(self.code), self.player
        )
        await self.send_json({"type": "state", **payload})

    async def send_error(self, message):
        await self.send_json({"type": "error", "message": message})