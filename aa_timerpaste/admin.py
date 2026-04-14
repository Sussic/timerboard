from django.contrib import admin
from .models import SolarSystemMap, TimerEntry


@admin.register(SolarSystemMap)
class SolarSystemMapAdmin(admin.ModelAdmin):
    list_display = ("system_name", "region_name", "constellation_name")
    search_fields = ("system_name", "region_name", "constellation_name")


@admin.register(TimerEntry)
class TimerEntryAdmin(admin.ModelAdmin):
    list_display = ("details", "system_name", "region_name", "structure_type", "timer_at", "parse_status")
    search_fields = ("details", "system_name", "region_name", "raw_text")
    list_filter = ("structure_type", "objective", "parse_status", "region_name")
