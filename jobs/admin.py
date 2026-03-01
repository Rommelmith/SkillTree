from django.contrib import admin
from .models import JobRecord, AnalyticsSnapshot, FetchLog


@admin.register(JobRecord)
class JobRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "source", "seniority", "is_remote", "first_seen")
    list_filter = ("source", "seniority", "is_remote")
    search_fields = ("title", "company", "description")
    readonly_fields = ("uid", "first_seen", "last_seen", "extracted_skills")
    ordering = ("-first_seen",)


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("created_at",)
    readonly_fields = ("created_at", "data")


@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display = ("started_at", "status", "jobs_fetched", "completed_at")
    readonly_fields = ("started_at", "completed_at", "jobs_fetched", "status", "error")
