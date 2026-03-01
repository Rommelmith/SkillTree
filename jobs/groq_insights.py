"""
groq_insights.py — generates AI market-intelligence insights via the Groq API
(llama-3.1-8b-instant model, fast + free tier).

Called once per scrape cycle from tasks.py.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# Fallback shown when Groq is unavailable
FALLBACK_INSIGHTS = [
    {"icon": "🔥", "title": "Hottest Skill", "text": "Python leads all tech job listings by a wide margin, appearing in more job descriptions than any other programming language.", "type": "hot"},
    {"icon": "📈", "title": "Rising Fast", "text": "LLM and OpenAI API skills are growing faster than any other category — AI integration is now a mainstream hiring requirement.", "type": "trend"},
    {"icon": "⚠️", "title": "Trend Watch", "text": "TypeScript is steadily replacing plain JavaScript in frontend and full-stack listings as teams standardise on typed codebases.", "type": "warn"},
    {"icon": "💰", "title": "Salary Insight", "text": "Jobs requiring cloud + AI skills (AWS/GCP + LLM) consistently command the highest compensation packages.", "type": "money"},
    {"icon": "🔮", "title": "Prediction", "text": "Based on current momentum, Go is on track to surpass Java in backend engineering listings within the next 12 months.", "type": "predict"},
    {"icon": "🏢", "title": "Company Intel", "text": "AI-focused companies are hiring at the fastest rate — OpenAI, Anthropic, and Cohere collectively account for a large share of AI/ML openings.", "type": "company"},
]


def generate_ai_insights(analytics: Dict[str, Any], api_key: str) -> List[Dict[str, Any]]:
    """
    Call Groq to generate 6 market-intelligence insights from analytics data.
    Returns FALLBACK_INSIGHTS on any failure.
    """
    if not api_key:
        return FALLBACK_INSIGHTS

    meta = analytics.get("meta", {})
    top_skills = analytics.get("skill_rankings", [])[:12]
    top_combos = analytics.get("skill_combos", [])[:5]
    top_companies = analytics.get("top_companies", [])[:8]
    remote = analytics.get("remote", {})
    salary = analytics.get("salary", {})
    seniority = analytics.get("seniority", {})

    prompt = f"""You are a senior tech job market analyst. Using ONLY the real data below, write 6 sharp, specific insights.

DATA ({meta.get('total_jobs', 0):,} live job listings):
Top skills: {', '.join(f"{s['skill']} {s['pct']}%" for s in top_skills)}
Top combos: {', '.join(f"{c['combo']} ({c['jobs']} jobs)" for c in top_combos)}
Top companies: {', '.join(f"{c['company']} ({c['jobs']} roles)" for c in top_companies)}
Remote: {remote.get('pct', 0)}% of listings
Salary (where listed): avg ${salary.get('avg_min', 0):,.0f}–${salary.get('avg_max', 0):,.0f}
Seniority mix: {dict(list(seniority.items())[:4])}

Return a JSON array of exactly 6 objects. Each object:
{{
  "icon": "<one emoji>",
  "title": "<2-4 word title>",
  "text": "<1-2 sentences with specific numbers from the data>",
  "type": "<one of: hot | trend | warn | money | predict | company>"
}}

Rules: be specific (use percentages, job counts, company names from the data). No generic advice.
Return ONLY the JSON array — no markdown, no explanation."""

    try:
        resp = requests.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "max_tokens": 1200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Robustly extract JSON array from the response
        match = re.search(r"\[.*\]", content, re.DOTALL)
        raw = match.group() if match else content
        insights = json.loads(raw)

        if isinstance(insights, list) and len(insights) >= 3:
            # Ensure required keys exist on each item
            valid = []
            for ins in insights[:6]:
                if isinstance(ins, dict) and "title" in ins and "text" in ins:
                    ins.setdefault("icon", "📊")
                    ins.setdefault("type", "trend")
                    valid.append(ins)
            if valid:
                logger.info("Generated %d AI insights via Groq", len(valid))
                return valid

    except Exception as e:
        logger.warning("Groq insights generation failed: %s", e)

    return FALLBACK_INSIGHTS
