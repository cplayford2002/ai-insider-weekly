"""
AI Insider Weekly — Orchestrator Agent
Coordinates all agents to produce one newsletter issue per week.
Run via: python orchestrator.py  (or via GitHub Actions cron)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from research_agent import ResearchAgent
from writing_agent import WritingAgent
from seo_agent import SEOAgent
from social_agent import SocialAgent
from publisher import Publisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("../logs/orchestrator.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("orchestrator")


def load_config() -> dict:
    config_path = Path("../config/config.json")
    with open(config_path) as f:
        return json.load(f)


def save_draft(data: dict) -> Path:
    drafts_dir = Path("../drafts")
    drafts_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = drafts_dir / f"issue_{date_str}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Draft saved to {out_path}")
    return out_path


def run_pipeline(auto_publish: bool = False):
    """
    Full weekly pipeline:
    1. Research   → find 5 trending AI topics
    2. Writing    → draft newsletter + 3 blog posts
    3. SEO        → optimise posts with keywords / meta
    4. Review     → save draft for optional human approval
    5. Social     → generate social copy
    6. Publish    → push to Substack + GitHub Pages (if approved)
    """
    config = load_config()
    log.info("=== AI Insider Weekly pipeline starting ===")

    # ── 1. Research ──────────────────────────────────────────────
    log.info("Step 1/5: Research agent running...")
    researcher = ResearchAgent(config)
    topics = researcher.get_trending_topics(n=5)
    log.info(f"Found topics: {[t['title'] for t in topics]}")

    # ── 2. Writing ───────────────────────────────────────────────
    log.info("Step 2/5: Writing agent running...")
    writer = WritingAgent(config)
    newsletter = writer.write_newsletter(topics)
    blog_posts = [writer.write_blog_post(t) for t in topics[:3]]
    log.info(f"Newsletter '{newsletter['subject']}' drafted")

    # ── 3. SEO ───────────────────────────────────────────────────
    log.info("Step 3/5: SEO agent running...")
    seo = SEOAgent(config)
    blog_posts = [seo.optimise(post) for post in blog_posts]
    log.info("SEO optimisation complete")

    # ── 4. Social copy ───────────────────────────────────────────
    log.info("Step 4/5: Social agent generating copy...")
    social = SocialAgent(config)
    social_posts = social.generate_posts(newsletter, blog_posts)

    # ── 5. Bundle & save draft ───────────────────────────────────
    issue = {
        "generated_at": datetime.utcnow().isoformat(),
        "newsletter": newsletter,
        "blog_posts": blog_posts,
        "social_posts": social_posts,
        "topics": topics,
        "status": "draft",
    }
    draft_path = save_draft(issue)

    if auto_publish:
        log.info("Step 5/5: Auto-publish enabled — publishing now...")
        _publish(issue, config)
    else:
        log.info(
            f"Step 5/5: Draft ready for review at {draft_path}\n"
            "Run: python orchestrator.py --publish <draft_path>  to publish."
        )

    log.info("=== Pipeline complete ===")
    return draft_path


def publish_draft(draft_path: str):
    config = load_config()
    with open(draft_path) as f:
        issue = json.load(f)
    issue["status"] = "approved"
    _publish(issue, config)


def _publish(issue: dict, config: dict):
    publisher = Publisher(config)
    publisher.publish_newsletter(issue["newsletter"])
    for post in issue["blog_posts"]:
        publisher.publish_blog_post(post)
    social = SocialAgent(config)
    social.post_all(issue["social_posts"])
    log.info("All content published successfully")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Insider Weekly Orchestrator")
    parser.add_argument("--publish", metavar="DRAFT_PATH", help="Publish a saved draft")
    parser.add_argument("--auto", action="store_true", help="Publish immediately without review")
    args = parser.parse_args()

    if args.publish:
        publish_draft(args.publish)
    else:
        run_pipeline(auto_publish=args.auto)
