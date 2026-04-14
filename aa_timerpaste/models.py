from django.conf import settings
from django.db import models


class SolarSystemMap(models.Model):
    system_name = models.CharField(max_length=64, unique=True, db_index=True)
    region_name = models.CharField(max_length=64, blank=True)
    constellation_name = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["system_name"]

    def __str__(self):
        return f"{self.system_name} ({self.region_name})"


class TimerEntry(models.Model):
    STRUCTURE_CHOICES = [
        ("skyhook", "Orbital Skyhook"),
        ("metenox", "Metenox Moon Drill"),
        ("mercenary_den", "Mercenary Den"),
        ("ansiblex", "Ansiblex"),
        ("astrahus", "Astrahus"),
        ("athanor", "Athanor"),
        ("fortizar", "Fortizar"),
        ("pos", "POS"),
        ("poco", "POCO"),
        ("other", "Other"),
    ]

    OBJECTIVE_CHOICES = [
        ("hostile", "Hostile"),
        ("friendly", "Friendly"),
        ("unknown", "Unknown"),
    ]

    PARSE_STATUS_CHOICES = [
        ("parsed", "Parsed"),
        ("partial", "Partial"),
        ("unknown_system", "Unknown System"),
        ("failed", "Failed"),
    ]

    raw_text = models.TextField(blank=True)
    details = models.CharField(max_length=255, blank=True)
    objective = models.CharField(max_length=16, choices=OBJECTIVE_CHOICES, default="unknown")
    system_name = models.CharField(max_length=64, blank=True, db_index=True)
    region_name = models.CharField(max_length=64, blank=True)
    moon_or_location = models.CharField(max_length=128, blank=True)
    structure_type = models.CharField(max_length=32, choices=STRUCTURE_CHOICES, default="other")
    owner_name = models.CharField(max_length=128, blank=True)
    distance_text = models.CharField(max_length=64, blank=True)
    timer_at = models.DateTimeField()
    parse_status = models.CharField(max_length=32, choices=PARSE_STATUS_CHOICES, default="parsed")
    parse_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timerpaste_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timer_at"]
        permissions = [
            ("use_paste_import", "Can use timer paste import"),
        ]

    def __str__(self):
        label = self.details or self.get_structure_type_display()
        return f"{label} - {self.system_name} - {self.timer_at.isoformat()}"
