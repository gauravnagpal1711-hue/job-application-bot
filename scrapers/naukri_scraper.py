"""
Naukri.com job search scraper (Playwright).

Naukri's public job-search results are far less aggressive about blocking
automated browsers than LinkedIn, so this scraper logs in only if
NAUKRI_EMAIL/NAUKRI_PASSWORD are set, and otherwise just scrapes the public
search results page (no login required to view listings).

NOTE: Naukri periodically changes its front-end markup/class names. The
CSS selectors below matched the site's structure as of this writing — if
scraping stops returning results, open the search page in a real browser,
inspect the job-card elements, and update SEARCH_RESULT_SELECTORS below.
"""
from __future__ import annotations

import urllib.parse

from playwright.sync_api import sync_playwright

from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

BASE_SEARCH_URL = "https://www.naukri.com/{query}-jobs-in-{location}"

# Selectors for the search-results job cards. Update here if Naukri's
# markup changes.
JOB_CARD_SELECTOR = "div.cust-job-tuple"
TITLE_SELECTOR = "a.title"
COMPANY_SELECTOR = "a.comp-name"
LOCATION_SELECTOR = "span.locWdth"


def _slugify(text: str) -> str:
    return urllib.parse.quote(text.strip().lower().replace(" ", "-"))


def scrape_naukri_jobs(max_jobs_per_query: int = 25) -> list[dict]:
    """Returns a list of dicts: title, company, location, source_link,
    application_link. Only jobs are returned — filtering by "last 24h" and
    de-duping against the sheet happens in job_bot_main.py."""
    keywords = [k.strip() for k in Config.JOB_KEYWORDS.split(",") if k.strip()]
    locations = [l.strip() for l in Config.JOB_LOCATIONS.split(",") if l.strip()]

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=Config.HEADLESS)
        page = browser.new_page()

        for keyword in keywords:
            for location in locations:
                url = BASE_SEARCH_URL.format(
                    query=_slugify(keyword), location=_slugify(location)
                )
                logger.info(f"[Naukri] Searching: {url}")
                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_selector(JOB_CARD_SELECTOR, timeout=15000)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[Naukri] No results / selector changed for '{keyword}' in '{location}': {exc}")
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
                        results.append({
                            "title": title_el.inner_text().strip(),
                            "company": company_el.inner_text().strip() if company_el else "",
                            "location": location_el.inner_text().strip() if location_el else location,
                            "source_link": job_link,
                            "application_link": job_link,
                        })
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[Naukri] Failed to parse a job card: {exc}")

        browser.close()

    logger.info(f"[Naukri] Scraped {len(results)} job listings")
    return results
