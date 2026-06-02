"""
SEO Agent
Optimises blog posts for search: adds meta tags, improves headings,
inserts keywords naturally, and generates structured data.
Uses free DataForSEO sandbox or falls back to Claude-only analysis.
"""

import re
import json
import logging
from openai import OpenAI

log = logging.getLogger("seo_agent")


class SEOAgent:
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.site_url = config.get("site_url", "https://yourdomain.github.io")
        self.site_name = config.get("newsletter_name", "AI Insider Weekly")

    def optimise(self, post: dict) -> dict:
        """Run full SEO pass on a blog post dict."""
        log.info(f"SEO optimising: {post['title']}")

        # 1. Claude SEO analysis
        seo_data = self._claude_seo_analysis(post)

        # 2. Apply improvements to markdown body
        post["body_markdown"] = self._apply_seo_improvements(
            post["body_markdown"], seo_data, post
        )

        # 3. Build full front matter
        post["front_matter"] = self._build_front_matter(post, seo_data)

        # 4. Add structured data (JSON-LD)
        post["structured_data"] = self._build_structured_data(post)

        # 5. Store SEO metadata
        post["seo"] = seo_data

        log.info(f"SEO complete. Primary KW: '{seo_data.get('primary_keyword')}'")
        return post

    def _claude_seo_analysis(self, post: dict) -> dict:
        prompt = f"""Perform an SEO analysis for this blog post and return ONLY a JSON object.

TITLE: {post['title']}
TARGET KEYWORD: {post.get('target_keyword', '')}
META DESCRIPTION: {post.get('meta_description', '')}
BODY (first 1000 chars): {post['body_markdown'][:1000]}

Return JSON with these keys:
{{
  "primary_keyword": "the best 2-5 word keyword phrase to target",
  "secondary_keywords": ["3-5 related phrases"],
  "optimised_title": "SEO title tag (50-60 chars, includes primary keyword)",
  "optimised_meta": "Meta description (150-155 chars, includes keyword, has CTA)",
  "suggested_h2s": ["improved H2 headings that include keywords naturally"],
  "internal_link_opportunities": ["topics from our own site to link to"],
  "word_count_target": 900,
  "readability_notes": "one sentence on how to improve readability"
}}

Return ONLY the JSON object, no other text."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            log.warning("SEO JSON parse failed, using defaults")
            return {
                "primary_keyword": post.get("target_keyword", post["title"]),
                "secondary_keywords": [],
                "optimised_title": post["title"][:60],
                "optimised_meta": post.get("meta_description", "")[:155],
            }

    def _apply_seo_improvements(self, body: str, seo_data: dict, post: dict) -> str:
        """Apply SEO improvements to the markdown body."""
        # Update H1 title if Claude suggests a better one
        optimised_title = seo_data.get("optimised_title")
        if optimised_title:
            body = re.sub(r"^#\s+.+$", f"# {optimised_title}", body, count=1, flags=re.MULTILINE)

        # Ensure primary keyword appears in first 100 words
        kw = seo_data.get("primary_keyword", "")
        if kw and kw.lower() not in body[:500].lower():
            # Insert after the first paragraph
            paras = body.split("\n\n")
            if len(paras) > 1:
                paras[1] = paras[1] + f"\n\n*{kw.capitalize()} is at the centre of this week's analysis.*"
                body = "\n\n".join(paras)

        return body

    def _build_front_matter(self, post: dict, seo_data: dict) -> dict:
        """Build Jekyll/GitHub Pages YAML front matter."""
        return {
            "layout": "post",
            "title": seo_data.get("optimised_title", post["title"]),
            "description": seo_data.get("optimised_meta", post.get("meta_description", "")),
            "date": post["generated_at"][:10],
            "slug": post["slug"],
            "tags": seo_data.get("secondary_keywords", [])[:4],
            "author": "AI Insider Weekly",
            "image": f"/assets/images/{post['slug']}-og.png",
            "canonical": f"{self.site_url}/blog/{post['slug']}/",
        }

    def _build_structured_data(self, post: dict) -> dict:
        """JSON-LD Article structured data for Google."""
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": post["title"],
            "description": post.get("meta_description", ""),
            "url": f"{self.site_url}/blog/{post['slug']}/",
            "datePublished": post["generated_at"][:10],
            "dateModified": post["generated_at"][:10],
            "publisher": {
                "@type": "Organization",
                "name": self.site_name,
                "url": self.site_url,
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{self.site_url}/blog/{post['slug']}/",
            },
        }

    def generate_sitemap_entry(self, post: dict) -> str:
        """Return a sitemap XML entry for this post."""
        url = f"{self.site_url}/blog/{post['slug']}/"
        date = post["generated_at"][:10]
        return (
            f"  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{date}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )
