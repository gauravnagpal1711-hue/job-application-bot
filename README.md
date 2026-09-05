# Job Application Bot

Scrapes HR/recruitment job postings from LinkedIn and Naukri, logs them to a
Google Sheet, and auto-applies to whichever rows you mark `YES` in the
"Order to Apply" column. Runs on Railway as a long-lived worker (daily
scrape + a continuous apply loop), no server or UI required — the Google
Sheet is the control panel.

## How it works

1. **Daily scrape** (11:00 IST by default) — pulls jobs posted in the last
   24h matching `JOB_KEYWORDS` / `JOB_LOCATIONS`, skips ones already in the
   tracker, appends new ones to **Sheet2** with `Status = Pending Review`.
2. **You review** Sheet2 and type `YES` in the **Order to Apply** column for
   jobs you want to apply to, any time during the day.
3. **Continuous apply loop** (every 5 minutes by default) — scans for
   `Order to Apply = YES` rows, fills the application form from your
   profile data in **Sheet1**, and updates `Status` / `Date Applied` /
   `Bot Notes` / `Missing Info Required`.
4. If a form asks for something not in your Sheet1 profile, the row is
   flagged with `Missing Info Required` instead of guessing — add the
   field to Sheet1 and the next apply-loop pass retries it.

## Project layout

```
job_bot_main.py          entry point: scheduler wiring
utils/config.py           env-var based config + validation
utils/logger.py           stdout logging
integrations/google_sheets.py   Sheet1/Sheet2 read+write wrapper
scrapers/naukri_scraper.py      Naukri search scraper (Playwright)
scrapers/linkedin_scraper.py    LinkedIn search scraper (Playwright)
automation/form_filler.py       LinkedIn Easy Apply / Naukri one-click filler
```

## Setup

See **SETUP_GUIDE.md** for the full walkthrough (Google service account,
Railway environment variables, first run).

## Known limitations — read before relying on this

- **LinkedIn actively blocks automation.** A password login can trigger a
  CAPTCHA/verification challenge that a headless bot cannot pass. If that
  happens, the bot logs a warning and skips LinkedIn rather than failing
  silently — see SETUP_GUIDE.md for the cookie-based workaround. Running
  this against your own LinkedIn account carries a real risk of a
  temporary restriction; that trade-off is yours to make.
- **CSS selectors will drift.** Both scrapers depend on LinkedIn's and
  Naukri's current page markup. When either site updates its front-end,
  the scraper will return zero results until the selectors in
  `scrapers/*.py` are updated to match the new markup.
- **Form filling is best-effort**, matching visible field labels against
  your Sheet1 profile keys by name. Multi-step LinkedIn Easy Apply flows
  and third-party ATS pages (Greenhouse, Lever, Workday, etc.) are only
  partially handled — see the `TODO`-style notes in `form_filler.py`.
- This is a first working version, not a battle-tested product — plan on
  watching the Railway logs and Sheet2's `Bot Notes` column closely for
  the first week and tightening selectors/logic as you see real jobs flow
  through it.
