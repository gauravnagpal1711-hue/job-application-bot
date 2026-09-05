# Setup Guide

## 1. Google Cloud service account (so the bot can read/write your Sheet)

1. Go to https://console.cloud.google.com/ and create a project (e.g. "Job Bot").
2. Enable **Google Sheets API** and **Google Drive API** for that project.
3. IAM & Admin → Service Accounts → Create Service Account (e.g. `job-bot-service`), role **Editor**.
4. Open the service account → Keys → Add Key → Create new key → **JSON** → download it.
   This file contains a private key — treat it like a password. Don't paste it into
   chat or commit it to the repo (it's already covered by `.gitignore`).
5. Open your Google Sheet → Share → paste the service account's `client_email`
   (from the downloaded JSON) → give it **Editor** access.

## 2. Google Sheet structure

**Sheet1 — Credentials & Profile** (key/value, one field per row):

| Column A | Column B |
|---|---|
| Resume Link | https://drive.google.com/... |
| HRBP Experience (years) | 5 |
| BFSI Experience (years) | 3 |
| Relocation Willingness | Yes |
| Available From | Immediate |
| ... | ... |

Add whatever fields your target applications actually ask for — the bot
matches form field labels against these keys by name.

**Sheet2 — Job Applications Tracker** headers (row 1):
`Date Found | Company Name | Job Title | Location | Source Link | Application Link | Order to Apply | Status | Date Applied | Bot Notes | Missing Info Required`

The bot will create/fix these headers automatically on first run if missing.

## 3. Deploy to Railway

1. https://railway.app/ → sign in with GitHub.
2. New Project → Deploy from GitHub repo → select `job-application-bot`.
3. Railway detects the `Dockerfile` and builds automatically.

## 4. Environment variables (Railway → your service → Variables)

Set these directly in Railway's dashboard — **do not** send these values
through any third party, including in chat:

| Variable | Value |
|---|---|
| `GOOGLE_SHEET_ID` | the ID from your sheet's URL (the long string between `/d/` and `/edit`) |
| `GOOGLE_CREDENTIALS_JSON` | paste the **entire contents** of the downloaded service-account JSON file |
| `LINKEDIN_EMAIL` | your LinkedIn login email |
| `LINKEDIN_PASSWORD` | see the LinkedIn note below — an app password does **not** apply to LinkedIn logins |
| `LOG_LEVEL` | `INFO` |
| `JOB_KEYWORDS` | comma-separated, e.g. `HR Manager,Talent Acquisition,HRBP` |
| `JOB_LOCATIONS` | comma-separated, e.g. `Delhi NCR,Remote` |

### A note on LinkedIn credentials

LinkedIn doesn't support "app passwords" the way Google/Gmail does — that
mechanism is specific to Google accounts with 2-Step Verification. For
LinkedIn you'd set your actual account password as `LINKEDIN_PASSWORD`,
which is exactly the kind of automated login LinkedIn's bot-detection is
built to catch (expect a CAPTCHA/"verify it's you" challenge most of the
time). The more reliable path:

1. Log into LinkedIn manually in a normal browser.
2. Open DevTools → Application → Cookies → linkedin.com → copy the value
   of the `li_at` cookie.
3. Set it as a Railway variable named `LI_AT_COOKIE` instead of relying on
   password login. `scrapers/linkedin_scraper.py` will use it automatically.
4. This cookie expires periodically (LinkedIn rotates it) — you'll need to
   refresh it every so often when the bot's logs show login failures.

Either way, only you should type your LinkedIn password/cookie into
Railway's own Variables screen — never share it in chat with anyone,
including an AI assistant.

## 5. First run

After variables are set, Railway redeploys automatically. Check
**Deployments → (latest) → Logs** for:

```
✅ Job Application Bot initialized
📅 Scheduled: Daily job scrape at 11 AM IST
🔄 Starting continuous monitoring for 'Order to Apply' entries...
```

If LinkedIn login fails, you'll see a warning in the logs and the bot will
still run Naukri scraping normally.

## 6. Daily usage

1. Check Sheet2 after 11 AM IST for new jobs.
2. Mark `Order to Apply = YES` on jobs you want.
3. Bot checks every 5 minutes and applies; watch `Status` and `Bot Notes`.
4. If `Missing Info Required` is populated, add that field to Sheet1 — the
   next apply-loop pass retries automatically.
