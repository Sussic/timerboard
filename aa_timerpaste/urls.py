from django.urls import path
from . import views

app_name = "aa_timerpaste"

urlpatterns = [
    path("", views.TimerEntryListView.as_view(), name="list"),
    path("paste/", views.TimerPasteView.as_view(), name="paste"),
    path("export/csv/", views.TimerExportCsvView.as_view(), name="export_csv"),
    path("export/json/", views.TimerExportJsonView.as_view(), name="export_json"),
    path("<int:pk>/edit/", views.TimerEntryEditView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.TimerEntryArchiveView.as_view(), name="archive"),
    path("<int:pk>/delete/", views.TimerEntryDeleteView.as_view(), name="delete"),
]
