"""
Research Agent
Scrapes trending AI topics from Reddit, Hacker News, and Product Hunt.
All sources are free — no paid API required.
"""

import re
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from openai import OpenAI

log = logging.getLogger("research_agent")

HEADERS = {"User-Agent": "AIInsiderWeekly/1.0 (newsletter research bot; contact via substack)"}

REDDIT_AI_SUBS = ["artificial", "MachineLearning", "ChatGPT", "singularity", "LocalLLaMA"]


class ResearchAgent:
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.affiliate_tools = config.get("affiliate_tools", [])

    # ── Public interface ─────────────────────────────────────────

    def get_trending_topics(self, n: int = 5) -> list[dict]:
        """Return n curated topic dicts, each with title, summary, source, url, relevance_score."""
        raw: list[dict] = []
        raw += self._fetch_hackernews()
        raw += self._fetch_reddit()
        raw += self._fetch_producthunt()

        log.info(f"Raw items collected: {len(raw)}")
        curated = self._curate_with_claude(raw, n)
        return curated

    # ── Data fetchers ────────────────────────────────────────────

    def _fetch_hackernews(self) -> list[dict]:
        items = []
        try:
            # HN Algolia API — completely free
            since = int((datetime.utcnow() - timedelta(days=3)).timestamp())
            url = (
                f"https://hn.algolia.com/api/v1/search?"
                f"query=AI+LLM+machine+learning&tags=story"
                f"&numericFilters=created_at_i>{since},points>30"
                f"&hitsPerPage=30"
            )
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                items.append({
                    "source": "HackerNews",
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "score": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                })
        except Exception as e:
            log.warning(f"HackerNews fetch failed: {e}")
        return items

    def _fetch_reddit(self) -> list[dict]:
        items = []
        for sub in REDDIT_AI_SUBS:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
                resp = requests.get(url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
                for post in resp.json()["data"]["children"]:
                    d = post["data"]
                    if d.get("score", 0) < 100:
                        continue
                    items.append({
                        "source": f"Reddit r/{sub}",
                        "title": d["title"],
                        "url": f"https://reddit.com{d['permalink']}",
                        "score": d["score"],
                        "comments": d["num_comments"],
                    })
                time.sleep(0.5)  # be polite
            except Exception as e:
                log.warning(f"Reddit r/{sub} fetch failed: {e}")
        return items

    def _fetch_producthunt(self) -> list[dict]:
        """Fetch top AI products from Product Hunt's public feed."""
        items = []
        try:
            url = "https://www.producthunt.com/feed"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            # Parse RSS titles — simple regex, no xml lib needed
            titles = re.findall(r"<title><!\[CDATA\[(.+?)]]></title>", resp.text)
            links = re.findall(r"<link>(.+?)</link>", resp.text)
            for title, link in zip(titles[1:], links[1:]):  # skip channel title
                if any(kw in title.lower() for kw in ["ai", "gpt", "llm", "claude", "copilot"]):
                    items.append({
                        "source": "ProductHunt",
                        "title": title,
                        "url": link,
                        "score": 50,
                        "comments": 0,
                    })
        except Exception as e:
            log.warning(f"ProductHunt fetch failed: {e}")
        return items

    # ── Claude curation ──────────────────────────────────────────

    def _curate_with_claude(self, raw: list[dict], n: int) -> list[dict]:
        """Use Claude to pick and summarise the most newsletter-worthy topics."""
        if not raw:
            log.warning("No raw items — returning empty list")
            return []

        affiliate_context = ""
        if self.affiliate_tools:
            names = ", ".join(t["name"] for t in self.affiliate_tools)
            affiliate_context = (
                f"\nBonus: if any topic naturally relates to these tools, "
                f"flag it — {names}. Do NOT force relevance."
            )

        prompt = f"""You are the research editor for 'AI Insider Weekly', a newsletter for 
professionals who want practical AI insights. 

From the list below, select the {n} most valuable topics for our readers. 
Prioritise: practical applications, tool releases, research breakthroughs, 
workflow tips. Avoid: hype, politics, sci-fi speculation.
{affiliate_context}

For each selected topic return a JSON object with:
- title: compelling newsletter-friendly headline (max 10 words)  
- summary: 2-sentence explanation of why this matters to readers
- source: original source name
- url: original url  
- relevance_score: 1-10
- affiliate_angle: name of affiliate tool IF naturally relevant, else null

Return ONLY a JSON array. No preamble.

RAW ITEMS:
{json.dumps(raw[:60], indent=2)}
"""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            topics = json.loads(text)
            log.info(f"Claude curated {len(topics)} topics")
            return topics[:n]
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse Claude curation response: {e}\nResponse: {text[:500]}")
            # Fallback: return top-n raw items
            return raw[:n]
