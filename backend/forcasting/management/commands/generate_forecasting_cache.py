from django.core.management.base import BaseCommand

from forcasting.forcasting import CACHE_FILE, generate_cache


class Command(BaseCommand):
    help = "Generate and persist forecasting cache JSON for frontend/API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild cache even if source files are unchanged.",
        )

    def handle(self, *args, **options):
        payloads = generate_cache(force=bool(options["force"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Forecasting cache ready: {CACHE_FILE} ({len(payloads)} regions)"
            )
        )
