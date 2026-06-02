"""
Publisher
Publishes newsletter drafts to Substack (via email API) and 
blog posts to GitHub Pages (via GitHub API).
Both are 100% free.
"""

import os
import re
import json
import base64
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import requests

log = logging.getLogger("publisher")


class Publisher:
    def __init__(self, config: dict):
        self.config = config
        self.github_token = config.get("github_token")
        self.github_repo = config.get("github_repo")  # e.g. "username/ai-insider-weekly"
        self.substack_cookie = config.get("substack_session_cookie")
        self.substack_publication = config.get("substack_publication_url")  # e.g. "aiinsiderweekly"

    # ── Substack ─────────────────────────────────────────────────

    def publish_newsletter(self, newsletter: dict, send_to_subscribers: bool = False):
        """
        Push a draft newsletter to Substack.
        send_to_subscribers=False: saves as draft for you to review in Substack dashboard
        send_to_subscribers=True:  immediately sends to all subscribers
        
        Note: Substack doesn't have an official public API.
        We use the same endpoints their web app uses.
        If this breaks, log in to Substack and paste the email body manually —
        it takes 2 minutes and that's within your 1-3 hr/week budget.
        """
        if not self.substack_cookie or not self.substack_publication:
            log.warning(
                "Substack not configured. Newsletter saved locally only.\n"
                "To enable: add 'substack_session_cookie' and 'substack_publication_url' to config.json\n"
                "Get cookie: Log into substack.com → DevTools → Application → Cookies → copy 'substack.sid'"
            )
            self._save_newsletter_locally(newsletter)
            return

        try:
            headers = {
                "Cookie": f"substack.sid={self.substack_cookie}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            }

            # Create draft post
            payload = {
                "draft_title": newsletter["subject"],
                "draft_subtitle": newsletter["preview"],
                "draft_body": self._newsletter_to_html(newsletter["body"]),
                "draft_byline": "AI Insider Weekly",
                "section_chosen": True,
                "type": "newsletter",
            }

            base_url = f"https://{self.substack_publication}.substack.com"
            resp = requests.post(
                f"{base_url}/api/v1/drafts",
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            post_id = resp.json().get("id")
            log.info(f"Substack draft created: post_id={post_id}")

            if send_to_subscribers and post_id:
                send_resp = requests.post(
                    f"{base_url}/api/v1/posts/{post_id}/send_email",
                    headers=headers,
                    json={"send_time": None},  # None = send immediately
                    timeout=15,
                )
                send_resp.raise_for_status()
                log.info(f"Newsletter sent to subscribers!")

        except Exception as e:
            log.error(f"Substack publish failed: {e}")
            log.info("Falling back to local save...")
            self._save_newsletter_locally(newsletter)

    def _newsletter_to_html(self, markdown_body: str) -> str:
        """Convert newsletter markdown body to basic HTML for Substack."""
        html = markdown_body
        # Bold
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        # Links
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)
        # Bullets
        lines = html.split("\n")
        out, in_list = [], False
        for line in lines:
            if line.startswith("- ") or line.startswith("• "):
                if not in_list:
                    out.append("<ul>")
                    in_list = True
                out.append(f"<li>{line[2:]}</li>")
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                if line.strip():
                    out.append(f"<p>{line}</p>")
                else:
                    out.append("<br>")
        if in_list:
            out.append("</ul>")
        return "\n".join(out)

    def _save_newsletter_locally(self, newsletter: dict):
        out_dir = Path("../output/newsletters")
        out_dir.mkdir(parents=True, exist_ok=True)
        date = newsletter["generated_at"][:10]
        path = out_dir / f"issue_{newsletter['issue_number']}_{date}.html"
        with open(path, "w") as f:
            f.write(f"<h1>{newsletter['subject']}</h1>\n")
            f.write(self._newsletter_to_html(newsletter["body"]))
        log.info(f"Newsletter saved locally: {path}")

    # ── GitHub Pages ─────────────────────────────────────────────

    def publish_blog_post(self, post: dict):
        """Push a blog post to GitHub Pages via the GitHub API."""
        if not self.github_token or not self.github_repo:
            log.warning(
                "GitHub not configured. Blog post saved locally only.\n"
                "To enable: add 'github_token' and 'github_repo' to config.json"
            )
            self._save_post_locally(post)
            return

        try:
            content = self._build_jekyll_post(post)
            date = post["generated_at"][:10]
            filename = f"_posts/{date}-{post['slug']}.md"

            encoded = base64.b64encode(content.encode()).decode()
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Check if file exists (for update vs create)
            check_url = f"https://api.github.com/repos/{self.github_repo}/contents/{filename}"
            check = requests.get(check_url, headers=headers, timeout=10)
            
            payload = {
                "message": f"Add post: {post['title'][:50]}",
                "content": encoded,
            }
            if check.status_code == 200:
                payload["sha"] = check.json()["sha"]

            resp = requests.put(check_url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            log.info(f"Published to GitHub Pages: {filename}")

        except Exception as e:
            log.error(f"GitHub publish failed: {e}")
            self._save_post_locally(post)

    def _build_jekyll_post(self, post: dict) -> str:
        """Build a Jekyll-compatible markdown file with front matter."""
        fm = post.get("front_matter", {})
        structured_data = json.dumps(post.get("structured_data", {}), indent=2)

        front_matter = "---\n"
        front_matter += f"layout: post\n"
        front_matter += f"title: \"{fm.get('title', post['title']).replace(chr(34), chr(39))}\"\n"
        front_matter += f"description: \"{fm.get('description', '')[:155].replace(chr(34), chr(39))}\"\n"
        front_matter += f"date: {fm.get('date', post['generated_at'][:10])}\n"
        front_matter += f"slug: {post['slug']}\n"
        if fm.get("tags"):
            tags_str = ", ".join(f'"{t}"' for t in fm["tags"])
            front_matter += f"tags: [{tags_str}]\n"
        front_matter += f"author: AI Insider Weekly\n"
        front_matter += "---\n\n"

        # Inject JSON-LD structured data
        schema_block = (
            f'<script type="application/ld+json">\n{structured_data}\n</script>\n\n'
        )

        return front_matter + schema_block + post["body_markdown"]

    def _save_post_locally(self, post: dict):
        out_dir = Path("../output/posts")
        out_dir.mkdir(parents=True, exist_ok=True)
        date = post["generated_at"][:10]
        path = out_dir / f"{date}-{post['slug']}.md"
        with open(path, "w") as f:
            f.write(self._build_jekyll_post(post))
        log.info(f"Post saved locally: {path}")
