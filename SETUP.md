# AI Insider Weekly — Setup Guide (OpenAI version)

Estimated setup time: **90 minutes** (one-time only).
After that: 1–3 hrs/week to review and send drafts.

---

## Step 1 — OpenAI API key (~10 minutes)

1. Go to **https://platform.openai.com**
2. Click **Sign up** — use your email address (no business ID required)
3. Verify your email, then verify your phone number
4. Once logged in, click your profile icon (top right) → **API keys**
5. Click **Create new secret key** → give it a name like "ai-insider-weekly"
6. **Copy the key immediately** — it starts with `sk-...` and is only shown once
7. Go to **Settings → Billing → Add payment method** — add a card
8. Set a **usage limit** of $20/month to be safe (the pipeline costs ~$8/mo)

**Keep your API key safe** — you'll add it to GitHub in Step 4.

---

## Step 2 — Substack newsletter (~10 minutes)

1. Go to **https://substack.com**
2. Click **Start writing** → sign up with your email
3. When asked "What's your publication about?" — choose **Technology**
4. Publication name: **AI Insider Weekly**
5. Subdomain: type `aiinsiderweekly` (or `aiinsider` if taken — check availability)
6. **Skip** the personal profile / author photo — leave it blank for a faceless brand
7. Write a short description: *"Practical AI tools and insights for professionals. Every Tuesday, free."*
8. Note your full Substack URL (e.g. `https://aiinsiderweekly.substack.com`)

**Get your session cookie** (needed so the pipeline can auto-draft):
1. Log into substack.com in **Google Chrome**
2. Press **F12** to open DevTools
3. Click the **Application** tab
4. In the left panel: Cookies → click `https://substack.com`
5. Find the row named **`substack.sid`**
6. Copy the entire **Value** — it's a long string of letters/numbers
7. Save it — you'll need it in Step 4

---

## Step 3 — GitHub repository (~20 minutes)

### 3a. Create a GitHub account (if you don't have one)
1. Go to **https://github.com** → Sign up
2. Verify your email address

### 3b. Create the repository
1. Click the **+** icon (top right) → **New repository**
2. Repository name: `ai-insider-weekly`
3. Set visibility to **Public** (required for free GitHub Pages)
4. Click **Create repository**

### 3c. Upload the code
1. On your new repo page, click **uploading an existing file**
2. Unzip the `ai-insider-weekly.zip` file on your computer
3. Open the unzipped folder — you'll see: `agents/`, `config/`, `site/`, `workflows/`, `scripts/`, `requirements.txt`, `SETUP.md`
4. Drag **all of these files and folders** into the GitHub upload area
5. Scroll down, click **Commit changes**

### 3d. Set up GitHub Pages (your free website)
1. In your repo, click **Settings** (top menu)
2. Scroll down to **Pages** (left sidebar)
3. Under "Source" select **Deploy from a branch**
4. Branch: `main` — Folder: `/site`
5. Click **Save**
6. Wait 2 minutes, then your site is live at:
   `https://YOUR_USERNAME.github.io/ai-insider-weekly`

### 3e. Move the workflow file
The automation file needs to be in a specific folder GitHub recognises:
1. In your repo, click **Add file → Create new file**
2. In the filename box type: `.github/workflows/weekly_pipeline.yml`
3. Go back to the uploaded `workflows/weekly_pipeline.yml` file in your repo
4. Copy its entire contents
5. Paste into the new file → **Commit changes**

### 3f. Create a personal access token
1. Click your profile photo → **Settings**
2. Scroll to bottom → **Developer settings**
3. **Personal access tokens → Tokens (classic)**
4. **Generate new token (classic)**
5. Note: "ai-insider-weekly"
6. Expiration: **No expiration**
7. Tick these scopes: `repo` and `workflow`
8. Click **Generate token** → **copy it immediately**

---

## Step 4 — Add your secrets to GitHub (~10 minutes)

Secrets keep your API keys safe — they're encrypted and never visible after you save them.

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each one below:

| Secret name | Value to paste |
|---|---|
| `OPENAI_API_KEY` | Your key from Step 1 |
| `SUBSTACK_COOKIE` | The `substack.sid` value from Step 2 |
| `SUBSTACK_PUBLICATION` | Just the subdomain e.g. `aiinsiderweekly` |
| `SUBSTACK_URL` | Full URL e.g. `https://aiinsiderweekly.substack.com` |
| `GH_PAGES_TOKEN` | Your personal access token from Step 3f |
| `GITHUB_REPO` | e.g. `yourusername/ai-insider-weekly` |
| `SITE_URL` | e.g. `https://yourusername.github.io/ai-insider-weekly` |
| `AFFILIATE_TOOLS_JSON` | Paste the affiliate_tools array from config.json (update with your real links from Step 5) |

