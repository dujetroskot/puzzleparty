from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import JoinRoomForm, NicknameForm
from .models import Room
from games.core.registry import all_games

SESSION_NICKNAME = "nickname"


def _ensure_session_key(request):
    # Django stvara session tek kad se nešto spremi, pa ga forsiramo.
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def home(request):
    return render(request, "rooms/home.html", {"join_form": JoinRoomForm()})


@require_POST
def create_room(request):
    room = services.create_room()
    return redirect("rooms:room", code=room.code)


@require_POST
def join_room(request):
    form = JoinRoomForm(request.POST)
    if form.is_valid():
        return redirect("rooms:room", code=form.cleaned_data["code"])
    return render(request, "rooms/home.html", {"join_form": form})


def room_detail(request, code):
    room = get_object_or_404(Room, code=services.normalize_code(code))
    if code != room.code:
        # /room/abcd/ -> /room/ABCD/
        return redirect("rooms:room", code=room.code)

    if request.method == "POST":
        form = NicknameForm(request.POST)
        if form.is_valid():
            request.session[SESSION_NICKNAME] = form.cleaned_data["nickname"]
            return redirect("rooms:room", code=room.code)
        return render(request, "rooms/nickname.html", {"room": room, "form": form})

    nickname = request.session.get(SESSION_NICKNAME)
    if not nickname:
        return render(
            request, "rooms/nickname.html", {"room": room, "form": NicknameForm()}
        )

    me = services.join_room(room, _ensure_session_key(request), nickname)
    context = {
        "room": room,
        "share_url": request.build_absolute_uri(),
        "games": all_games(),
        "room_config": {"code": room.code, "me": me.pk},
    }
    return render(request, "rooms/lobby.html", context)