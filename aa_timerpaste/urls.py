from django.urls import path
from . import views

app_name = "aa_timerpaste"

urlpatterns = [
    path("", views.TimerEntryListView.as_view(), name="list"),
    path("paste/", views.TimerPasteView.as_view(), name="paste"),
]
