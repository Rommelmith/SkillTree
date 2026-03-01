from rest_framework import serializers
from .models import JobRecord, FetchLog


class JobRecordSerializer(serializers.ModelSerializer):
    salary_display = serializers.ReadOnlyField()
    apply_link = serializers.ReadOnlyField()

    class Meta:
        model = JobRecord
        fields = [
            "id",
            "source",
            "title",
            "company",
            "location",
            "seniority",
            "is_remote",
            "workplace_type",
            "extracted_skills",
            "salary_display",
            "salary_min",
            "salary_max",
            "salary_currency",
            "apply_link",
            "company_logo",
            "tags",
            "posted_at",
            "first_seen",
        ]


class FetchLogSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = FetchLog
        fields = ["id", "started_at", "completed_at", "jobs_fetched", "status", "error", "duration_seconds"]
