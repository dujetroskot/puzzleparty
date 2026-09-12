from django.urls import path

from . import views

app_name = "country"

urlpatterns = [
    path("search/", views.search, name="search"),
]