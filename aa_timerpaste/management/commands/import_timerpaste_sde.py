import yaml
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from aa_timerpaste.models import SolarSystemMap


class Command(BaseCommand):
    help = "Import system -> region mapping from a local EVE SDE universe directory."

    def add_arguments(self, parser):
        parser.add_argument("universe_root", type=str, help="Path to fsd/universe/eve")

    def handle(self, *args, **options):
        universe_root = Path(options["universe_root"])
        if not universe_root.exists():
            raise CommandError(f"Path not found: {universe_root}")

        region_count = 0
        system_count = 0
        SolarSystemMap.objects.all().delete()

        for region_dir in universe_root.iterdir():
            if not region_dir.is_dir():
                continue
            region_name = region_dir.name.replace("_", " ")
            region_count += 1

            for constellation_dir in region_dir.iterdir():
                if not constellation_dir.is_dir():
                    continue
                constellation_name = constellation_dir.name.replace("_", " ")

                for system_dir in constellation_dir.iterdir():
                    if not system_dir.is_dir():
                        continue
                    system_name = system_dir.name.replace("_", " ")

                    SolarSystemMap.objects.update_or_create(
                        system_name=system_name,
                        defaults={
                            "region_name": region_name,
                            "constellation_name": constellation_name,
                        },
                    )
                    system_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported {system_count} solar systems across {region_count} regions."
        ))
