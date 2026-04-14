from django.conf import settings
from django.db import models
from django.utils import timezone


class SolarSystemMap(models.Model):
    system_name = models.CharField(max_length=64, unique=True, db_index=True)
    region_name = models.CharField(max_length=64, blank=True)
    constellation_name = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["system_name"]

    def __str__(self):
        return f"{self.system_name} ({self.region_name})"


class TimerEntryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_archived=False)

    def upcoming(self):
        return self.filter(timer_at__gte=timezone.now())


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
        ("neutral", "Neutral"),
        ("friendly", "Friendly"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATE_CHOICES = [
        ("unknown", "Unknown"),
        ("shield", "Shield"),
        ("armor", "Armor"),
        ("hull", "Hull"),
        ("final", "Final"),
    ]

    SOURCE_CHOICES = [
        ("paste", "Bulk Paste"),
        ("manual", "Manual Edit"),
    ]

    raw_text = models.TextField(blank=True)
    details = models.CharField(max_length=255, blank=True)
    objective = models.CharField(max_length=16, choices=OBJECTIVE_CHOICES, default="hostile")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="normal")
    timer_state = models.CharField(max_length=16, choices=STATE_CHOICES, default="unknown")
    campaign_name = models.CharField(max_length=128, blank=True, db_index=True)
    system_name = models.CharField(max_length=64, blank=True, db_index=True)
    region_name = models.CharField(max_length=64, blank=True, db_index=True)
    constellation_name = models.CharField(max_length=64, blank=True)
    moon_or_location = models.CharField(max_length=128, blank=True)
    structure_type = models.CharField(max_length=32, choices=STRUCTURE_CHOICES, default="other", db_index=True)
    owner_name = models.CharField(max_length=128, blank=True)
    timer_at = models.DateTimeField(db_index=True)
    notes = models.TextField(blank=True)
    parse_notes = models.TextField(blank=True)
    source_kind = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="paste")
    duplicate_key = models.CharField(max_length=255, blank=True, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timerpaste_archived_entries",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timerpaste_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timerpaste_updated_entries",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimerEntryQuerySet.as_manager()

    class Meta:
        ordering = ["timer_at", "region_name", "system_name"]
        permissions = [
            ("use_paste_import", "Can use timer paste import"),
            ("archive_timerentry", "Can archive timer entry"),
            ("export_timerentry", "Can export timer entries"),
        ]

    def __str__(self):
        label = self.details or self.get_structure_type_display()
        return f"{label} - {self.system_name} - {self.timer_at.isoformat()}"

    def build_duplicate_key(self):
        timer_part = self.timer_at.strftime("%Y-%m-%d %H:%M:%S") if self.timer_at else ""
        return "|".join([
            (self.system_name or "").strip().upper(),
            (self.moon_or_location or "").strip().upper(),
            (self.structure_type or "").strip().lower(),
            timer_part,
        ])

    def save(self, *args, **kwargs):
        self.duplicate_key = self.build_duplicate_key()
        super().save(*args, **kwargs)
