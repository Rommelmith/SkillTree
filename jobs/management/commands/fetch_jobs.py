"""
Management command: python manage.py fetch_jobs

Usage:
  python manage.py fetch_jobs                  # full scrape
  python manage.py fetch_jobs --no-ats         # feeds only
  python manage.py fetch_jobs --no-feeds       # ATS only
  python manage.py fetch_jobs --workers 10     # parallel ATS fetching
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the job scraper immediately and save results to the database."

    def add_arguments(self, parser):
        parser.add_argument("--no-ats", action="store_true", help="Skip ATS career pages")
        parser.add_argument("--no-feeds", action="store_true", help="Skip public feed sources")
        parser.add_argument("--workers", type=int, default=6, help="Parallel ATS fetch workers (default 6)")

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting job fetch..."))
        from jobs.tasks import run_fetch

        try:
            count = run_fetch(
                include_ats=not options["no_ats"],
                include_feeds=not options["no_feeds"],
                max_workers=options["workers"],
            )
            self.stdout.write(self.style.SUCCESS(f"Done — {count} jobs saved."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Fetch failed: {e}"))
            raise
