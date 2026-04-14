from django.contrib import admin
from .models import SolarSystemMap, TimerEntry


@admin.register(SolarSystemMap)
class SolarSystemMapAdmin(admin.ModelAdmin):
    list_display = ("system_name", "region_name", "constellation_name")
    search_fields = ("system_name", "region_name", "constellation_name")


@admin.register(TimerEntry)
class TimerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "details",
        "system_name",
        "region_name",
        "structure_type",
        "objective",
        "priority",
        "timer_state",
        "timer_at",
        "is_archived",
    )
    search_fields = ("details", "system_name", "region_name", "campaign_name", "raw_text", "notes")
    list_filter = ("structure_type", "objective", "priority", "timer_state", "region_name", "is_archived")
