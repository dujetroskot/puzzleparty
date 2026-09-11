from django.urls import path

from . import views

app_name = "rooms"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create_room, name="create"),
    path("join/", views.join_room, name="join"),
    path("room/<str:code>/", views.room_detail, name="room"),
]