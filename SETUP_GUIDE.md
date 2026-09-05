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
| `NAUKRI_COOKIES` | your Naukri session cookies — see the note below (needed for one-click apply; search/scrape works without it) |
| `LOG_LEVEL` | `INFO` |
| `JOB_KEYWORDS` | comma-separated, e.g. `HR Manager,Talent Acquisition,HRBP` |
| `JOB_LOCATIONS` | comma-separated, e.g. `Delhi NCR,Remote` |

### Why a cookie instead of your password

Naukri's own login flow is built to catch automated password logins, so
this bot never types your password into the site. It authenticates the
same way a "remember me" session does: with a cookie copied from a browser
where **you** logged in normally. That means:

- Your actual password is never stored anywhere in this project, in
  Railway, or in any conversation — including with an AI assistant. Only
  type your Naukri password into naukri.com's own login page, nowhere else.
- A leaked cookie is a much smaller risk than a leaked password — you can
  invalidate it any time by simply logging out (or changing your
  password), and it can't be used to change your account's password or
  security settings the way a real password could.
- The tradeoff: cookies expire periodically, so if the bot's logs start
  showing login failures, just repeat the steps below to grab a fresh one.

### Getting your Naukri cookie (`NAUKRI_COOKIES`)

1. Log into Naukri manually (as the candidate account you want the bot to
   apply as) in a normal browser.
2. Open DevTools → Application → Storage → Cookies → `naukri.com`.
3. Copy every row as one string in `name=value; name2=value2` format (in
   Chrome you can select all rows in the cookie table, copy, and paste —
   or copy them one at a time and join with `; `). Include at least the
   session/auth-looking cookies (names vary and change over time, so when
   in doubt include all of them).
4. Set that whole string as a Railway variable named `NAUKRI_COOKIES`.
   `job_bot_main.py` loads it into the browser before every apply run.

Only you should ever open DevTools on your own logged-in session and paste
the resulting cookie value into Railway's own Variables screen — never
share your password, or the cookie value, in chat with anyone, including
an AI assistant.

## 5. First run

After variables are set, Railway redeploys automatically. Check
**Deployments → (latest) → Logs** for:

```
✅ Job Application Bot initialized
📅 Scheduled: Daily job scrape at 11 AM IST
🔄 Starting continuous monitoring for 'Order to Apply' entries...
```

If `NAUKRI_COOKIES` is missing or expired, one-click apply will hit a
login wall — you'll see it noted in the logs and in each row's `Bot
Notes`, while search/scrape keeps working normally.

## 6. Daily usage

1. Check Sheet2 after 11 AM IST for new jobs.
2. Mark `Order to Apply = YES` on jobs you want.
3. Bot checks every 5 minutes and applies; watch `Status` and `Bot Notes`.
4. If `Missing Info Required` is populated, add that field to Sheet1 — the
   next apply-loop pass retries automatically.
