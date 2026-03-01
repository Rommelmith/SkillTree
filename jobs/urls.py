from django.urls import path
from .views import AnalyticsView, FetchStatusView, HotJobsView, JobListView

urlpatterns = [
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("status/", FetchStatusView.as_view(), name="fetch-status"),
    path("fetch/", FetchStatusView.as_view(), name="trigger-fetch"),
    path("hotjobs/", HotJobsView.as_view(), name="hot-jobs"),
]
