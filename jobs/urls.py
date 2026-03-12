from django.urls import path
from .views import (
    AnalyticsView,
    FetchStatusView,
    HotJobsView,
    JobListView,
    SkillTrendView,
    TrendBulkView,
    TrendMoversView,
    TrendRankingsView,
)

urlpatterns = [
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("status/", FetchStatusView.as_view(), name="fetch-status"),
    path("fetch/", FetchStatusView.as_view(), name="trigger-fetch"),
    path("hotjobs/", HotJobsView.as_view(), name="hot-jobs"),
    path("trends/movers/", TrendMoversView.as_view(), name="trend-movers"),
    path("trends/skill/<str:skill_name>/", SkillTrendView.as_view(), name="skill-trend"),
    path("trends/rankings/", TrendRankingsView.as_view(), name="trend-rankings"),
    path("trends/bulk/", TrendBulkView.as_view(), name="trend-bulk"),
]
