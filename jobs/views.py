import random
import threading
from datetime import datetime, timezone as dt_timezone

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalyticsSnapshot, FetchLog, JobRecord
from .serializers import FetchLogSerializer, JobRecordSerializer

# Friendly display names for each source
SOURCE_LABELS = {
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "lever": "Lever",
    "remoteok": "RemoteOK",
    "arbeitnow": "Arbeitnow",
    "remotive": "Remotive",
    "jobicy": "Jobicy",
    "himalayas": "Himalayas",
    "hn_whoishiring": "HN Hiring",
    "amazon": "Amazon Jobs",
    "google": "Google Careers",
    "meta": "Meta Careers",
    "apple": "Apple Jobs",
}


class JobListView(APIView):
    """
    GET /api/jobs/
    Query params: source, skill, seniority, remote, search, page, size
    """

    def get(self, request):
        qs = JobRecord.objects.all()

        source = request.query_params.get("source")
        skill = request.query_params.get("skill")
        seniority = request.query_params.get("seniority")
        remote = request.query_params.get("remote")
        search = request.query_params.get("search")

        if source:
            qs = qs.filter(source=source)
        if skill:
            qs = qs.filter(extracted_skills__contains=[skill])
        if seniority:
            qs = qs.filter(seniority=seniority)
        if remote is not None:
            qs = qs.filter(is_remote=(remote.lower() == "true"))
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(company__icontains=search)
                | Q(description__icontains=search)
            )

        # Pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            size = min(200, max(1, int(request.query_params.get("size", 50))))
        except ValueError:
            page, size = 1, 50

        total = qs.count()
        start = (page - 1) * size
        jobs = qs[start : start + size]

        return Response(
            {
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size,
                "jobs": JobRecordSerializer(jobs, many=True).data,
            }
        )


class AnalyticsView(APIView):
    """GET /api/analytics/ — latest analytics snapshot."""

    def get(self, request):
        snapshot = AnalyticsSnapshot.objects.first()
        if snapshot:
            return Response(snapshot.data)

        # No snapshot yet — fetch is still in progress.
        # Return a lightweight live count so the dashboard can render
        # basic stats while the full analytics are being computed.
        total = JobRecord.objects.count()
        fetch_running = FetchLog.objects.filter(status="running").exists()
        return Response(
            {
                "_pending": True,
                "_message": "First fetch in progress — full analytics coming soon.",
                "meta": {
                    "total_jobs": total,
                    "unique_skills": 0,
                    "sources": {},
                    "scraped_at": None,
                },
                "skill_rankings": [],
                "skill_combos": [],
                "remote": {"remote": 0, "onsite": total, "pct": 0},
                "seniority": {},
                "salary": {"with_data": 0, "avg_min": 0, "avg_max": 0},
                "top_companies": [],
            },
            status=status.HTTP_200_OK,
        )


class FetchStatusView(APIView):
    """
    GET  /api/status/ — last fetch log
    POST /api/fetch/  — trigger an immediate background fetch
    """

    def get(self, request):
        log = FetchLog.objects.first()
        if not log:
            return Response({"status": "never_run", "jobs_in_db": 0})
        return Response(
            {
                **FetchLogSerializer(log).data,
                "jobs_in_db": JobRecord.objects.count(),
                "next_run_in": _next_run_seconds(),
            }
        )

    def post(self, request):
        # Guard against overlapping fetches
        if FetchLog.objects.filter(status="running").exists():
            return Response(
                {"detail": "A fetch is already running."},
                status=status.HTTP_409_CONFLICT,
            )
        from .tasks import run_fetch

        t = threading.Thread(target=run_fetch, daemon=True)
        t.start()
        return Response({"detail": "Fetch started."}, status=status.HTTP_202_ACCEPTED)


