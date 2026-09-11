from django import forms

from . import services
from .models import Room


class JoinRoomForm(forms.Form):
    code = forms.CharField(max_length=8)

    def clean_code(self):
        code = services.normalize_code(self.cleaned_data["code"])
        if not Room.objects.filter(code=code).exists():
            raise forms.ValidationError("Room with that code doesn't exist.")
        return code


class NicknameForm(forms.Form):
    nickname = forms.CharField(max_length=24)