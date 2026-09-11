from django.urls import path

from . import views

app_name = "movie"

urlpatterns = [
    path("search/", views.search, name="search"),
]