class HotJobsView(APIView):
    """
    GET /api/hotjobs/
    Returns 24 jobs from at least 5 different sources.
    The selection rotates every 20 minutes using a time-based seed,
    so the listing refreshes without any new scraping.
    """

    TOTAL = 24         # jobs to return
    MIN_SOURCES = 5    # minimum distinct sources in result
    MAX_PER_SOURCE = 4 # hard cap per source to ensure diversity

    def get(self, request):
        # 20-minute rotation window (changes every 1200 seconds)
        now = datetime.now(dt_timezone.utc)
        window = int(now.timestamp()) // 1200

        # Fetch candidates: must have skills + a URL
        candidates = list(
            JobRecord.objects
            .exclude(extracted_skills=[])
            .exclude(source_url="")
            .values(
                "id", "title", "company", "source", "location",
                "extracted_skills", "salary_min", "salary_max",
                "salary_text", "apply_url", "source_url",
                "posted_at", "first_seen", "is_remote", "seniority",
            )
        )

        if not candidates:
            return Response({"jobs": [], "window": window})

        # Group by source
        by_source: dict = {}
        for job in candidates:
            by_source.setdefault(job["source"], []).append(job)

        # Use a seeded RNG so results are stable within the same 30-min window
        rng = random.Random(window)

        # Shuffle each source's pool
        for src_jobs in by_source.values():
            rng.shuffle(src_jobs)

        # Build the selection:
        # Round-robin across all sources (shuffled), max MAX_PER_SOURCE per source
        sources_shuffled = list(by_source.keys())
        rng.shuffle(sources_shuffled)

        picked = []
        source_counts: dict = {}
        # Two passes: first pass picks 1 from each source until we have MIN_SOURCES
        for src in sources_shuffled:
            if len(picked) >= self.TOTAL:
                break
            pool = by_source[src]
            if pool:
                picked.append(pool.pop(0))
                source_counts[src] = 1

        # Second pass: fill remaining slots (up to MAX_PER_SOURCE per source)
        for src in sources_shuffled:
            if len(picked) >= self.TOTAL:
                break
            if source_counts.get(src, 0) >= self.MAX_PER_SOURCE:
                continue
            pool = by_source[src]
            if pool:
                picked.append(pool.pop(0))
                source_counts[src] = source_counts.get(src, 0) + 1

        # Shuffle final result so source order varies
        rng.shuffle(picked)

        def _salary(j):
            if j["salary_min"] and j["salary_max"]:
                mn, mx = int(j["salary_min"]), int(j["salary_max"])
                if mn >= 1000:
                    return f"${mn // 1000}K–${mx // 1000}K"
                return f"${mn:,}–${mx:,}"
            return j["salary_text"] or None

        serialized = [
            {
                "id": j["id"],
                "title": j["title"],
                "company": j["company"],
                "source": j["source"],
                "source_label": SOURCE_LABELS.get(j["source"], j["source"]),
                "location": j["location"] or ("Remote" if j["is_remote"] else ""),
                "skills": (j["extracted_skills"] or [])[:5],
                "salary": _salary(j),
                "url": j["apply_url"] or j["source_url"],
                "posted_at": j["posted_at"],
                "first_seen": j["first_seen"].isoformat() if j["first_seen"] else None,
                "seniority": j["seniority"],
                "is_remote": j["is_remote"],
                "hot": bool(j["salary_min"] and j["salary_min"] > 150_000)
                       or len(j["extracted_skills"] or []) > 5,
            }
            for j in picked
        ]

        # Tell the frontend when the next rotation happens
        next_rotation_in = 1200 - (int(now.timestamp()) % 1200)

        return Response({
            "jobs": serialized,
            "window": window,
            "next_rotation_in": next_rotation_in,
            "sources": list(source_counts.keys()),
        })


def _next_run_seconds():
    """Seconds until the next scheduled fetch."""
    try:
        from .scheduler import scheduler

        job = scheduler.get_job("fetch_jobs")
        if job and job.next_run_time:
            from django.utils import timezone

            delta = job.next_run_time - timezone.now()
            return max(0, int(delta.total_seconds()))
    except Exception:
        pass
    return None
