"""
Research Agent
Scrapes trending AI topics from HackerNews, ArXiv, TechCrunch RSS, and Product Hunt.
All sources are free and don't block automated requests.
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


class ResearchAgent:
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.affiliate_tools = config.get("affiliate_tools", [])

    # ── Public interface ─────────────────────────────────────────

    def get_trending_topics(self, n: int = 5) -> list[dict]:
        """Return n curated topic dicts."""
        raw: list[dict] = []
        raw += self._fetch_hackernews()
        raw += self._fetch_arxiv()
        raw += self._fetch_techcrunch()
        raw += self._fetch_producthunt()

        log.info(f"Raw items collected: {len(raw)}")
        if not raw:
            log.warning("No raw items found — using fallback topics")
            return self._fallback_topics(n)
        curated = self._curate_with_openai(raw, n)
        return curated

    # ── Data fetchers ────────────────────────────────────────────

    def _fetch_hackernews(self) -> list[dict]:
        items = []
        try:
            since = int((datetime.utcnow() - timedelta(days=3)).timestamp())
            url = (
                f"https://hn.algolia.com/api/v1/search?"
                f"query=AI+LLM+machine+learning+GPT&tags=story"
                f"&numericFilters=created_at_i>{since},points>20"
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
            log.info(f"HackerNews: {len(items)} items")
        except Exception as e:
            log.warning(f"HackerNews fetch failed: {e}")
        return items

    def _fetch_arxiv(self) -> list[dict]:
        """Fetch latest AI papers from ArXiv RSS — always works, never blocks."""
        items = []
        try:
            url = "https://rss.arxiv.org/rss/cs.AI"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            titles = re.findall(r"<title>(.*?)</title>", resp.text, re.DOTALL)
            links = re.findall(r"<link>(https://arxiv\.org/abs/\S+)</link>", resp.text)
            descriptions = re.findall(r"<description>(.*?)</description>", resp.text, re.DOTALL)
            for i, (title, link) in enumerate(zip(titles[1:16], links[:15])):
                title = re.sub(r"<[^>]+>", "", title).strip()
                desc = ""
                if i + 1 < len(descriptions):
                    desc = re.sub(r"<[^>]+>", "", descriptions[i + 1]).strip()[:200]
                if title:
                    items.append({
                        "source": "ArXiv CS.AI",
                        "title": title,
                        "url": link,
                        "score": 30,
                        "comments": 0,
                        "summary": desc,
                    })
            log.info(f"ArXiv: {len(items)} items")
        except Exception as e:
            log.warning(f"ArXiv fetch failed: {e}")
        return items

    def _fetch_techcrunch(self) -> list[dict]:
        """Fetch AI articles from TechCrunch RSS feed."""
        items = []
        try:
            url = "https://techcrunch.com/feed/"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            titles = re.findall(r"<title><!\[CDATA\[(.*?)]]></title>", resp.text)
            links = re.findall(r"<link>(https://techcrunch\.com/\S+)</link>", resp.text)
            for title, link in zip(titles, links):
                if any(kw in title.lower() for kw in ["ai", "openai", "anthropic", "gpt", "llm", "machine learning", "claude", "gemini"]):
                    items.append({
                        "source": "TechCrunch",
                        "title": title,
                        "url": link,
                        "score": 50,
                        "comments": 0,
                    })
            log.info(f"TechCrunch: {len(items)} items")
        except Exception as e:
            log.warning(f"TechCrunch fetch failed: {e}")
        return items

    def _fetch_producthunt(self) -> list[dict]:
        """Fetch top AI products from Product Hunt RSS."""
        items = []
        try:
            url = "https://www.producthunt.com/feed"
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            titles = re.findall(r"<title><!\[CDATA\[(.*?)]]></title>", resp.text)
            links = re.findall(r"<link>(.*?)</link>", resp.text)
            for title, link in zip(titles[1:], links[1:]):
                if any(kw in title.lower() for kw in ["ai", "gpt", "llm", "claude", "copilot", "automation"]):
                    items.append({
                        "source": "ProductHunt",
                        "title": title,
                        "url": link,
                        "score": 40,
                        "comments": 0,
                    })
            log.info(f"ProductHunt: {len(items)} items")
        except Exception as e:
            log.warning(f"ProductHunt fetch failed: {e}")
        return items

    def _fallback_topics(self, n: int) -> list[dict]:
        """Fallback topics if all sources fail."""
        return [
            {"title": "How AI agents are changing knowledge work", "summary": "A look at how autonomous AI agents are beginning to handle complex multi-step tasks that previously required human expertise.", "source": "AI Insider Weekly", "url": "https://aiinsiderweekly.substack.com", "relevance_score": 8, "affiliate_angle": "Perplexity AI"},
            {"title": "The best free AI tools for professionals in 2026", "summary": "Roundup of the most powerful AI tools available at no cost, and how to use them to save hours each week.", "source": "AI Insider Weekly", "url": "https://aiinsiderweekly.substack.com", "relevance_score": 9, "affiliate_angle": "Notion AI"},
            {"title": "Prompt engineering tips that actually work", "summary": "Practical techniques for getting better results from any AI model, based on what's working right now.", "source": "AI Insider Weekly", "url": "https://aiinsiderweekly.substack.com", "relevance_score": 8, "affiliate_angle": None},
            {"title": "AI for small business: what's worth the investment", "summary": "An honest assessment of which AI tools deliver real ROI for small teams and solopreneurs.", "source": "AI Insider Weekly", "url": "https://aiinsiderweekly.substack.com", "relevance_score": 7, "affiliate_angle": "Jasper AI"},
            {"title": "How to automate your workflow with AI in one afternoon", "summary": "Step-by-step guide to identifying and automating your most repetitive tasks using free AI tools.", "source": "AI Insider Weekly", "url": "https://aiinsiderweekly.substack.com", "relevance_score": 9, "affiliate_angle": None},
        ][:n]

    # ── OpenAI curation ──────────────────────────────────────────

    def _curate_with_openai(self, raw: list[dict], n: int) -> list[dict]:
        """Use GPT-4o to pick and summarise the most newsletter-worthy topics."""
        if not raw:
            return self._fallback_topics(n)

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

Return ONLY a JSON array. No preamble. No markdown fences.

RAW ITEMS:
{json.dumps(raw[:50], indent=2)}
"""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            topics = json.loads(text)
            log.info(f"GPT-4o curated {len(topics)} topics")
            return topics[:n]
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse curation response: {e}")
            return self._fallback_topics(n)
