"""
Scraper module — adapted from JobsData.py.
Contains all data-fetching logic; no Django imports here so it can be
tested standalone.  Django persistence lives in tasks.py.
"""
from __future__ import annotations

import html
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

# ─────────────────────────────────────────────────────────────────────
# SKILL TAXONOMY
# ─────────────────────────────────────────────────────────────────────

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

# Pre-compile patterns
_PATTERNS: List[Tuple[re.Pattern, str, str]] = []
for _cat, _skills in SKILL_TAXONOMY.items():
    for _name, _pats in _skills.items():
        for _p in _pats:
            try:
                _PATTERNS.append((re.compile(_p, re.IGNORECASE), _cat, _name))
            except re.error:
                pass

_SKILL_TO_CAT: Dict[str, str] = {}
for _cat, _skills in SKILL_TAXONOMY.items():
    for _name in _skills:
        _SKILL_TO_CAT[_name] = _cat


def extract_skills(text: str) -> List[str]:
    if not text:
        return []
    found: set = set()
    results = []
    text_lower = text.lower()
    for pattern, category, skill_name in _PATTERNS:
        if skill_name not in found and pattern.search(text_lower):
            found.add(skill_name)
            results.append(skill_name)
    return results


# ─────────────────────────────────────────────────────────────────────
# DATA MODEL (plain dataclass — no Django dependency)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ScrapedJob:
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
    extracted_skills: List[str] = field(default_factory=list)
    seniority: str = ""
    job_type: str = ""

    def uid(self) -> str:
        sid = (self.source_id or "").strip()
        if sid:
            return f"{self.source}:{sid}"
        return f"{self.source}:{(self.source_url or '').strip()}:{self.title.strip()}"

    def enrich(self) -> "ScrapedJob":
        full_text = f"{self.title} {self.description} {' '.join(self.tags)}"
        self.extracted_skills = extract_skills(full_text)
        if not self.seniority:
            self.seniority = detect_seniority(self.title)
        if self.is_remote is None:
            self.is_remote = detect_remote(self.title, self.location, self.tags)
        return self


# ─────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────
# ATS SCRAPERS
# ─────────────────────────────────────────────────────────────────────

