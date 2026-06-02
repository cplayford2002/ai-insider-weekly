"""
Writing Agent
Uses Claude to draft the weekly newsletter and SEO blog posts.
Automatically weaves in affiliate links where contextually appropriate.
"""

import re
import json
import logging
from datetime import datetime
from pathlib import Path

from openai import OpenAI

log = logging.getLogger("writing_agent")

NEWSLETTER_SYSTEM = """You are the editor of 'AI Insider Weekly', a sharp, practical newsletter 
for professionals and solopreneurs who want to use AI to work smarter.

Voice: conversational but substantive — like a well-read friend who happens to be an AI expert. 
No hype. No fluff. Specific, actionable, occasionally witty.
Format: plain text with minimal markdown (readers see this in email).
Never use the phrase "game-changer" or "revolutionary"."""

BLOG_SYSTEM = """You are writing SEO-optimised blog posts for 'AI Insider Weekly'.
Voice: authoritative, practical, well-structured. Written for a professional audience.
Format: markdown with proper H2/H3 headings, short paragraphs, bullet lists where helpful.
Each post should be comprehensive enough to rank — aim for 800-1200 words."""


class WritingAgent:
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.affiliate_tools = config.get("affiliate_tools", [])
        self.newsletter_name = config.get("newsletter_name", "AI Insider Weekly")
        self.issue_number = self._get_next_issue_number()

    def write_newsletter(self, topics: list[dict]) -> dict:
        """Draft a full newsletter issue from curated topics."""
        affiliate_block = self._build_affiliate_context(topics)
        topics_text = "\n\n".join(
            f"TOPIC {i+1}: {t['title']}\n{t['summary']}\nSource: {t['source']} — {t['url']}"
            for i, t in enumerate(topics)
        )

        prompt = f"""Write Issue #{self.issue_number} of {self.newsletter_name}.

TODAY'S TOPICS:
{topics_text}

{affiliate_block}

STRUCTURE (follow exactly):
1. Subject line — punchy, curiosity-driven, max 50 chars (write as: SUBJECT: ...)
2. Preview text — 90 chars max (write as: PREVIEW: ...)
3. Opening hook — 2-3 sentences, no greeting, drop the reader straight into a compelling observation
4. Main stories — for each topic: a short bold headline, 2-3 paragraphs, a "→ Read more" link
5. This week's tool spotlight — pick ONE affiliate tool that genuinely helps with the week's themes.
   Write 3-4 sentences on WHY it's useful (not an ad — an honest recommendation). 
   Include the affiliate link naturally.
6. Quick wins — 3 bullet points: actionable AI tips readers can use TODAY
7. Closing — 2 sentences, warm but not sappy. Sign off as "— The AI Insider Team"

Write the full newsletter now:"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=3000,
            messages=[
                {"role": "system", "content": NEWSLETTER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content

        subject = self._extract_field(raw, "SUBJECT")
        preview = self._extract_field(raw, "PREVIEW")
        body = re.sub(r"^(SUBJECT|PREVIEW):[^\n]+\n?", "", raw, flags=re.MULTILINE).strip()

        return {
            "issue_number": self.issue_number,
            "subject": subject or f"AI Insider Weekly #{self.issue_number}",
            "preview": preview or "Your weekly dose of practical AI",
            "body": body,
            "generated_at": datetime.utcnow().isoformat(),
            "topics_count": len(topics),
        }

    def write_blog_post(self, topic: dict) -> dict:
        """Write a full SEO blog post for a single topic."""
        affiliate_hint = ""
        if topic.get("affiliate_angle"):
            tool = self._find_affiliate_tool(topic["affiliate_angle"])
            if tool:
                affiliate_hint = (
                    f"\nNaturally mention {tool['name']} once in the article where relevant. "
                    f"Use this link: {tool['affiliate_url']}. Make it read as a genuine recommendation."
                )

        prompt = f"""Write a comprehensive blog post based on this topic:

TITLE IDEA: {topic['title']}
SUMMARY: {topic['summary']}
SOURCE: {topic['url']}
{affiliate_hint}

Requirements:
- Compelling H1 title (SEO-friendly, includes primary keyword)
- Introduction that hooks the reader and states what they'll learn
- 4-6 H2 sections covering: what it is, why it matters, practical applications, 
  step-by-step guidance or examples, potential downsides/caveats
- Conclusion with clear takeaway
- Meta description (write as META: at the very end, 155 chars max)
- Target keyword phrase (write as KEYWORD: at the very end)

Write the full post now:"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2500,
            messages=[
                {"role": "system", "content": BLOG_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content

        meta = self._extract_field(raw, "META")
        keyword = self._extract_field(raw, "KEYWORD")
        body = re.sub(r"^(META|KEYWORD):[^\n]+\n?", "", raw, flags=re.MULTILINE).strip()

        # Extract H1 title
        h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = h1_match.group(1) if h1_match else topic["title"]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

        return {
            "title": title,
            "slug": slug,
            "body_markdown": body,
            "meta_description": meta or topic["summary"][:155],
            "target_keyword": keyword or topic["title"],
            "source_topic": topic,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ── Helpers ──────────────────────────────────────────────────

    def _build_affiliate_context(self, topics: list[dict]) -> str:
        if not self.affiliate_tools:
            return ""
        relevant = []
        for t in topics:
            if t.get("affiliate_angle"):
                tool = self._find_affiliate_tool(t["affiliate_angle"])
                if tool:
                    relevant.append(tool)
        if not relevant:
            relevant = self.affiliate_tools[:1]  # default to first tool
        lines = [f"AFFILIATE TOOLS AVAILABLE (use ONE naturally):"]
        for tool in relevant:
            lines.append(f"- {tool['name']}: {tool['description']} | Link: {tool['affiliate_url']}")
        return "\n".join(lines)

    def _find_affiliate_tool(self, name: str) -> dict | None:
        name_lower = name.lower()
        for tool in self.affiliate_tools:
            if name_lower in tool["name"].lower():
                return tool
        return None

    def _extract_field(self, text: str, field: str) -> str:
        match = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _get_next_issue_number(self) -> int:
        counter_path = Path("../config/issue_counter.json")
        if counter_path.exists():
            with open(counter_path) as f:
                data = json.load(f)
            n = data.get("current", 0) + 1
        else:
            n = 1
        counter_path.parent.mkdir(exist_ok=True)
        with open(counter_path, "w") as f:
            json.dump({"current": n}, f)
        return n
