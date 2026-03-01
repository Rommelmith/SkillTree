"""
jobs_scraper.py
Scrape job listings from public ATS job-board APIs (Greenhouse, Ashby, Lever).

Why this works:
- Greenhouse Job Board API is public for GET endpoints. (boards-api.greenhouse.io)  [docs]
- Ashby has a public job posting endpoint. (api.ashbyhq.com/posting-api/job-board/...) [docs]
- Lever has a postings API supporting JSON output and pagination. (api.lever.co/v0/postings/...) [docs]

Install:
  pip install requests

Optional (for nicer CSV writing):
  pip install pandas

Run:
  python jobs_scraper.py --out jobs.json --csv jobs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Job:
    company: str
    source: str              # "greenhouse" | "ashby" | "lever"
    id: str
    title: str
    location: str
    team: Optional[str]
    department: Optional[str]
    workplace_type: Optional[str]
    is_remote: Optional[bool]
    updated_at: Optional[str]
    job_url: str
    apply_url: Optional[str]
    description_plain: Optional[str]


# -----------------------------
# HTTP helpers
# -----------------------------
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; JobScraper/1.0; +https://example.com)",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        }
    )
    return s


def get_json(session: requests.Session, url: str, params: Optional[dict] = None, timeout: int = 30) -> dict:
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


# -----------------------------
# Greenhouse
# Docs: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
# -----------------------------
def fetch_greenhouse_jobs(session: requests.Session, company: str, board_token: str, include_content: bool = True) -> List[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    params = {"content": "true"} if include_content else None
    data = get_json(session, url, params=params)

    jobs: List[Job] = []
    for j in data.get("jobs", []):
        jobs.append(
            Job(
                company=company,
                source="greenhouse",
                id=str(j.get("id", "")),
                title=j.get("title", "") or "",
                location=(j.get("location") or {}).get("name", "") or "",
                team=None,
                department=None,
                workplace_type=None,
                is_remote=None,
                updated_at=j.get("updated_at"),
                job_url=j.get("absolute_url", "") or "",
                apply_url=None,
                description_plain=_strip_basic_html_entities(j.get("content")) if include_content else None,
            )
        )
    return jobs


def _strip_basic_html_entities(text: Optional[str]) -> Optional[str]:
    # Greenhouse "content" may be HTML-entity encoded; keep it simple (you can improve later).
    if not text:
        return None
    return (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
    )


# -----------------------------
# Ashby
# Docs: GET https://api.ashbyhq.com/posting-api/job-board/{JOB_BOARD_NAME}?includeCompensation=true
# -----------------------------
def fetch_ashby_jobs(session: requests.Session, company: str, job_board_name: str, include_comp: bool = False) -> List[Job]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{job_board_name}"
    params = {"includeCompensation": "true"} if include_comp else None
    data = get_json(session, url, params=params)

    jobs: List[Job] = []
    for j in data.get("jobs", []):
        jobs.append(
            Job(
                company=company,
                source="ashby",
                id=str(j.get("jobUrl", "")).rsplit("/", 1)[-1] or j.get("title", ""),
                title=j.get("title", "") or "",
                location=j.get("location", "") or "",
                team=j.get("team"),
                department=j.get("department"),
                workplace_type=j.get("workplaceType"),
                is_remote=j.get("isRemote"),
                updated_at=j.get("publishedAt"),
                job_url=j.get("jobUrl", "") or "",
                apply_url=j.get("applyUrl"),
                description_plain=j.get("descriptionPlain"),
            )
        )
    return jobs


# -----------------------------
# Lever
# Docs: GET /v0/postings/SITE?skip=X&limit=Y&mode=json
# Base: https://api.lever.co/v0/postings/  (global)
# -----------------------------
def fetch_lever_jobs(
    session: requests.Session,
    company: str,
    site: str,
    limit: int = 100,
    sleep_s: float = 0.2,
    instance: str = "global",  # "global" | "eu"
) -> List[Job]:
    base = "https://api.lever.co/v0/postings/" if instance == "global" else "https://api.eu.lever.co/v0/postings/"
    jobs: List[Job] = []

    skip = 0
    while True:
        url = f"{base}{site}"
        params = {"skip": skip, "limit": limit, "mode": "json"}
        batch = get_json(session, url, params=params)

        if not isinstance(batch, list) or len(batch) == 0:
            break

        for j in batch:
            categories = j.get("categories") or {}
            jobs.append(
                Job(
                    company=company,
                    source="lever",
                    id=j.get("id", "") or "",
                    title=j.get("text", "") or "",
                    location=categories.get("location", "") or "",
                    team=categories.get("team"),
                    department=categories.get("department"),
                    workplace_type=(j.get("workplaceType") or None),
                    is_remote=(True if (j.get("workplaceType") == "remote") else None),
                    updated_at=str(j.get("createdAt")) if j.get("createdAt") is not None else None,
                    job_url=j.get("hostedUrl", "") or "",
                    apply_url=j.get("applyUrl"),
                    description_plain=j.get("descriptionPlain"),
                )
            )

        skip += len(batch)
        time.sleep(sleep_s)

    return jobs


# -----------------------------
# Config: add more companies here
# -----------------------------
COMPANIES: List[Dict[str, Any]] = [
    # OpenAI uses Ashby (job board name appears in jobs.ashbyhq.com/openai/...)
    {"company": "OpenAI", "source": "ashby", "job_board_name": "openai"},

    # Greenhouse examples
    {"company": "Anthropic", "source": "greenhouse", "board_token": "anthropic"},
    {"company": "xAI", "source": "greenhouse", "board_token": "xai"},
    {"company": "Airbnb", "source": "greenhouse", "board_token": "airbnb"},

    # Example Lever entry (replace with a real Lever site name)
    # {"company": "ExampleLeverCo", "source": "lever", "site": "leverdemo"},
]


def run_all(out_json: str, out_csv: Optional[str] = None, include_comp: bool = False) -> List[Job]:
    session = make_session()
    all_jobs: List[Job] = []

    for c in COMPANIES:
        src = c["source"].lower()
        company = c["company"]

        try:
            if src == "greenhouse":
                jobs = fetch_greenhouse_jobs(session, company, c["board_token"], include_content=True)
            elif src == "ashby":
                jobs = fetch_ashby_jobs(session, company, c["job_board_name"], include_comp=include_comp)
            elif src == "lever":
                jobs = fetch_lever_jobs(session, company, c["site"], instance=c.get("instance", "global"))
            else:
                print(f"[skip] Unknown source for {company}: {src}")
                continue

            print(f"[ok] {company}: {len(jobs)} jobs")
            all_jobs.extend(jobs)

        except requests.HTTPError as e:
            print(f"[error] {company} ({src}) HTTP error: {e}")
        except Exception as e:
            print(f"[error] {company} ({src}) unexpected error: {e}")

    # Write JSON
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump([asdict(j) for j in all_jobs], f, ensure_ascii=False, indent=2)
    print(f"[saved] {out_json} ({len(all_jobs)} total jobs)")

    # Write CSV (optional)
    if out_csv:
        write_csv(out_csv, all_jobs)
        print(f"[saved] {out_csv}")

    return all_jobs


def write_csv(path: str, jobs: List[Job]) -> None:
    fieldnames = list(asdict(Job(
        company="", source="", id="", title="", location="", team=None, department=None,
        workplace_type=None, is_remote=None, updated_at=None, job_url="", apply_url=None,
        description_plain=None
    )).keys())

    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for j in jobs:
            w.writerow(asdict(j))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="jobs.json", help="Output JSON file path")
    ap.add_argument("--csv", default=None, help="Optional output CSV file path")
    ap.add_argument("--include-comp", action="store_true", help="Ashby only: include compensation if available")
    args = ap.parse_args()

    run_all(out_json=args.out, out_csv=args.csv, include_comp=args.include_comp)


if __name__ == "__main__":
    main()
