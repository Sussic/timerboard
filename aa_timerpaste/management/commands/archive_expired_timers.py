from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from aa_timerpaste.models import TimerEntry


class Command(BaseCommand):
    help = "Archive timers older than the given number of hours."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24)

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(hours=options["hours"])
        updated = TimerEntry.objects.filter(is_archived=False, timer_at__lt=threshold).update(
            is_archived=True,
            archived_at=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS(f"Archived {updated} expired timers."))
