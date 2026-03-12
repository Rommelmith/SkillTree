"""
Management command: python manage.py aggregate_snapshots

Rolls up raw SkillSnapshot rows into DailySkillAggregate for long-term
trend analysis. Intended to run daily via cron/systemd timer.

Usage:
  python manage.py aggregate_snapshots              # aggregate yesterday
  python manage.py aggregate_snapshots --date 2025-03-10   # specific date
  python manage.py aggregate_snapshots --backfill 7        # last N days
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum


class Command(BaseCommand):
    help = "Aggregate raw SkillSnapshots into DailySkillAggregate rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", type=str, default=None,
            help="Specific date to aggregate (YYYY-MM-DD). Default: yesterday.",
        )
        parser.add_argument(
            "--backfill", type=int, default=0,
            help="Backfill N days ending yesterday.",
        )

    def handle(self, *args, **options):
        from jobs.models import DailySkillAggregate, SkillSnapshot

        if options["backfill"] > 0:
            dates = [date.today() - timedelta(days=i) for i in range(1, options["backfill"] + 1)]
        elif options["date"]:
            dates = [date.fromisoformat(options["date"])]
        else:
            dates = [date.today() - timedelta(days=1)]

        total_created = 0
        total_updated = 0

        for target_date in sorted(dates):
            # Find all snapshots from this calendar day
            rows = (
                SkillSnapshot.objects
                .filter(scraped_at__date=target_date)
                .values("skill_name")
                .annotate(
                    total=Sum("mention_count"),
                    num=Count("id"),
                    avg=Avg("mention_count"),
                )
            )

            if not rows:
                self.stdout.write(f"  {target_date}: no snapshots found")
                continue

            created = 0
            updated = 0
            for row in rows:
                _, was_created = DailySkillAggregate.objects.update_or_create(
                    skill_name=row["skill_name"],
                    date=target_date,
                    defaults={
                        "total_mentions": row["total"],
                        "num_snapshots": row["num"],
                        "avg_mentions": round(row["avg"], 1),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {target_date}: {created} created, {updated} updated ({created + updated} skills)"
                )
            )
            total_created += created
            total_updated += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {total_created} created, {total_updated} updated across {len(dates)} day(s)."
            )
        )
