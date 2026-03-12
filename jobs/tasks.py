"""
tasks.py — runs the scraper and persists results to the Django DB.
Called by the scheduler every 8 hours, or manually via POST /api/fetch/.
"""
from __future__ import annotations

import logging
import time

from django.db import OperationalError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# How many times to retry a batch on "database is locked" before giving up
_LOCK_RETRIES = 5
_LOCK_RETRY_DELAY = 2  # seconds between retries


def _upsert_with_retry(uid: str, defaults: dict, JobRecord) -> bool:
    """
    update_or_create with retry logic for SQLite 'database is locked'.
    Returns True on success, False after exhausting retries.
    """
    for attempt in range(_LOCK_RETRIES):
        try:
            JobRecord.objects.update_or_create(uid=uid, defaults=defaults)
            return True
        except OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < _LOCK_RETRIES - 1:
                time.sleep(_LOCK_RETRY_DELAY)
            else:
                raise
    return False


def run_fetch(
    include_ats: bool = True,
    include_feeds: bool = True,
    max_workers: int = 6,
) -> int:
    """
    Execute a full scrape cycle.
    Returns the number of jobs upserted.
    """
    from .models import AnalyticsSnapshot, FetchLog, JobRecord
    from .scraper import gather_all, generate_analytics

    log = FetchLog.objects.create(status="running")
    logger.info("Starting job fetch (log id=%s)", log.pk)

    try:
        scraped_jobs = gather_all(
            include_ats=include_ats,
            include_feeds=include_feeds,
            max_workers=max_workers,
        )

        # ── Build list of (uid, defaults) pairs ──────────────────────────
        rows = []
        for jr in scraped_jobs:
            rows.append((
                jr.uid(),
                {
                    "source": jr.source,
                    "source_id": jr.source_id or "",
                    "source_url": (jr.source_url or "")[:800],
                    "title": (jr.title or "")[:500],
                    "company": (jr.company or "")[:200],
                    "location": (jr.location or "")[:300],
                    "description": jr.description or "",
                    "tags": jr.tags or [],
                    "posted_at": jr.posted_at,
                    "updated_at_raw": jr.updated_at,
                    "is_remote": jr.is_remote,
                    "workplace_type": jr.workplace_type,
                    "team": jr.team,
                    "department": jr.department,
                    "salary_min": jr.salary_min,
                    "salary_max": jr.salary_max,
                    "salary_currency": jr.salary_currency,
                    "salary_text": jr.salary_text,
                    "apply_url": (jr.apply_url or "")[:800] if jr.apply_url else None,
                    "company_logo": (jr.company_logo or "")[:800] if jr.company_logo else None,
                    "extracted_skills": jr.extracted_skills or [],
                    "seniority": jr.seniority or "",
                    "job_type": jr.job_type or "",
                },
            ))

        # ── Upsert in one atomic transaction (one lock acquisition) ───────
        # Chunk into batches of 200 so the transaction doesn't grow huge and
        # the write lock is held for a short, bounded time per chunk.
        CHUNK = 200
        count = 0
        failed = 0

        for i in range(0, len(rows), CHUNK):
            chunk = rows[i : i + CHUNK]
            try:
                with transaction.atomic():
                    for uid, defaults in chunk:
                        JobRecord.objects.update_or_create(uid=uid, defaults=defaults)
                        count += 1
            except OperationalError as e:
                if "database is locked" in str(e).lower():
                    # Retry the entire chunk with individual retries
                    logger.warning("Chunk %d locked, retrying row-by-row…", i // CHUNK)
                    for uid, defaults in chunk:
                        try:
                            _upsert_with_retry(uid, defaults, JobRecord)
                            count += 1
                        except Exception as row_err:
                            logger.warning("Failed to upsert job %s: %s", uid, row_err)
                            failed += 1
                else:
                    raise
            except Exception as exc:
                logger.error("Chunk %d failed: %s", i // CHUNK, exc)
                failed += len(chunk)

        if failed:
            logger.warning("%d jobs could not be saved (lock exhausted)", failed)

        # ── Analytics ─────────────────────────────────────────────────────
        if scraped_jobs:
            analytics_data = generate_analytics(scraped_jobs)

            # Groq AI Insights (enriches analytics before saving)
            try:
                from django.conf import settings as dj_settings
                groq_key = getattr(dj_settings, "GROQ_API_KEY", None)
                if groq_key:
                    from .groq_insights import generate_ai_insights
                    logger.info("Generating AI insights via Groq...")
                    analytics_data["ai_insights"] = generate_ai_insights(analytics_data, groq_key)
                    logger.info("AI insights generated successfully")
            except Exception as groq_err:
                logger.warning("Groq insights skipped: %s", groq_err)

            with transaction.atomic():
                AnalyticsSnapshot.objects.create(data=analytics_data)
                old_ids = list(
                    AnalyticsSnapshot.objects.order_by("-created_at")
                    .values_list("id", flat=True)[10:]
                )
                if old_ids:
                    AnalyticsSnapshot.objects.filter(id__in=old_ids).delete()

            # ── Skill Snapshots (historical trend data) ──────────────────
            try:
                from .models import SkillSnapshot
                now = timezone.now()
                total_jobs = len(scraped_jobs)
                skill_rankings = analytics_data.get("skill_rankings", [])
                snapshot_rows = [
                    SkillSnapshot(
                        skill_name=sr["skill"],
                        mention_count=sr["jobs"],
                        total_jobs=total_jobs,
                        scraped_at=now,
                    )
                    for sr in skill_rankings
                ]
                if snapshot_rows:
                    with transaction.atomic():
                        SkillSnapshot.objects.bulk_create(snapshot_rows)
                    logger.info("Saved %d skill snapshots", len(snapshot_rows))

                # Prune raw snapshots older than 30 days
                cutoff = now - timezone.timedelta(days=30)
                pruned, _ = SkillSnapshot.objects.filter(scraped_at__lt=cutoff).delete()
                if pruned:
                    logger.info("Pruned %d old skill snapshots", pruned)
            except Exception as snap_err:
                logger.warning("Skill snapshots skipped: %s", snap_err)
        else:
            logger.warning("Scrape returned 0 jobs; preserving previous analytics snapshot.")

        log.completed_at = timezone.now()
        log.jobs_fetched = count
        log.status = "success"
        log.save()

        logger.info("Fetch complete: %d saved, %d failed", count, failed)
        return count

    except Exception as exc:
        logger.error("Fetch failed: %s", exc, exc_info=True)
        log.status = "error"
        log.error = str(exc)
        log.save()
        raise
