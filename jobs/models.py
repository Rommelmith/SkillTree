from django.db import models
from django.utils import timezone


class JobRecord(models.Model):
    """Mirrors the JobRecord dataclass from the scraper, persisted to DB."""

    source = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=300, blank=True)
    source_url = models.CharField(max_length=800, blank=True)
    title = models.CharField(max_length=500)
    company = models.CharField(max_length=200, blank=True, db_index=True)
    location = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)

    tags = models.JSONField(default=list)
    posted_at = models.CharField(max_length=100, blank=True, null=True)
    updated_at_raw = models.CharField(max_length=100, blank=True, null=True)

    is_remote = models.BooleanField(null=True, db_index=True)
    workplace_type = models.CharField(max_length=50, blank=True, null=True)

    team = models.CharField(max_length=200, blank=True, null=True)
    department = models.CharField(max_length=200, blank=True, null=True)

    salary_min = models.FloatField(null=True, blank=True)
    salary_max = models.FloatField(null=True, blank=True)
    salary_currency = models.CharField(max_length=10, blank=True, null=True)
    salary_text = models.CharField(max_length=300, blank=True, null=True)

    apply_url = models.CharField(max_length=800, blank=True, null=True)
    company_logo = models.CharField(max_length=800, blank=True, null=True)

    extracted_skills = models.JSONField(default=list)
    seniority = models.CharField(max_length=50, blank=True, db_index=True)
    job_type = models.CharField(max_length=50, blank=True)

    # Unique identifier computed by the scraper
    uid = models.CharField(max_length=600, unique=True, db_index=True)

    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-first_seen"]

    def __str__(self):
        return f"{self.title} @ {self.company}"

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max:
            mn = int(self.salary_min)
            mx = int(self.salary_max)
            if mn >= 1000 and mx >= 1000:
                return f"${mn // 1000}K–${mx // 1000}K"
            return f"${mn:,}–${mx:,}"
        if self.salary_text:
            return self.salary_text
        return None

    @property
    def apply_link(self):
        return self.apply_url or self.source_url or ""


class AnalyticsSnapshot(models.Model):
    """Stores the latest analytics JSON generated after each scrape."""

    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Snapshot {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class FetchLog(models.Model):
    """Audit log for every scrape run."""

    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("error", "Error"),
    ]

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    jobs_fetched = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"FetchLog {self.started_at.strftime('%Y-%m-%d %H:%M')} [{self.status}]"

    @property
    def duration_seconds(self):
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).seconds
        return None
