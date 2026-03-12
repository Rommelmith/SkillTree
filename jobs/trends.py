"""
trends.py — Trend computation utilities for historical skill analysis.
Works with SkillSnapshot and DailySkillAggregate models.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Avg, Sum
from django.utils import timezone


def _get_model():
    from .models import DailySkillAggregate, SkillSnapshot
    return SkillSnapshot, DailySkillAggregate


def _period_mentions(skill_name: str, end_date: date, days: int) -> int:
    """Sum of daily mentions for a skill over a period ending at end_date."""
    _, DailySkillAggregate = _get_model()
    start = end_date - timedelta(days=days)
    result = (
        DailySkillAggregate.objects
        .filter(skill_name=skill_name, date__gt=start, date__lte=end_date)
        .aggregate(total=Sum("total_mentions"))
    )
    return result["total"] or 0


def get_week_over_week_delta(skill_name: str) -> Optional[float]:
    """% change in mentions vs previous 7 days. Returns None if no data."""
    today = date.today()
    current = _period_mentions(skill_name, today, 7)
    previous = _period_mentions(skill_name, today - timedelta(days=7), 7)
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def get_monthly_delta(skill_name: str) -> Optional[float]:
    """% change vs previous 30 days."""
    today = date.today()
    current = _period_mentions(skill_name, today, 30)
    previous = _period_mentions(skill_name, today - timedelta(days=30), 30)
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def get_trending_skills(n: int = 10, period_days: int = 7) -> List[Dict[str, Any]]:
    """Top N skills with highest positive delta over period."""
    _, DailySkillAggregate = _get_model()
    today = date.today()

    # Get all skills that have data in the current period
    current_start = today - timedelta(days=period_days)
    prev_start = current_start - timedelta(days=period_days)

    current_data = dict(
        DailySkillAggregate.objects
        .filter(date__gt=current_start, date__lte=today)
        .values_list("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )
    prev_data = dict(
        DailySkillAggregate.objects
        .filter(date__gt=prev_start, date__lte=current_start)
        .values_list("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )

    results = []
    for skill, current in current_data.items():
        prev = prev_data.get(skill, 0)
        if prev == 0:
            continue
        delta = round((current - prev) / prev * 100, 1)
        results.append({
            "skill": skill,
            "current_mentions": current,
            "delta_pct": delta,
            "period": f"{period_days}d",
        })

    results.sort(key=lambda x: x["delta_pct"], reverse=True)
    return results[:n]


def get_declining_skills(n: int = 10, period_days: int = 7) -> List[Dict[str, Any]]:
    """Top N skills with highest negative delta."""
    _, DailySkillAggregate = _get_model()
    today = date.today()

    current_start = today - timedelta(days=period_days)
    prev_start = current_start - timedelta(days=period_days)

    current_data = dict(
        DailySkillAggregate.objects
        .filter(date__gt=current_start, date__lte=today)
        .values_list("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )
    prev_data = dict(
        DailySkillAggregate.objects
        .filter(date__gt=prev_start, date__lte=current_start)
        .values_list("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )

    results = []
    for skill, current in current_data.items():
        prev = prev_data.get(skill, 0)
        if prev == 0:
            continue
        delta = round((current - prev) / prev * 100, 1)
        if delta < 0:
            results.append({
                "skill": skill,
                "current_mentions": current,
                "delta_pct": delta,
                "period": f"{period_days}d",
            })

    results.sort(key=lambda x: x["delta_pct"])
    return results[:n]


def get_skill_timeseries(skill_name: str, days: int = 90) -> List[Dict[str, Any]]:
    """Returns list of {date, mentions} dicts for charting."""
    _, DailySkillAggregate = _get_model()
    cutoff = date.today() - timedelta(days=days)
    rows = (
        DailySkillAggregate.objects
        .filter(skill_name=skill_name, date__gt=cutoff)
        .order_by("date")
        .values_list("date", "total_mentions")
    )
    return [{"date": str(d), "mentions": m} for d, m in rows]


def get_velocity(skill_name: str) -> str:
    """Is the growth accelerating or decelerating? (delta of deltas)"""
    today = date.today()

    # Recent 7d vs previous 7d
    recent = _period_mentions(skill_name, today, 7)
    mid = _period_mentions(skill_name, today - timedelta(days=7), 7)
    old = _period_mentions(skill_name, today - timedelta(days=14), 7)

    if old == 0 or mid == 0:
        return "insufficient_data"

    delta_recent = (recent - mid) / mid
    delta_old = (mid - old) / old

    if delta_recent > delta_old + 0.02:
        return "accelerating"
    elif delta_recent < delta_old - 0.02:
        return "decelerating"
    return "stable"


def get_skill_rankings_with_movement(n: int = 50) -> List[Dict[str, Any]]:
    """Current skill rankings with rank change vs previous period."""
    _, DailySkillAggregate = _get_model()
    today = date.today()
    current_start = today - timedelta(days=7)
    prev_start = current_start - timedelta(days=7)

    # Current period rankings
    current_data = list(
        DailySkillAggregate.objects
        .filter(date__gt=current_start, date__lte=today)
        .values("skill_name")
        .annotate(total=Sum("total_mentions"))
        .order_by("-total")[:n]
    )

    # Previous period rankings
    prev_data = list(
        DailySkillAggregate.objects
        .filter(date__gt=prev_start, date__lte=current_start)
        .values("skill_name")
        .annotate(total=Sum("total_mentions"))
        .order_by("-total")[:n]
    )

    prev_ranks = {row["skill_name"]: i + 1 for i, row in enumerate(prev_data)}

    rankings = []
    for i, row in enumerate(current_data):
        rank = i + 1
        skill = row["skill_name"]
        prev_rank = prev_ranks.get(skill)
        movement = (prev_rank - rank) if prev_rank else None
        rankings.append({
            "rank": rank,
            "skill": skill,
            "mentions": row["total"],
            "prev_rank": prev_rank,
            "movement": movement,
        })

    return rankings


def get_movers_from_snapshots(n: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """
    Fallback: compute movers directly from SkillSnapshot when DailySkillAggregate
    doesn't have enough data yet. Compares the latest two snapshots.
    """
    SkillSnapshot, _ = _get_model()

    # Get the distinct scrape timestamps (last 2)
    timestamps = list(
        SkillSnapshot.objects
        .values_list("scraped_at", flat=True)
        .distinct()
        .order_by("-scraped_at")[:2]
    )

    if len(timestamps) < 2:
        return [], []

    latest_ts, prev_ts = timestamps[0], timestamps[1]

    latest = {
        row["skill_name"]: row["mention_count"]
        for row in SkillSnapshot.objects
        .filter(scraped_at=latest_ts)
        .values("skill_name", "mention_count")
    }
    prev = {
        row["skill_name"]: row["mention_count"]
        for row in SkillSnapshot.objects
        .filter(scraped_at=prev_ts)
        .values("skill_name", "mention_count")
    }

    deltas = []
    for skill, count in latest.items():
        p = prev.get(skill, 0)
        if p == 0:
            continue
        delta = round((count - p) / p * 100, 1)
        deltas.append({
            "skill": skill,
            "current_mentions": count,
            "delta_pct": delta,
            "period": "last_scrape",
        })

    risers = sorted([d for d in deltas if d["delta_pct"] > 0], key=lambda x: -x["delta_pct"])[:n]
    fallers = sorted([d for d in deltas if d["delta_pct"] < 0], key=lambda x: x["delta_pct"])[:n]

    return risers, fallers


def get_sparkline_bulk(skill_names: List[str], days: int = 30) -> Dict[str, List[int]]:
    """
    Batch-fetch sparkline data for multiple skills at once.
    Returns {skill_name: [mentions_day1, mentions_day2, ...]}
    """
    _, DailySkillAggregate = _get_model()
    cutoff = date.today() - timedelta(days=days)

    rows = (
        DailySkillAggregate.objects
        .filter(skill_name__in=skill_names, date__gt=cutoff)
        .order_by("skill_name", "date")
        .values_list("skill_name", "date", "total_mentions")
    )

    result: Dict[str, List[int]] = defaultdict(list)
    for skill, d, mentions in rows:
        result[skill].append(mentions)

    return dict(result)


def get_delta_bulk(skill_names: List[str], period_days: int = 7) -> Dict[str, Optional[float]]:
    """
    Batch-compute deltas for multiple skills.
    Returns {skill_name: delta_pct_or_None}
    """
    _, DailySkillAggregate = _get_model()
    today = date.today()
    current_start = today - timedelta(days=period_days)
    prev_start = current_start - timedelta(days=period_days)

    current = dict(
        DailySkillAggregate.objects
        .filter(skill_name__in=skill_names, date__gt=current_start, date__lte=today)
        .values("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )
    prev = dict(
        DailySkillAggregate.objects
        .filter(skill_name__in=skill_names, date__gt=prev_start, date__lte=current_start)
        .values("skill_name")
        .annotate(total=Sum("total_mentions"))
        .values_list("skill_name", "total")
    )

    result = {}
    for skill in skill_names:
        c = current.get(skill, 0)
        p = prev.get(skill, 0)
        if p == 0:
            result[skill] = None
        else:
            result[skill] = round((c - p) / p * 100, 1)
    return result