def fetch_greenhouse(session: requests.Session, company: str, board_token: str) -> List[ScrapedJob]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    data = get_json(session, url, params={"content": "true"})
    jobs = []
    for j in data.get("jobs", []):
        jr = ScrapedJob(
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


def fetch_ashby(session: requests.Session, company: str, board_name: str) -> List[ScrapedJob]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    data = get_json(session, url, params={"includeCompensation": "true"})
    jobs = []
    for j in data.get("jobs", []):
        jr = ScrapedJob(
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


def fetch_lever(session: requests.Session, company: str, site: str, instance: str = "global") -> List[ScrapedJob]:
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
            jr = ScrapedJob(
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


# ─────────────────────────────────────────────────────────────────────
# FEED SCRAPERS
# ─────────────────────────────────────────────────────────────────────

def fetch_remoteok(session: requests.Session) -> List[ScrapedJob]:
    data = get_json(session, "https://remoteok.com/api")
    jobs = []
    for item in (data if isinstance(data, list) else []):
        if not isinstance(item, dict) or "id" not in item:
            continue
        jr = ScrapedJob(
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


def fetch_arbeitnow(session: requests.Session, max_pages: int = 5) -> List[ScrapedJob]:
    jobs = []
    next_url: Optional[str] = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(max_pages):
        if not next_url:
            break
        data = get_json(session, next_url)
        for item in data.get("data") or []:
            tags = [str(t) for t in (item.get("tags") or [])]
            jr = ScrapedJob(
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


def fetch_remotive(session: requests.Session) -> List[ScrapedJob]:
    data = get_json(session, "https://remotive.com/api/remote-jobs")
    jobs = []
    for item in data.get("jobs") or []:
        salary = (item.get("salary") or "").strip()
        mn, mx, cur = parse_salary_range(salary) if salary else (None, None, None)
        jr = ScrapedJob(
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


def fetch_jobicy(session: requests.Session) -> List[ScrapedJob]:
    data = get_json(session, "https://jobicy.com/api/v2/remote-jobs", params={"count": 50})
    jobs = []
    for item in data.get("jobs") or []:
        jr = ScrapedJob(
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


def fetch_himalayas(session: requests.Session) -> List[ScrapedJob]:
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
        jr = ScrapedJob(
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


def _fetch_hn_comment(kid_id: int) -> Optional[dict]:
    """Fetch a single HN comment — used in parallel by fetch_hn_who_is_hiring."""
    try:
        s = make_session()
        return get_json(s, f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json", timeout=5)
    except Exception:
        return None


def fetch_hn_who_is_hiring(session: requests.Session, max_comments: int = 75) -> List[ScrapedJob]:
    """Fetch HN 'Who is Hiring' thread. Comments are fetched in parallel (10 workers)."""
    data = get_json(session, "https://hn.algolia.com/api/v1/search", params={
        "query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 5,
    })
    hits = sorted(data.get("hits") or [], key=lambda x: x.get("created_at_i") or 0, reverse=True)
    if not hits:
        return []
    hn_id = hits[0].get("objectID")
    if not hn_id:
        return []

    item = get_json(session, f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json")
    kids = (item.get("kids") or [])[:max_comments]

    # Fetch all comments in parallel — much faster than sequential
    with ThreadPoolExecutor(max_workers=10) as pool:
        comments = list(pool.map(_fetch_hn_comment, kids))

    jobs = []
    for c in comments:
        if not c or not isinstance(c, dict):
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
        jr = ScrapedJob(
            source="hn_whoishiring",
            source_id=str(c.get("id", "")),
            source_url=f"https://news.ycombinator.com/item?id={c.get('id','')}",
            title=title[:200],
            company=company[:100],
            location=location[:200],
            description=text[:5000],
            tags=extra_tags,
            posted_at=str(c.get("time")) if c.get("time") else None,
        )
        jobs.append(jr.enrich())
    return jobs


# ─────────────────────────────────────────────────────────────────────
# CUSTOM COMPANY SCRAPERS (FAANG / proprietary ATS)
# ─────────────────────────────────────────────────────────────────────

def fetch_amazon(session: requests.Session, max_pages: int = 5) -> List[ScrapedJob]:
    """Amazon Jobs API — paginates via offset, 20 results per page."""
    jobs = []
    result_limit = 20
    for page in range(max_pages):
        offset = page * result_limit
        try:
            data = get_json(session, "https://www.amazon.jobs/en/search.json", params={
                "result_limit": result_limit,
                "offset": offset,
                "normalized_country_code[]": "USA",
            })
        except Exception as e:
            print(f"  [amazon] page {page}: {e}")
            break
        hits = data.get("jobs") or data.get("hits") or []
        for j in hits:
            job_path = j.get("job_path", "") or ""
            cat = j.get("category") or {}
            dept = cat.get("label") if isinstance(cat, dict) else None
            jr = ScrapedJob(
                source="amazon",
                source_id=str(j.get("id_icims") or j.get("id", "")),
                source_url=f"https://www.amazon.jobs{job_path}" if job_path else "",
                title=j.get("title", "") or "",
                company="Amazon",
                location=j.get("location", "") or "",
                description=clean_html(j.get("description_short") or j.get("description") or ""),
                department=j.get("business_category") or dept,
                posted_at=j.get("posted_date") or None,
            )
            jobs.append(jr.enrich())
        if len(hits) < result_limit:
            break
        time.sleep(0.5)
    return jobs


def fetch_google(session: requests.Session, max_pages: int = 5) -> List[ScrapedJob]:
    """Google Careers API — paginates via page param."""
    jobs = []
    for page in range(1, max_pages + 1):
        try:
            data = get_json(session, "https://careers.google.com/api/jobs/", params={
                "page_size": 20,
                "page": page,
                "q": "",
                "location": "United States",
                "sort_by": "relevance",
            })
        except Exception as e:
            print(f"  [google] page {page}: {e}")
            break
        job_list = data.get("jobs") or []
        for j in job_list:
            locs = j.get("locations") or []
            loc_str = ", ".join(locs) if isinstance(locs, list) else str(locs)
            apply_url = j.get("apply_url") or ""
            jr = ScrapedJob(
                source="google",
                source_id=str(j.get("id") or apply_url),
                source_url=apply_url,
                title=j.get("title", "") or "",
                company="Google",
                location=loc_str,
                description=clean_html(j.get("description") or ""),
                posted_at=j.get("publish_date") or None,
            )
            jobs.append(jr.enrich())
        if not job_list:
            break
        time.sleep(0.5)
    return jobs


def fetch_meta(session: requests.Session, max_pages: int = 5) -> List[ScrapedJob]:
    """Meta Careers API — GET endpoint with offset pagination."""
    jobs = []
    results_per_page = 20
    for page in range(max_pages):
        offset = page * results_per_page
        try:
            data = get_json(session, "https://www.metacareers.com/v2/jobs/", params={
                "results_per_page": results_per_page,
                "offset": offset,
                "location[]": "USA",
            })
        except Exception as e:
            print(f"  [meta] page {page}: {e}")
            break
        job_list = data.get("data") or []
        for j in job_list:
            jid = str(j.get("id", ""))
            jr = ScrapedJob(
                source="meta",
                source_id=jid,
                source_url=j.get("apply_url") or (f"https://www.metacareers.com/jobs/{jid}" if jid else ""),
                title=j.get("title", "") or "",
                company="Meta",
                location=j.get("location") or "",
                description=clean_html(j.get("description") or ""),
                department=j.get("team_name") or None,
                posted_at=j.get("post_date") or None,
            )
            jobs.append(jr.enrich())
        if len(job_list) < results_per_page:
            break
        time.sleep(0.5)
    return jobs


def fetch_apple(session: requests.Session, max_pages: int = 5) -> List[ScrapedJob]:
    """Apple Jobs API — POST-based search with offset pagination."""
    jobs = []
    limit = 20
    for page in range(max_pages):
        offset = page * limit
        payload = {
            "filters": {"postingpostLocation": ["post-location-USA"]},
            "limit": limit,
            "offset": offset,
        }
        try:
            r = session.post(
                "https://jobs.apple.com/api/role/search",
                json=payload,
                timeout=20,
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  [apple] page {page}: {e}")
            break
        job_list = data.get("searchResults") or []
        for j in job_list:
            role_id = j.get("positionId") or j.get("id") or ""
            locs = j.get("locations") or []
            loc_name = locs[0].get("name", "") if locs and isinstance(locs[0], dict) else ""
            team = j.get("team") or {}
            jr = ScrapedJob(
                source="apple",
                source_id=str(role_id),
                source_url=f"https://jobs.apple.com/en-us/details/{role_id}" if role_id else "",
                title=j.get("postingTitle") or j.get("title") or "",
                company="Apple",
                location=loc_name,
                description=clean_html(j.get("jobSummary") or ""),
                team=team.get("teamName") if isinstance(team, dict) else None,
                posted_at=j.get("postDateValue") or None,
            )
            jobs.append(jr.enrich())
        if len(job_list) < limit:
            break
        time.sleep(0.5)
    return jobs


# ─────────────────────────────────────────────────────────────────────
# COMPANY REGISTRY
# ─────────────────────────────────────────────────────────────────────

ATS_COMPANIES: List[Dict[str, Any]] = [
    # ── Greenhouse (confirmed working) ────────────────────────────────
    # Social / Consumer
    {"company": "Airbnb",           "source": "greenhouse", "board_token": "airbnb"},
    {"company": "Reddit",           "source": "greenhouse", "board_token": "reddit"},
    {"company": "Discord",          "source": "greenhouse", "board_token": "discord"},
    {"company": "Pinterest",        "source": "greenhouse", "board_token": "pinterest"},
    {"company": "Twitch",           "source": "greenhouse", "board_token": "twitch"},
    {"company": "Duolingo",         "source": "greenhouse", "board_token": "duolingo"},
    # Fintech / Commerce
    {"company": "Stripe",           "source": "greenhouse", "board_token": "stripe"},
    {"company": "Coinbase",         "source": "greenhouse", "board_token": "coinbase"},
    {"company": "Robinhood",        "source": "greenhouse", "board_token": "robinhood"},
    {"company": "Brex",             "source": "greenhouse", "board_token": "brex"},
    {"company": "Gusto",            "source": "greenhouse", "board_token": "gusto"},
    {"company": "Instacart",        "source": "greenhouse", "board_token": "instacart"},
    {"company": "Lyft",             "source": "greenhouse", "board_token": "lyft"},
    {"company": "Chime",            "source": "greenhouse", "board_token": "chime"},
    {"company": "Carta",            "source": "greenhouse", "board_token": "carta"},
    {"company": "Faire",            "source": "greenhouse", "board_token": "faire"},
    {"company": "Lattice",          "source": "greenhouse", "board_token": "lattice"},
    # AI / ML
    {"company": "Anthropic",        "source": "greenhouse", "board_token": "anthropic"},
    {"company": "xAI",              "source": "greenhouse", "board_token": "xai"},
    {"company": "DeepMind",         "source": "greenhouse", "board_token": "deepmind"},
    {"company": "Scale AI",         "source": "greenhouse", "board_token": "scaleai"},
    {"company": "CoreWeave",        "source": "greenhouse", "board_token": "coreweave"},
    {"company": "Waymo",            "source": "greenhouse", "board_token": "waymo"},
    # Infrastructure / Cloud / DevTools
    {"company": "Cloudflare",       "source": "greenhouse", "board_token": "cloudflare"},
    {"company": "Databricks",       "source": "greenhouse", "board_token": "databricks"},
    {"company": "Datadog",          "source": "greenhouse", "board_token": "datadog"},
    {"company": "Elastic",          "source": "greenhouse", "board_token": "elastic"},
    {"company": "MongoDB",          "source": "greenhouse", "board_token": "mongodb"},
    {"company": "CockroachDB",      "source": "greenhouse", "board_token": "cockroachlabs"},
    {"company": "PagerDuty",        "source": "greenhouse", "board_token": "pagerduty"},
    {"company": "Twilio",           "source": "greenhouse", "board_token": "twilio"},
    {"company": "Okta",             "source": "greenhouse", "board_token": "okta"},
    {"company": "GitLab",           "source": "greenhouse", "board_token": "gitlab"},
    {"company": "Amplitude",        "source": "greenhouse", "board_token": "amplitude"},
    # Design / Productivity
    {"company": "Figma",            "source": "greenhouse", "board_token": "figma"},
    {"company": "Airtable",         "source": "greenhouse", "board_token": "airtable"},
    {"company": "Asana",            "source": "greenhouse", "board_token": "asana"},
    {"company": "Webflow",          "source": "greenhouse", "board_token": "webflow"},
    {"company": "Grammarly",        "source": "greenhouse", "board_token": "grammarly"},
    {"company": "Dropbox",          "source": "greenhouse", "board_token": "dropbox"},
    {"company": "Calendly",         "source": "greenhouse", "board_token": "calendly"},
    # Hardware / Security / Other
    {"company": "Vercel",           "source": "greenhouse", "board_token": "vercel"},
    {"company": "Verkada",          "source": "greenhouse", "board_token": "verkada"},
    {"company": "Samsara",          "source": "greenhouse", "board_token": "samsara"},
    {"company": "Flexport",         "source": "greenhouse", "board_token": "flexport"},
    {"company": "Intercom",         "source": "greenhouse", "board_token": "intercom"},
    # Navan (formerly TripActions) confirmed working:
    {"company": "Navan",            "source": "greenhouse", "board_token": "tripactions"},
    # Additional Greenhouse companies
    {"company": "Netflix",          "source": "greenhouse", "board_token": "netflix"},
    {"company": "Shopify",          "source": "greenhouse", "board_token": "shopify"},
    {"company": "HubSpot",          "source": "greenhouse", "board_token": "hubspot"},
    {"company": "Zendesk",          "source": "greenhouse", "board_token": "zendesk"},
    {"company": "Box",              "source": "greenhouse", "board_token": "box"},
    {"company": "DocuSign",         "source": "greenhouse", "board_token": "docusign"},
    {"company": "Squarespace",      "source": "greenhouse", "board_token": "squarespace"},
    {"company": "Quora",            "source": "greenhouse", "board_token": "quora"},

    # ── Ashby (confirmed working) ─────────────────────────────────────
    # AI / LLM
    # AI / LLM (confirmed working)
    {"company": "OpenAI",           "source": "ashby", "job_board_name": "openai"},
    {"company": "ElevenLabs",       "source": "ashby", "job_board_name": "elevenlabs"},
    {"company": "Runway",           "source": "ashby", "job_board_name": "runway"},
    {"company": "Harvey",           "source": "ashby", "job_board_name": "harvey"},
    {"company": "Cohere",           "source": "ashby", "job_board_name": "cohere"},
    {"company": "Pika",             "source": "ashby", "job_board_name": "pika"},
    # Developer tools / infra (confirmed working)
    {"company": "Ramp",             "source": "ashby", "job_board_name": "ramp"},
    {"company": "Notion",           "source": "ashby", "job_board_name": "notion"},
    {"company": "Linear",           "source": "ashby", "job_board_name": "Linear"},
    {"company": "Cursor",           "source": "ashby", "job_board_name": "cursor"},
    {"company": "Supabase",         "source": "ashby", "job_board_name": "supabase"},
    {"company": "PostHog",          "source": "ashby", "job_board_name": "posthog"},
    {"company": "Warp",             "source": "ashby", "job_board_name": "warp"},
    {"company": "Resend",           "source": "ashby", "job_board_name": "resend"},
    {"company": "Replit",           "source": "ashby", "job_board_name": "replit"},
    {"company": "Vanta",            "source": "ashby", "job_board_name": "vanta"},
    # Additional Ashby companies
    {"company": "Mistral",          "source": "ashby", "job_board_name": "mistralai"},
    {"company": "Perplexity",       "source": "ashby", "job_board_name": "perplexityai"},
    {"company": "Character.ai",     "source": "ashby", "job_board_name": "characterai"},
    {"company": "Together AI",      "source": "ashby", "job_board_name": "togetherai"},
    {"company": "Glean",            "source": "ashby", "job_board_name": "glean"},
    {"company": "Hugging Face",     "source": "ashby", "job_board_name": "huggingface"},
]

FEEDS = [
    "remoteok", "arbeitnow", "remotive", "jobicy", "himalayas", "hn_whoishiring",
    "amazon", "google", "meta", "apple",
]

FEED_FUNCS = {
    "remoteok": fetch_remoteok,
    "arbeitnow": fetch_arbeitnow,
    "remotive": fetch_remotive,
    "jobicy": fetch_jobicy,
    "himalayas": fetch_himalayas,
    "hn_whoishiring": fetch_hn_who_is_hiring,
    "amazon": fetch_amazon,
    "google": fetch_google,
    "meta": fetch_meta,
    "apple": fetch_apple,
}


def _fetch_ats_company(company_cfg: Dict[str, Any]) -> Tuple[str, List[ScrapedJob]]:
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
        print(f"  [ATS] {name}: {e}")
        return name, []


def gather_all(
    include_ats: bool = True,
    include_feeds: bool = True,
    arbeitnow_pages: int = 5,
    max_workers: int = 6,
) -> List[ScrapedJob]:
    all_jobs: List[ScrapedJob] = []
    session = make_session()

    if include_feeds:
        # Each feed gets its own session so they can run in parallel safely
        def _run_feed(name: str) -> Tuple[str, List[ScrapedJob], float]:
            func = FEED_FUNCS.get(name)
            if not func:
                return name, [], 0.0
            t0 = time.time()
            s = make_session()
            if name == "arbeitnow":
                result = func(s, max_pages=arbeitnow_pages)
            else:
                result = func(s)
            return name, result, time.time() - t0

        print(f"\n  Fetching {len(FEEDS)} feeds in parallel...\n")
        with ThreadPoolExecutor(max_workers=len(FEEDS)) as pool:
            feed_futures = {pool.submit(_run_feed, name): name for name in FEEDS}
            for future in as_completed(feed_futures):
                try:
                    name, jobs, elapsed = future.result()
                    print(f"  feed:{name:<18s} {len(jobs):>5} jobs  ({elapsed:.1f}s)")
                    all_jobs.extend(jobs)
                except Exception as e:
                    name = feed_futures[future]
                    print(f"  feed:{name:<18s} ERROR: {e}")

    if include_ats:
        print(f"\n  Fetching {len(ATS_COMPANIES)} company career pages ({max_workers} workers)...\n")
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_fetch_ats_company, c): c for c in ATS_COMPANIES}
            for future in as_completed(futures):
                name, jobs = future.result()
                if jobs:
                    print(f"  ats:{name:<20s} {len(jobs):>5} jobs")
                    all_jobs.extend(jobs)
                else:
                    print(f"  ats:{name:<20s} 0 jobs or error")

    # Deduplicate by uid
    seen: Dict[str, ScrapedJob] = {}
    for j in all_jobs:
        seen[j.uid()] = j
    return list(seen.values())


# ─────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────

def generate_analytics(jobs: List[ScrapedJob]) -> Dict[str, Any]:
    skill_counter: Counter = Counter()
    combo_counter: Counter = Counter()

    # company -> {skill: count}
    company_skill_counter: Dict[str, Counter] = {}

    for j in jobs:
        for s in j.extracted_skills:
            skill_counter[s] += 1
        sorted_s = sorted(j.extracted_skills)
        for i in range(len(sorted_s)):
            for k in range(i + 1, min(i + 4, len(sorted_s))):
                combo_counter[f"{sorted_s[i]} + {sorted_s[k]}"] += 1
        if j.company and j.extracted_skills:
            if j.company not in company_skill_counter:
                company_skill_counter[j.company] = Counter()
            for s in j.extracted_skills:
                company_skill_counter[j.company][s] += 1

    n = len(jobs) or 1
    skill_rankings = [
        {
            "rank": r,
            "skill": s,
            "category": _SKILL_TO_CAT.get(s, "other"),
            "jobs": c,
            "pct": round(c / n * 100, 1),
        }
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

    top_companies = [
        {
            "company": c,
            "jobs": cnt,
            "topSkill": company_skill_counter.get(c, Counter()).most_common(1)[0][0]
            if company_skill_counter.get(c)
            else "",
        }
        for c, cnt in company_counter.most_common(30)
    ]

    return {
        "meta": {
            "total_jobs": len(jobs),
            "unique_skills": len(skill_counter),
            "sources": dict(source_counter),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "skill_rankings": skill_rankings,
        "skill_combos": combos,
        "remote": {
            "remote": remote_count,
            "onsite": len(jobs) - remote_count,
            "pct": round(remote_count / n * 100, 1),
        },
        "seniority": dict(seniority_counter.most_common()),
        "salary": {"with_data": len(salaries), "avg_min": avg_min, "avg_max": avg_max},
        "top_companies": top_companies,
    }
