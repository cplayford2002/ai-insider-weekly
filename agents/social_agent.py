"""
Social Agent
Generates platform-specific social copy and posts to X (Twitter) and LinkedIn.
Uses free-tier APIs. Twitter API v2 free tier: 1,500 tweets/month.
"""

import re
import json
import logging
import time
from typing import Optional

import requests
from openai import OpenAI

log = logging.getLogger("social_agent")


class SocialAgent:
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI(api_key=config["openai_api_key"])
        self.newsletter_name = config.get("newsletter_name", "AI Insider Weekly")
        self.site_url = config.get("site_url", "")
        self.substack_url = config.get("substack_url", "")

        # Twitter/X credentials
        self.twitter_bearer = config.get("twitter_bearer_token")
        self.twitter_api_key = config.get("twitter_api_key")
        self.twitter_api_secret = config.get("twitter_api_secret")
        self.twitter_access_token = config.get("twitter_access_token")
        self.twitter_access_secret = config.get("twitter_access_secret")

        # LinkedIn credentials
        self.linkedin_access_token = config.get("linkedin_access_token")
        self.linkedin_person_urn = config.get("linkedin_person_urn")

    # ── Generate copy ────────────────────────────────────────────

    def generate_posts(self, newsletter: dict, blog_posts: list[dict]) -> dict:
        """Generate a full week's social copy for all platforms."""
        log.info("Generating social media copy...")

        newsletter_hook = newsletter["subject"]
        top_topic = blog_posts[0]["title"] if blog_posts else "AI this week"

        x_posts = self._generate_x_thread(newsletter, blog_posts)
        linkedin_post = self._generate_linkedin(newsletter, blog_posts)
        reddit_comment = self._generate_reddit_post(blog_posts[0] if blog_posts else None)

        return {
            "x_thread": x_posts,
            "linkedin": linkedin_post,
            "reddit": reddit_comment,
        }

    def _generate_x_thread(self, newsletter: dict, blog_posts: list[dict]) -> list[str]:
        """Generate a 5-tweet thread promoting the newsletter."""
        topics_text = "\n".join(f"- {p['title']}" for p in blog_posts[:3])
        substack_link = self.substack_url or "[SUBSTACK_URL]"

        prompt = f"""Write a 5-tweet thread for X (Twitter) to promote this newsletter issue.

NEWSLETTER SUBJECT: {newsletter['subject']}
TOP TOPICS COVERED:
{topics_text}
SUBSCRIBE LINK: {substack_link}

Rules:
- Tweet 1: hook that makes people stop scrolling. No "thread🧵" cliché. Start mid-thought.
- Tweets 2-4: one insight per tweet from the newsletter. Specific, not vague. Include a stat or surprising fact.
- Tweet 5: CTA to subscribe. Mention it's free.
- Each tweet MAX 240 chars (leave room for link)
- No hashtags spam — max 1 per tweet, only if very natural
- Separate each tweet with "---"

Write the thread:"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        tweets = [t.strip() for t in raw.split("---") if t.strip()]
        return tweets[:5]

    def _generate_linkedin(self, newsletter: dict, blog_posts: list[dict]) -> str:
        """Generate a LinkedIn post (longer form, professional tone)."""
        topics_text = "\n".join(f"• {p['title']}" for p in blog_posts[:3])
        substack_link = self.substack_url or "[SUBSTACK_URL]"

        prompt = f"""Write a LinkedIn post promoting this newsletter issue.

NEWSLETTER: {newsletter['subject']}
TOPICS:
{topics_text}
LINK: {substack_link}

LinkedIn style: Starts with a bold first line (no "I'm excited to share"). 
Professional but human. 150-250 words. 3-4 short paragraphs. 
End with a question to drive comments. Include link naturally in last paragraph.
NO generic "engagement bait". Be specific and add genuine value.

Write the post:"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    def _generate_reddit_post(self, top_post: Optional[dict]) -> Optional[str]:
        """Generate a Reddit-appropriate comment to add value in AI subs."""
        if not top_post:
            return None

        prompt = f"""Write a Reddit comment for r/artificial or r/MachineLearning that adds genuine value.
Topic: {top_post['title']}
Key insight: {top_post.get('source_topic', {}).get('summary', '')}

Rules: 
- Sound like a knowledgeable person, NOT a marketer
- Add a real insight or nuance NOT in the article
- At the very END, casually mention your newsletter as "I covered this in more depth in my newsletter [link] if anyone wants the full breakdown" — only if it fits naturally
- 100-150 words max

Write the comment:"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    # ── Post to platforms ────────────────────────────────────────

    def post_all(self, social_posts: dict):
        """Post to all configured platforms."""
        if self.twitter_access_token and social_posts.get("x_thread"):
            self._post_x_thread(social_posts["x_thread"])
        else:
            log.info("X/Twitter not configured — skipping")

        if self.linkedin_access_token and social_posts.get("linkedin"):
            self._post_linkedin(social_posts["linkedin"])
        else:
            log.info("LinkedIn not configured — skipping")

    def _post_x_thread(self, tweets: list[str]):
        """Post a thread to X using OAuth 1.0a."""
        try:
            from requests_oauthlib import OAuth1
            auth = OAuth1(
                self.twitter_api_key,
                self.twitter_api_secret,
                self.twitter_access_token,
                self.twitter_access_secret,
            )
            reply_to = None
            for i, tweet in enumerate(tweets):
                payload = {"text": tweet}
                if reply_to:
                    payload["reply"] = {"in_reply_to_tweet_id": reply_to}
                resp = requests.post(
                    "https://api.twitter.com/2/tweets",
                    auth=auth,
                    json=payload,
                    timeout=10,
                )
                resp.raise_for_status()
                reply_to = resp.json()["data"]["id"]
                log.info(f"Posted X tweet {i+1}/{len(tweets)}")
                time.sleep(1)
        except ImportError:
            log.warning("requests-oauthlib not installed — install it to enable Twitter posting")
        except Exception as e:
            log.error(f"X posting failed: {e}")

    def _post_linkedin(self, text: str):
        """Post to LinkedIn using the Share API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            payload = {
                "author": self.linkedin_person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
            resp = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            log.info("LinkedIn post published")
        except Exception as e:
            log.error(f"LinkedIn posting failed: {e}")
