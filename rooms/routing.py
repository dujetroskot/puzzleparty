from django.urls import path

from .consumers import RoomConsumer

websocket_urlpatterns = [
    path("ws/room/<str:code>/", RoomConsumer.as_asgi()),
]