**Optional — social media auto-posting:**

| Secret name | Where to get it |
|---|---|
| `TWITTER_API_KEY` | developer.twitter.com → create a free app |
| `TWITTER_API_SECRET` | Same |
| `TWITTER_ACCESS_TOKEN` | Same |
| `TWITTER_ACCESS_SECRET` | Same |
| `LINKEDIN_ACCESS_TOKEN` | developers.linkedin.com |
| `LINKEDIN_PERSON_URN` | Your LinkedIn profile API ID |

You can skip social secrets for now — the pipeline will just save social copy locally for you to post manually.

---

## Step 5 — Affiliate signups (~20 minutes)

All free to join. Do these two first — they have the simplest signup:

### Perplexity AI (easiest, 20% recurring)
1. Go to **https://perplexity.ai**
2. Scroll to the very bottom footer → click **Affiliates**
3. Sign up with your email
4. Copy your unique referral link from the dashboard

### Notion (20% recurring)
1. Go to **https://notion.so/affiliates**
2. Apply — usually approved within 24 hours
3. Copy your referral link

### Jasper AI (highest commission — 25% recurring for life)
1. Go to **https://jasper.ai/affiliates**
2. Sign up → copy your link

### Add your links to the config
1. In your GitHub repo, open `config/config.json`
2. Click the pencil icon to edit
3. Replace each `YOUR_XXX_AFFILIATE_LINK` with your real links
4. Do the same in `site/_data/affiliates.yml`
5. Commit changes

---

## Step 6 — Test the pipeline (~5 minutes)

1. Go to your GitHub repo → click **Actions** tab
2. Click **Weekly Newsletter Pipeline** in the left list
3. Click **Run workflow** (top right) → leave auto_publish as `false` → **Run workflow**
4. A yellow circle appears — click it to watch it run live
5. Takes about 3–4 minutes to complete
6. When green: click the run → scroll to **Artifacts** → download **newsletter-draft-1**
7. Unzip it — open the JSON file in any text editor — your first newsletter is inside!

If it turns red (failed): click the failed step, read the error, and message me — I'll fix it.

---

## Your weekly routine (every Tuesday)

GitHub Actions runs automatically at 7am UTC every Tuesday. Your job:

1. **Check your email** — GitHub sends you a notification the pipeline ran
2. **Download the draft** from the Actions artifacts (~2 min)
3. **Read the newsletter** — edit anything that seems off (~20 min)
4. **Log into Substack** → New Post → paste the body → Preview → Send (~10 min)
5. **Post social content** — copy the generated tweets/LinkedIn post and publish (~10 min)

That's it. Everything else — research, writing, SEO, blog publishing — is automatic.

---

## Revenue milestones

| Stage | Subscribers | Weekly revenue | What to focus on |
|---|---|---|---|
| Month 1–2 | 0–200 | $0–50 | Growing subs, testing content |
| Month 2–3 | 200–500 | $50–200 | Affiliate links live, first conversions |
| Month 3–4 | 500–1000 | $200–500 | Launch paid tier at $9/mo |
| Month 4–6 | 1000+ | $500–1000+ | Add sponsorships at $200–400/issue |
| Month 6+ | 2000+ | $1000+/wk | Scale — more issues, more affiliates |

---

## Getting your first 100 subscribers fast

- **Reddit**: Post genuinely helpful comments in r/ChatGPT, r/artificial, r/productivity. Add newsletter link in your profile bio only.
- **Your network**: Email 20 people personally. One personal ask beats 1,000 cold impressions.
- **Twitter/X**: Post the generated tweet thread every Tuesday. Consistency beats virality.
- **ProductHunt**: Submit the newsletter on a Tuesday when issue #2 or #3 drops.

---

## Troubleshooting

**Pipeline fails — "Invalid API key"**: Double-check your `OPENAI_API_KEY` secret has no spaces and billing is enabled at platform.openai.com.

**Substack draft not appearing**: The session cookie expires every few weeks. Log into Substack again, get a fresh cookie, update the `SUBSTACK_COOKIE` secret.

**GitHub Pages not showing**: Check Actions tab for a "pages build and deployment" workflow. Can take up to 10 minutes on first deploy.

**Social posting skipped**: That's normal if you haven't added Twitter/LinkedIn secrets — the pipeline logs a warning and continues. Everything else still runs.
