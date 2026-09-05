"""
LinkedIn job search + recruiter-feed-post scraper (Playwright).

*** IMPORTANT ***
LinkedIn actively fingerprints and rate-limits automated browsers, and its
Terms of Service prohibit scraping. A password-based automated login very
commonly triggers a "verify it's you" / CAPTCHA / email-code challenge that
a headless bot cannot solve, which will make this scraper silently fail
(or worse, get the account temporarily restricted). This module implements
the straightforward approach (log in with email+password, then search),
but if you hit login challenges in the Railway logs, the practical fix is
to log in manually once in a normal browser, export that session's cookies,
and load them here via LI_AT_COOKIE instead of a live login — see
SETUP_GUIDE.md.

Update the selectors below if LinkedIn's markup changes.
"""
from __future__ import annotations

import urllib.parse

from playwright.sync_api import sync_playwright

from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

LOGIN_URL = "https://www.linkedin.com/login"
JOBS_SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
    "&f_TPR=r86400"  # posted in the last 24 hours
)

JOB_CARD_SELECTOR = "div.job-card-container"
TITLE_SELECTOR = "a.job-card-list__title"
COMPANY_SELECTOR = "span.job-card-container__primary-description"
LOCATION_SELECTOR = "li.job-card-container__metadata-item"

# Optional: a valid li_at session cookie value, captured from a manual
# browser login, as a fallback when password login gets challenged.
LI_AT_COOKIE = Config.LI_AT_COOKIE


def _login_with_password(page) -> bool:
    page.goto(LOGIN_URL, timeout=30000)
    page.fill("#username", Config.LINKEDIN_EMAIL)
    page.fill("#password", Config.LINKEDIN_PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_timeout(4000)

    if "checkpoint" in page.url or "challenge" in page.url:
        logger.warning(
            "[LinkedIn] Login hit a verification challenge (CAPTCHA / 2FA / "
            "'verify it's you'). Automated login cannot pass this. Set "
            "LI_AT_COOKIE instead (see SETUP_GUIDE.md)."
        )
        return False
    return True


def _login_with_cookie(context) -> bool:
    if not LI_AT_COOKIE:
        return False
    context.add_cookies([{
        "name": "li_at",
        "value": LI_AT_COOKIE,
        "domain": ".linkedin.com",
        "path": "/",
    }])
    return True


def scrape_linkedin_jobs(max_jobs_per_query: int = 25) -> list[dict]:
    if not Config.LINKEDIN_EMAIL or not (Config.LINKEDIN_PASSWORD or LI_AT_COOKIE):
        logger.warning("[LinkedIn] No credentials/cookie configured — skipping LinkedIn scrape")
        return []

    keywords = [k.strip() for k in Config.JOB_KEYWORDS.split(",") if k.strip()]
    locations = [l.strip() for l in Config.JOB_LOCATIONS.split(",") if l.strip()]

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=Config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        logged_in = False
        if LI_AT_COOKIE:
            logged_in = _login_with_cookie(context)
        if not logged_in and Config.LINKEDIN_PASSWORD:
            logged_in = _login_with_password(page)

        if not logged_in:
            logger.error("[LinkedIn] Could not establish a logged-in session — aborting LinkedIn scrape")
            browser.close()
            return []

        for keyword in keywords:
            for location in locations:
                url = JOBS_SEARCH_URL.format(
                    keywords=urllib.parse.quote(keyword),
                    location=urllib.parse.quote(location),
                )
                logger.info(f"[LinkedIn] Searching: {url}")
                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_selector(JOB_CARD_SELECTOR, timeout=15000)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[LinkedIn] No results / selector changed for '{keyword}' in '{location}': {exc}")
                    continue

                cards = page.query_selector_all(JOB_CARD_SELECTOR)
                for card in cards[:max_jobs_per_query]:
                    try:
                        title_el = card.query_selector(TITLE_SELECTOR)
                        company_el = card.query_selector(COMPANY_SELECTOR)
                        location_el = card.query_selector(LOCATION_SELECTOR)

                        if not title_el:
                            continue

                        job_link = title_el.get_attribute("href") or ""
                        if job_link.startswith("/"):
                            job_link = "https://www.linkedin.com" + job_link

                        results.append({
                            "title": title_el.inner_text().strip(),
                            "company": company_el.inner_text().strip() if company_el else "",
                            "location": location_el.inner_text().strip() if location_el else location,
                            "source_link": job_link,
                            "application_link": job_link,
                        })
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[LinkedIn] Failed to parse a job card: {exc}")

        browser.close()

    logger.info(f"[LinkedIn] Scraped {len(results)} job listings")
    return results
