import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _enable_wal(sender, connection, **kwargs):
    """
    Switch SQLite to WAL journal mode on every new connection.

    WAL (Write-Ahead Logging) allows concurrent readers while a single
    writer holds the lock, which eliminates most "database is locked"
    errors when the background scraper thread writes at the same time as
    the web server handles requests.
    """
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")  # ms — SQLite-level wait


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"

    def ready(self):
        """
        Called once when Django finishes loading.

        - In development (`runserver`), Django spawns a child process with
          RUN_MAIN=true for the actual server; the parent is just the file
          watcher.  We only start the scheduler in the child.
        - In production (gunicorn/uvicorn), RUN_MAIN is unset; we start it
          unconditionally (set DISABLE_SCHEDULER=1 to skip for workers that
          shouldn't run background tasks).
        """
        if os.environ.get("DISABLE_SCHEDULER") == "1":
            return

        run_main = os.environ.get("RUN_MAIN")
        # In dev: only start in the real server process (RUN_MAIN='true')
        # In prod: RUN_MAIN is not set, so start always
        if run_main is not None and run_main != "true":
            return

        # Register WAL mode for every new SQLite connection
        from django.db.backends.signals import connection_created
        connection_created.connect(_enable_wal)

        from django.conf import settings

        interval = getattr(settings, "JOB_FETCH_INTERVAL_SECONDS", 28800)

        from .scheduler import start
        start(interval_seconds=interval)

        # Kick off an immediate fetch in a background thread if DB is empty
        self._initial_fetch_if_needed()

    @staticmethod
    def _initial_fetch_if_needed():
        import threading

        def _check_and_fetch():
            try:
                from django.db import connection
                # Guard: only run if the jobs table actually exists (post-migrate)
                if "jobs_jobrecord" not in connection.introspection.table_names():
                    return
                from .models import JobRecord
                if not JobRecord.objects.exists():
                    logger.info("DB empty — running initial job fetch...")
                    from .tasks import run_fetch
                    run_fetch()
            except Exception as e:
                logger.error("Initial fetch failed: %s", e)

        t = threading.Thread(target=_check_and_fetch, daemon=True, name="initial-fetch")
        t.start()
