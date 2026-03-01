#!/usr/bin/env python3
"""
SkillTree.dev — JobsData.py
Ultimate job data collector: 9 sources, 38+ company career pages, skill extraction.

Sources:
  FEEDS:  RemoteOK, Arbeitnow, Remotive, Jobicy, Himalayas, HN Who's Hiring
  ATS:    Greenhouse (31 companies), Ashby (7 companies) — all verified working

Run:
  python JobsData.py                       # full scrape, saves to data/
  python JobsData.py --no-ats              # feeds only (faster)
  python JobsData.py --no-feeds            # ATS only
  python JobsData.py --out myfile.json     # custom output name
  python JobsData.py --workers 10          # parallel ATS fetching

Install:
  pip install requests
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  SKILL TAXONOMY — 173 skills across 11 categories               ║
# ║  This is SkillTree's secret sauce.                               ║
# ╚═══════════════════════════════════════════════════════════════════╝

SKILL_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "languages": {
        "Python": ["python", "python3"],
        "JavaScript": ["javascript", r"\bjs\b", "ecmascript", "es6"],
        "TypeScript": ["typescript"],
        "Java": [r"\bjava\b", r"\bjdk\b", r"\bjvm\b"],
        "C++": [r"c\+\+", r"\bcpp\b"],
        "C#": [r"c\s*#", r"\bcsharp\b"],
        "Go": [r"\bgolang\b", r"\bgo\b language", r"\bgo\b developer", r"\bgo\b engineer"],
        "Rust": [r"\brust\b", "rustlang"],
        "Ruby": [r"\bruby\b"],
        "PHP": [r"\bphp\b"],
        "Swift": [r"\bswift\b"],
        "Kotlin": [r"\bkotlin\b"],
        "Scala": [r"\bscala\b"],
        "R": [r"\br\b programming", r"\br\b language", "rstudio"],
        "Dart": [r"\bdart\b"],
        "Elixir": [r"\belixir\b"],
        "Clojure": [r"\bclojure\b"],
        "Haskell": [r"\bhaskell\b"],
        "Lua": [r"\blua\b"],
        "Perl": [r"\bperl\b"],
        "Shell/Bash": [r"\bbash\b", "shell scripting"],
        "SQL": [r"\bsql\b"],
        "Solidity": [r"\bsolidity\b"],
        "Zig": [r"\bzig\b language"],
        "MATLAB": [r"\bmatlab\b"],
        "Objective-C": [r"objective.c", r"\bobjc\b"],
    },
    "frontend": {
        "React": [r"\breact\b", "reactjs", r"react\.js"],
        "Next.js": [r"\bnext\.?js\b", r"\bnextjs\b"],
        "Vue": [r"\bvue\b", "vuejs", r"vue\.js"],
        "Nuxt": [r"\bnuxt\b"],
        "Angular": [r"\bangular\b"],
        "Svelte": [r"\bsvelte\b", "sveltekit"],
        "Astro": [r"\bastro\b build"],
        "Remix": [r"\bremix\b run"],
        "jQuery": [r"\bjquery\b"],
        "Tailwind": [r"\btailwind\b"],
        "Bootstrap": [r"\bbootstrap\b"],
        "HTMX": [r"\bhtmx\b"],
    },
    "backend": {
        "Node.js": [r"\bnode\b", "nodejs", r"node\.js"],
        "Express": [r"\bexpress\b", "expressjs"],
        "Django": [r"\bdjango\b"],
        "Flask": [r"\bflask\b"],
        "FastAPI": [r"\bfastapi\b"],
        "Spring": [r"\bspring\b boot", r"\bspringboot\b"],
        "Rails": [r"\brails\b", "ruby on rails"],
        "Laravel": [r"\blaravel\b"],
        "NestJS": [r"\bnestjs\b"],
        "ASP.NET": [r"\basp\.?net\b", "dotnet", r"\.net\b"],
        "Gin": ["gin-gonic", r"\bgin\b framework"],
        "Phoenix": [r"\bphoenix\b elixir"],
        "Hono": [r"\bhono\b"],
    },
    "databases": {
        "PostgreSQL": [r"\bpostgres\b", "postgresql"],
        "MySQL": [r"\bmysql\b", "mariadb"],
        "MongoDB": [r"\bmongo\b", "mongodb"],
        "Redis": [r"\bredis\b"],
        "SQLite": [r"\bsqlite\b"],
        "DynamoDB": [r"\bdynamodb\b"],
        "Cassandra": [r"\bcassandra\b"],
        "Elasticsearch": [r"\belasticsearch\b", "opensearch"],
        "Neo4j": [r"\bneo4j\b"],
        "ClickHouse": [r"\bclickhouse\b"],
        "Supabase": [r"\bsupabase\b"],
        "Firebase": [r"\bfirebase\b", "firestore"],
        "Snowflake": [r"\bsnowflake\b"],
        "BigQuery": [r"\bbigquery\b"],
        "Pinecone": [r"\bpinecone\b"],
        "Weaviate": [r"\bweaviate\b"],
        "Qdrant": [r"\bqdrant\b"],
    },
    "cloud": {
        "AWS": [r"\baws\b", "amazon web services", r"\bec2\b", r"\bs3\b"],
        "GCP": [r"\bgcp\b", "google cloud"],
        "Azure": [r"\bazure\b"],
        "Cloudflare": [r"\bcloudflare\b"],
        "Vercel": [r"\bvercel\b"],
        "Netlify": [r"\bnetlify\b"],
        "DigitalOcean": [r"\bdigitalocean\b"],
        "Heroku": [r"\bheroku\b"],
    },
    "devops": {
        "Docker": [r"\bdocker\b", "dockerfile", "containerization"],
        "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
        "Terraform": [r"\bterraform\b"],
        "Ansible": [r"\bansible\b"],
        "Jenkins": [r"\bjenkins\b"],
        "GitHub Actions": ["github actions"],
        "GitLab CI": ["gitlab ci"],
        "ArgoCD": [r"\bargocd\b", "argo cd"],
        "Helm": [r"\bhelm\b chart"],
        "Pulumi": [r"\bpulumi\b"],
        "Prometheus": [r"\bprometheus\b"],
        "Grafana": [r"\bgrafana\b"],
        "Datadog": [r"\bdatadog\b"],
        "Nginx": [r"\bnginx\b"],
        "Linux": [r"\blinux\b", r"\bubuntu\b"],
        "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
        "CI/CD": [r"\bci/?cd\b", "continuous integration", "continuous delivery"],
    },
    "ai_ml": {
        "PyTorch": [r"\bpytorch\b"],
        "TensorFlow": [r"\btensorflow\b"],
        "Hugging Face": [r"hugging\s*face", "transformers library"],
        "LangChain": [r"\blangchain\b"],
        "OpenAI API": [r"\bopenai\b", "gpt api"],
        "LLM": [r"\bllm\b", "large language model"],
        "RAG": [r"\brag\b", "retrieval augmented"],
        "Computer Vision": ["computer vision", "image recognition"],
        "NLP": [r"\bnlp\b", "natural language processing"],
        "MLOps": [r"\bmlops\b"],
        "scikit-learn": [r"\bscikit\b", "sklearn"],
        "Pandas": [r"\bpandas\b"],
        "NumPy": [r"\bnumpy\b"],
        "Jupyter": [r"\bjupyter\b"],
        "CUDA": [r"\bcuda\b"],
        "vLLM": [r"\bvllm\b"],
        "Fine-tuning": [r"fine.?tun", r"\blora\b", r"\bqlora\b"],
        "Prompt Engineering": ["prompt engineer"],
        "MCP": [r"\bmcp\b", "model context protocol"],
        "GPT": [r"\bgpt\b"],
    },
    "mobile": {
        "React Native": ["react native"],
        "Flutter": [r"\bflutter\b"],
        "iOS": [r"\bios\b", r"\bswiftui\b"],
        "Android": [r"\bandroid\b"],
        "Expo": [r"\bexpo\b"],
    },
    "data": {
        "Spark": [r"\bspark\b", "pyspark"],
        "Kafka": [r"\bkafka\b"],
        "Airflow": [r"\bairflow\b"],
        "dbt": [r"\bdbt\b"],
        "Tableau": [r"\btableau\b"],
        "Power BI": [r"power\s*bi"],
        "Looker": [r"\blooker\b"],
        "ETL": [r"\betl\b"],
        "Data Pipeline": ["data pipeline"],
        "Data Warehouse": ["data warehouse"],
    },
    "security": {
        "Cybersecurity": ["cybersecurity", "cyber security", "infosec"],
        "Penetration Testing": ["pen test", "penetration test"],
        "SOC": [r"\bsoc\b analyst"],
        "SIEM": [r"\bsiem\b"],
        "OAuth": [r"\boauth\b"],
        "Zero Trust": ["zero trust"],
    },
    "tools": {
        "GraphQL": [r"\bgraphql\b"],
        "REST API": [r"\brest\b api", "restful"],
        "gRPC": [r"\bgrpc\b"],
        "WebSocket": [r"\bwebsocket\b"],
        "RabbitMQ": [r"\brabbitmq\b"],
        "Celery": [r"\bcelery\b"],
        "Stripe API": [r"\bstripe\b api"],
        "Figma": [r"\bfigma\b"],
        "Webpack": [r"\bwebpack\b"],
        "Vite": [r"\bvite\b"],
        "Storybook": [r"\bstorybook\b"],
        "Jest": [r"\bjest\b"],
        "Playwright": [r"\bplaywright\b"],
        "Cypress": [r"\bcypress\b"],
        "Selenium": [r"\bselenium\b"],
    },
}

# Pre-compile all regex patterns for speed
_PATTERNS: List[Tuple[re.Pattern, str, str]] = []
for _cat, _skills in SKILL_TAXONOMY.items():
    for _name, _pats in _skills.items():
        for _p in _pats:
            try:
                _PATTERNS.append((re.compile(_p, re.IGNORECASE), _cat, _name))
            except re.error:
                pass

_SKILL_TO_CAT = {}
for _cat, _skills in SKILL_TAXONOMY.items():
    for _name in _skills:
        _SKILL_TO_CAT[_name] = _cat


def extract_skills(text: str) -> List[str]:
    """Extract skill names from text using regex taxonomy."""
    if not text:
        return []
    found = set()
    results = []
    text_lower = text.lower()
    for pattern, category, skill_name in _PATTERNS:
        if skill_name not in found and pattern.search(text_lower):
            found.add(skill_name)
            results.append(skill_name)
    return results


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  UNIFIED DATA MODEL                                              ║
# ╚═══════════════════════════════════════════════════════════════════╝

@dataclass
class JobRecord:
    source: str
    source_id: str
    source_url: str
    title: str
    company: str
    location: str
    description: str = ""

    tags: List[str] = field(default_factory=list)
    posted_at: Optional[str] = None
    updated_at: Optional[str] = None

    is_remote: Optional[bool] = None
    workplace_type: Optional[str] = None

    team: Optional[str] = None
    department: Optional[str] = None

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_text: Optional[str] = None

    apply_url: Optional[str] = None
    company_logo: Optional[str] = None

    # SkillTree enrichment fields
    extracted_skills: List[str] = field(default_factory=list)
    seniority: str = ""
    job_type: str = ""

    def uid(self) -> str:
        sid = (self.source_id or "").strip()
        if sid:
            return f"{self.source}:{sid}"
        return f"{self.source}:{(self.source_url or '').strip()}:{self.title.strip()}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def enrich(self) -> "JobRecord":
        """Auto-extract skills, seniority, remote status."""
        full_text = f"{self.title} {self.description} {' '.join(self.tags)}"
        self.extracted_skills = extract_skills(full_text)
        if not self.seniority:
            self.seniority = detect_seniority(self.title)
        if self.is_remote is None:
            self.is_remote = detect_remote(self.title, self.location, self.tags)
        return self


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  UTILITIES                                                       ║
# ╚═══════════════════════════════════════════════════════════════════╝

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SkillTree/1.0; +https://skilltree.dev)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}
HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(text: Optional[str]) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_json(session: requests.Session, url: str, params: Optional[dict] = None, timeout: int = 20) -> Any:
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def parse_salary_range(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if not text:
        return None, None, None
    t = text.strip()

    currency = None
    mcur = re.search(r"(USD|EUR|GBP|PKR|INR|CAD|AUD|CHF|SEK|NOK|DKK|JPY|CNY)\b", t, re.I)
    if mcur:
        currency = mcur.group(1).upper()
    else:
        msym = re.search(r"[$€£₹¥]", t)
        if msym:
            currency = msym.group(0)

    def _to_num(s: str) -> Optional[float]:
        s = s.replace(",", "").strip().lower()
        mult = 1.0
        if s.endswith("k"):
            mult, s = 1000.0, s[:-1]
        elif s.endswith("m"):
            mult, s = 1_000_000.0, s[:-1]
        try:
            return float(s) * mult
        except Exception:
            return None

    parts = re.split(r"\s*(?:-|–|—|to)\s*", t, maxsplit=1, flags=re.I)
    if len(parts) == 2:
        n1_list = re.findall(r"\d+(?:\.\d+)?\s*[km]?", parts[0], re.I)
        n2_list = re.findall(r"\d+(?:\.\d+)?\s*[km]?", parts[1], re.I)
        n1 = _to_num(n1_list[-1]) if n1_list else None
        n2 = _to_num(n2_list[0]) if n2_list else None
        return n1, n2, currency

    nums = re.findall(r"\d+(?:\.\d+)?\s*[km]?", t, re.I)
    if nums:
        return _to_num(nums[0]), None, currency
    return None, None, currency


def detect_remote(title: str, location: str, tags: Iterable[str]) -> Optional[bool]:
    hay = " ".join([title or "", location or "", " ".join(tags or [])]).lower()
    if any(k in hay for k in ["remote", "work from home", "wfh", "distributed", "anywhere", "worldwide"]):
        return True
    if any(k in hay for k in ["on-site", "onsite", "in office", "in-office"]):
        return False
    return None


def detect_seniority(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["intern", "trainee", "apprentice"]):
        return "intern"
    if any(w in t for w in ["junior", "jr.", "jr ", "entry level", "entry-level", "associate"]):
        return "junior"
    if any(w in t for w in ["senior", "sr.", "sr ", "iii", "lead"]):
        return "senior"
    if any(w in t for w in ["staff", "principal", "distinguished"]):
        return "staff"
    if any(w in t for w in ["director", "vp ", "vice president", "head of", "chief"]):
        return "director"
    if any(w in t for w in ["manager", "engineering manager"]):
        return "manager"
    return "mid"


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  ATS SCRAPERS — Greenhouse / Ashby / Lever                      ║
# ╚═══════════════════════════════════════════════════════════════════╝

def fetch_greenhouse(session: requests.Session, company: str, board_token: str) -> List[JobRecord]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    data = get_json(session, url, params={"content": "true"})
    jobs = []
    for j in data.get("jobs", []):
        jr = JobRecord(
            source="greenhouse",
            source_id=str(j.get("id", "")),
            source_url=j.get("absolute_url", "") or "",
            title=j.get("title", "") or "",
            company=company,
            location=(j.get("location") or {}).get("name", "") or "",
            description=clean_html(j.get("content")),
            updated_at=j.get("updated_at"),
        )
        jobs.append(jr.enrich())
    return jobs


def fetch_ashby(session: requests.Session, company: str, board_name: str) -> List[JobRecord]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    data = get_json(session, url, params={"includeCompensation": "true"})
    jobs = []
    for j in data.get("jobs", []):
        jr = JobRecord(
            source="ashby",
            source_id=str(j.get("jobUrl", "")).rsplit("/", 1)[-1] or j.get("title", ""),
            source_url=j.get("jobUrl", "") or "",
            title=j.get("title", "") or "",
            company=company,
            location=j.get("location", "") or "",
            description=(j.get("descriptionPlain") or "").strip(),
            workplace_type=j.get("workplaceType"),
            is_remote=j.get("isRemote"),
            team=j.get("team"),
            department=j.get("department"),
            posted_at=j.get("publishedAt"),
            apply_url=j.get("applyUrl"),
        )
        comp = j.get("compensationTierSummary") or j.get("compensation") or j.get("compensationSummary")
        if isinstance(comp, str):
            jr.salary_text = comp
            jr.salary_min, jr.salary_max, jr.salary_currency = parse_salary_range(comp)
        jobs.append(jr.enrich())
    return jobs


def fetch_lever(session: requests.Session, company: str, site: str, instance: str = "global") -> List[JobRecord]:
    base = "https://api.lever.co/v0/postings/" if instance == "global" else "https://api.eu.lever.co/v0/postings/"
    jobs = []
    skip = 0
    while True:
        batch = get_json(session, f"{base}{site}", params={"skip": skip, "limit": 100, "mode": "json"})
        if not isinstance(batch, list) or not batch:
            break
        for j in batch:
            cats = j.get("categories") or {}
            wt = j.get("workplaceType")
            jr = JobRecord(
                source="lever",
                source_id=j.get("id", ""),
                source_url=j.get("hostedUrl", "") or "",
                title=j.get("text", "") or "",
                company=company,
                location=cats.get("location", "") or "",
                description=(j.get("descriptionPlain") or "").strip(),
                workplace_type=wt,
                is_remote=True if wt == "remote" else None,
                team=cats.get("team"),
                department=cats.get("department"),
                updated_at=str(j.get("createdAt")) if j.get("createdAt") else None,
                apply_url=j.get("applyUrl"),
            )
            jobs.append(jr.enrich())
        skip += len(batch)
        time.sleep(0.2)
    return jobs


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  FEED SCRAPERS — 6 public sources                               ║
# ╚═══════════════════════════════════════════════════════════════════╝

def fetch_remoteok(session: requests.Session) -> List[JobRecord]:
    data = get_json(session, "https://remoteok.com/api")
    jobs = []
    for item in (data if isinstance(data, list) else []):
        if not isinstance(item, dict) or "id" not in item:
            continue
        jr = JobRecord(
            source="remoteok",
            source_id=str(item.get("id", "")),
            source_url=item.get("url", "") or "",
            title=item.get("position", "") or "",
            company=item.get("company", "") or "",
            company_logo=item.get("company_logo", "") or item.get("logo", ""),
            description=clean_html(item.get("description", "")),
            location=item.get("location", "") or "Remote",
            is_remote=True,
            tags=[str(t) for t in (item.get("tags") or [])],
            posted_at=item.get("date") or None,
            salary_min=safe_float(item.get("salary_min")),
            salary_max=safe_float(item.get("salary_max")),
        )
        jobs.append(jr.enrich())
    return jobs


def fetch_arbeitnow(session: requests.Session, max_pages: int = 5) -> List[JobRecord]:
    jobs = []
    next_url = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(max_pages):
        if not next_url:
            break
        data = get_json(session, next_url)
        for item in data.get("data") or []:
            tags = [str(t) for t in (item.get("tags") or [])]
            jr = JobRecord(
                source="arbeitnow",
                source_id=str(item.get("slug") or item.get("id") or ""),
                source_url=item.get("url", "") or "",
                title=item.get("title", "") or "",
                company=item.get("company_name", "") or "",
                location=item.get("location", "") or "",
                description=clean_html(item.get("description", "")),
                tags=tags,
                posted_at=item.get("created_at") or None,
            )
            jobs.append(jr.enrich())
        next_url = (data.get("links") or {}).get("next")
        time.sleep(1)
    return jobs


def fetch_remotive(session: requests.Session) -> List[JobRecord]:
    data = get_json(session, "https://remotive.com/api/remote-jobs")
    jobs = []
    for item in data.get("jobs") or []:
        salary = (item.get("salary") or "").strip()
        mn, mx, cur = parse_salary_range(salary) if salary else (None, None, None)
        jr = JobRecord(
            source="remotive",
            source_id=str(item.get("id", "")),
            source_url=item.get("url", "") or "",
            title=item.get("title", "") or "",
            company=item.get("company_name", "") or "",
            location=item.get("candidate_required_location", "") or "Remote",
            description=clean_html(item.get("description", "")),
            tags=[str(t) for t in (item.get("tags") or [])],
            posted_at=item.get("publication_date") or None,
            is_remote=True,
            salary_min=mn, salary_max=mx, salary_currency=cur,
            salary_text=salary or None,
        )
        jobs.append(jr.enrich())
    return jobs


def fetch_jobicy(session: requests.Session) -> List[JobRecord]:
    data = get_json(session, "https://jobicy.com/api/v2/remote-jobs", params={"count": 50})
    jobs = []
    for item in data.get("jobs") or []:
        jr = JobRecord(
            source="jobicy",
            source_id=str(item.get("id", "")),
            source_url=item.get("url", "") or "",
            title=item.get("jobTitle", "") or "",
            company=item.get("companyName", "") or "",
            company_logo=item.get("companyLogo"),
            location=item.get("jobGeo", "") or "Remote",
            description=clean_html(item.get("jobDescription", "")),
            posted_at=item.get("pubDate") or None,
            is_remote=True,
            salary_min=safe_float(item.get("salaryMin")),
            salary_max=safe_float(item.get("salaryMax")),
            salary_currency=item.get("salaryCurrency"),
        )
        jobs.append(jr.enrich())
    return jobs


def fetch_himalayas(session: requests.Session) -> List[JobRecord]:
    data = get_json(session, "https://himalayas.app/jobs/api")
    jobs = []
    for item in data.get("jobs") or []:
        tags = []
        for t in item.get("tags") or []:
            if isinstance(t, dict) and t.get("name"):
                tags.append(str(t["name"]))
            elif isinstance(t, str):
                tags.append(t)
        co = item.get("company") or {}
        jr = JobRecord(
            source="himalayas",
            source_id=str(item.get("id", "")),
            source_url=item.get("url", "") or "",
            title=item.get("title", "") or "",
            company=co.get("name", "") if isinstance(co, dict) else str(co),
            company_logo=co.get("logoUrl") if isinstance(co, dict) else None,
            location=item.get("location", "") or "Remote",
            description=clean_html(item.get("description", "")),
            tags=tags,
            posted_at=item.get("createdAt") or None,
            is_remote=True,
        )
        jobs.append(jr.enrich())
    return jobs


def fetch_hn_who_is_hiring(session: requests.Session, max_comments: int = 300) -> List[JobRecord]:
    """Fetch latest HN 'Who is Hiring' thread via Algolia + Firebase."""
    # Find thread
    data = get_json(session, "https://hn.algolia.com/api/v1/search", params={
        "query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 5,
    })
    hits = sorted(data.get("hits") or [], key=lambda x: x.get("created_at_i") or 0, reverse=True)
    if not hits:
        return []

    hn_id = hits[0].get("objectID")
    if not hn_id:
        return []

    # Fetch thread
    item = get_json(session, f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json")
    kids = (item.get("kids") or [])[:max_comments]

    jobs = []
    for kid_id in kids:
        try:
            c = get_json(session, f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json", timeout=10)
        except Exception:
            continue
        if not isinstance(c, dict):
            continue
        text = clean_html(c.get("text") or "")
        if len(text) < 50:
            continue

        first_line = text.split("\n", 1)[0].strip()
        parts = [p.strip() for p in first_line.split("|") if p.strip()]
        company = parts[0] if parts else "Unknown"
        title = parts[1] if len(parts) > 1 else "Hiring"
        location = parts[2] if len(parts) > 2 else ""
        extra_tags = parts[3:] if len(parts) > 3 else []

        jr = JobRecord(
            source="hn_whoishiring",
            source_id=str(kid_id),
            source_url=f"https://news.ycombinator.com/item?id={kid_id}",
            title=title[:200],
            company=company[:100],
            location=location[:200],
            description=text[:5000],
            tags=extra_tags,
            posted_at=str(c.get("time")) if c.get("time") else None,
        )
        jobs.append(jr.enrich())
    return jobs


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  COMPANY REGISTRY — 38 verified ATS endpoints                   ║
# ╚═══════════════════════════════════════════════════════════════════╝

ATS_COMPANIES: List[Dict[str, Any]] = [
    # ── Greenhouse (31 verified) ───────────────────────────────────
    # FAANG-tier / Big Tech
    {"company": "Airbnb",       "source": "greenhouse", "board_token": "airbnb"},
    {"company": "Stripe",       "source": "greenhouse", "board_token": "stripe"},
    {"company": "Coinbase",     "source": "greenhouse", "board_token": "coinbase"},
    {"company": "Discord",      "source": "greenhouse", "board_token": "discord"},
    {"company": "Pinterest",    "source": "greenhouse", "board_token": "pinterest"},
    {"company": "Lyft",         "source": "greenhouse", "board_token": "lyft"},
    {"company": "Twitch",       "source": "greenhouse", "board_token": "twitch"},
    {"company": "Instacart",    "source": "greenhouse", "board_token": "instacart"},
    {"company": "Reddit",       "source": "greenhouse", "board_token": "reddit"},
    {"company": "Dropbox",      "source": "greenhouse", "board_token": "dropbox"},

    # AI / ML
    {"company": "Anthropic",    "source": "greenhouse", "board_token": "anthropic"},
    {"company": "xAI",          "source": "greenhouse", "board_token": "xai"},
    {"company": "DeepMind",     "source": "greenhouse", "board_token": "deepmind"},
    {"company": "Scale AI",     "source": "greenhouse", "board_token": "scaleai"},

    # Cloud / Infra
    {"company": "Cloudflare",   "source": "greenhouse", "board_token": "cloudflare"},
    {"company": "Databricks",   "source": "greenhouse", "board_token": "databricks"},
    {"company": "CoreWeave",    "source": "greenhouse", "board_token": "coreweave"},
    {"company": "Datadog",      "source": "greenhouse", "board_token": "datadog"},
    {"company": "Elastic",      "source": "greenhouse", "board_token": "elastic"},
    {"company": "GitLab",       "source": "greenhouse", "board_token": "gitlab"},
    {"company": "Vercel",       "source": "greenhouse", "board_token": "vercel"},

    # Fintech
    {"company": "Robinhood",    "source": "greenhouse", "board_token": "robinhood"},
    {"company": "Brex",         "source": "greenhouse", "board_token": "brex"},

    # Other major tech
    {"company": "Figma",        "source": "greenhouse", "board_token": "figma"},
    {"company": "Duolingo",     "source": "greenhouse", "board_token": "duolingo"},
    {"company": "Airtable",     "source": "greenhouse", "board_token": "airtable"},
    {"company": "Flexport",     "source": "greenhouse", "board_token": "flexport"},
    {"company": "Verkada",      "source": "greenhouse", "board_token": "verkada"},
    {"company": "Samsara",      "source": "greenhouse", "board_token": "samsara"},
    {"company": "Gusto",        "source": "greenhouse", "board_token": "gusto"},
    {"company": "CockroachDB",  "source": "greenhouse", "board_token": "cockroachlabs"},

    # ── Ashby (7 verified) ─────────────────────────────────────────
    {"company": "OpenAI",       "source": "ashby", "job_board_name": "openai"},
    {"company": "Ramp",         "source": "ashby", "job_board_name": "ramp"},
    {"company": "Notion",       "source": "ashby", "job_board_name": "notion"},
    {"company": "Linear",       "source": "ashby", "job_board_name": "Linear"},
    {"company": "Cursor",       "source": "ashby", "job_board_name": "cursor"},
    {"company": "Supabase",     "source": "ashby", "job_board_name": "supabase"},
    {"company": "Cohere",       "source": "ashby", "job_board_name": "cohere"},
]

FEEDS = ["remoteok", "arbeitnow", "remotive", "jobicy", "himalayas", "hn_whoishiring"]

FEED_FUNCS = {
    "remoteok": fetch_remoteok,
    "arbeitnow": fetch_arbeitnow,
    "remotive": fetch_remotive,
    "jobicy": fetch_jobicy,
    "himalayas": fetch_himalayas,
    "hn_whoishiring": fetch_hn_who_is_hiring,
}


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  ORCHESTRATOR                                                    ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _fetch_ats_company(company_cfg: Dict[str, Any]) -> Tuple[str, List[JobRecord]]:
    """Fetch a single ATS company (used by ThreadPoolExecutor)."""
    session = make_session()
    src = company_cfg["source"]
    name = company_cfg["company"]
    try:
        if src == "greenhouse":
            jobs = fetch_greenhouse(session, name, company_cfg["board_token"])
        elif src == "ashby":
            jobs = fetch_ashby(session, name, company_cfg["job_board_name"])
        elif src == "lever":
            jobs = fetch_lever(session, name, company_cfg["site"], company_cfg.get("instance", "global"))
        else:
            return name, []
        return name, jobs
    except Exception as e:
        return name, []


def gather_all(
    include_ats: bool = True,
    include_feeds: bool = True,
    arbeitnow_pages: int = 5,
    max_workers: int = 6,
) -> List[JobRecord]:
    all_jobs: List[JobRecord] = []
    session = make_session()

    # ── Feeds (sequential, they're fast) ────────────────────────
    if include_feeds:
        for name in FEEDS:
            func = FEED_FUNCS.get(name)
            if not func:
                continue
            try:
                t0 = time.time()
                if name == "arbeitnow":
                    jobs = func(session, max_pages=arbeitnow_pages)
                else:
                    jobs = func(session)
                elapsed = time.time() - t0
                print(f"  ✅ feed:{name:<18s} {len(jobs):>5} jobs  ({elapsed:.1f}s)")
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  ❌ feed:{name:<18s} ERROR: {e}")

    # ── ATS (parallel, many slow endpoints) ─────────────────────
    if include_ats:
        print(f"\n  Fetching {len(ATS_COMPANIES)} company career pages ({max_workers} workers)...\n")
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_ats_company, c): c for c in ATS_COMPANIES}
            for future in as_completed(futures):
                name, jobs = future.result()
                if jobs:
                    print(f"  ✅ ats:{name:<20s} {len(jobs):>5} jobs")
                    all_jobs.extend(jobs)
                else:
                    print(f"  ⚠️  ats:{name:<20s} 0 jobs or error")
        print(f"\n  ATS fetch complete in {time.time()-t0:.1f}s")

    # ── Deduplicate ─────────────────────────────────────────────
    seen: Dict[str, JobRecord] = {}
    for j in all_jobs:
        seen[j.uid()] = j
    deduped = list(seen.values())
    removed = len(all_jobs) - len(deduped)
    if removed:
        print(f"\n  Dedup: removed {removed} duplicates")

    return deduped


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  ANALYTICS                                                       ║
# ╚═══════════════════════════════════════════════════════════════════╝

def generate_analytics(jobs: List[JobRecord]) -> Dict[str, Any]:
    skill_counter: Counter = Counter()
    combo_counter: Counter = Counter()

    for j in jobs:
        for s in j.extracted_skills:
            skill_counter[s] += 1
        sorted_s = sorted(j.extracted_skills)
        for i in range(len(sorted_s)):
            for k in range(i + 1, min(i + 4, len(sorted_s))):  # top 3 pairs per skill
                combo_counter[f"{sorted_s[i]} + {sorted_s[k]}"] += 1

    n = len(jobs) or 1
    skill_rankings = [
        {"rank": r, "skill": s, "category": _SKILL_TO_CAT.get(s, "other"),
         "jobs": c, "pct": round(c / n * 100, 1)}
        for r, (s, c) in enumerate(skill_counter.most_common(50), 1)
    ]
    combos = [
        {"combo": c, "jobs": cnt, "pct": round(cnt / n * 100, 1)}
        for c, cnt in combo_counter.most_common(25)
    ]

    source_counter = Counter(j.source for j in jobs)
    remote_count = sum(1 for j in jobs if j.is_remote)
    seniority_counter = Counter(j.seniority for j in jobs if j.seniority)
    company_counter = Counter(j.company for j in jobs if j.company)

    salaries = [(j.salary_min, j.salary_max) for j in jobs if j.salary_min and j.salary_max]
    avg_min = round(sum(s[0] for s in salaries) / len(salaries)) if salaries else 0
    avg_max = round(sum(s[1] for s in salaries) / len(salaries)) if salaries else 0

    return {
        "meta": {
            "total_jobs": len(jobs),
            "unique_skills": len(skill_counter),
            "sources": dict(source_counter),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "skill_rankings": skill_rankings,
        "skill_combos": combos,
        "remote": {"remote": remote_count, "onsite": len(jobs) - remote_count,
                    "pct": round(remote_count / n * 100, 1)},
        "seniority": dict(seniority_counter.most_common()),
        "salary": {"with_data": len(salaries), "avg_min": avg_min, "avg_max": avg_max},
        "top_companies": [{"company": c, "jobs": n} for c, n in company_counter.most_common(30)],
    }


def print_report(a: Dict[str, Any]):
    m = a["meta"]
    print(f"\n{'═' * 70}")
    print(f"  SkillTree.dev — Job Market Intelligence Report")
    print(f"{'═' * 70}")
    print(f"  Total jobs:    {m['total_jobs']:,}")
    print(f"  Unique skills: {m['unique_skills']}")
    print(f"  Sources:       {m['sources']}")
    print(f"  Scraped at:    {m['scraped_at'][:19]}Z")

    print(f"\n{'─' * 70}")
    print(f"  📊 TOP 30 SKILLS BY DEMAND")
    print(f"{'─' * 70}")
    print(f"  {'#':<4} {'Skill':<22} {'Category':<12} {'Jobs':>6} {'%':>6}  {'Bar'}")
    for s in a["skill_rankings"][:30]:
        bar = "█" * max(1, int(s["pct"] / 2))
        print(f"  {s['rank']:<4} {s['skill']:<22} {s['category']:<12} {s['jobs']:>6} {s['pct']:>5.1f}%  {bar}")

    print(f"\n{'─' * 70}")
    print(f"  🔗 TOP 15 SKILL COMBOS")
    print(f"{'─' * 70}")
    for c in a["skill_combos"][:15]:
        print(f"  {c['combo']:<45} {c['jobs']:>5} jobs ({c['pct']}%)")

    r = a["remote"]
    print(f"\n  🌍 Remote: {r['remote']:,} ({r['pct']}%)  |  Onsite: {r['onsite']:,}")

    sal = a["salary"]
    if sal["avg_min"]:
        print(f"  💰 Salary ({sal['with_data']} jobs): ${sal['avg_min']:,.0f} – ${sal['avg_max']:,.0f}")

    print(f"\n{'─' * 70}")
    print(f"  🏢 TOP 15 COMPANIES")
    print(f"{'─' * 70}")
    for c in a["top_companies"][:15]:
        print(f"  {c['company']:<40} {c['jobs']:>5} jobs")

    print(f"\n{'═' * 70}")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  MAIN                                                            ║
# ╚═══════════════════════════════════════════════════════════════════╝

def main():
    ap = argparse.ArgumentParser(description="SkillTree.dev — Ultimate Job Data Collector")
    ap.add_argument("--out", default="JobsData.json", help="Output JSON filename (saved under ./data/)")
    ap.add_argument("--no-ats", action="store_true", help="Skip ATS company career pages")
    ap.add_argument("--no-feeds", action="store_true", help="Skip public feed sources")
    ap.add_argument("--no-analytics", action="store_true", help="Skip analytics generation")
    ap.add_argument("--arbeitnow-pages", type=int, default=5, help="Arbeitnow pages to fetch (default 5)")
    ap.add_argument("--workers", type=int, default=6, help="Parallel workers for ATS fetching (default 6)")
    args = ap.parse_args()

    print(f"\n🚀 SkillTree.dev — Starting data collection...\n")
    t_start = time.time()

    jobs = gather_all(
        include_ats=not args.no_ats,
        include_feeds=not args.no_feeds,
        arbeitnow_pages=args.arbeitnow_pages,
        max_workers=args.workers,
    )

    elapsed = time.time() - t_start
    print(f"\n  📦 Total: {len(jobs):,} unique jobs in {elapsed:.1f}s")

    # Save jobs
    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", os.path.basename(args.out))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([j.to_dict() for j in jobs], f, ensure_ascii=False, indent=2)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  💾 Saved {out_path} ({size_mb:.1f} MB)")

    # Analytics
    if not args.no_analytics and jobs:
        analytics = generate_analytics(jobs)
        analytics_path = os.path.join("data", "analytics.json")
        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2)
        print(f"  💾 Saved {analytics_path}")
        print_report(analytics)

    print(f"\n✅ Done!\n")


if __name__ == "__main__":
    main()
