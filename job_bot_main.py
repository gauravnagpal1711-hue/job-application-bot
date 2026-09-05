"""
Job Application Bot — entry point.

Two jobs run on a schedule:
  1. Daily scrape (default 11:00 IST): pull jobs posted in the last 24h
     from Naukri, skip ones already in the tracker, append the rest to
     Sheet2 with Status = "Pending Review".
  2. Continuous apply loop (default every 5 minutes): scan Sheet2 for rows
     where "Order to Apply" = YES and Status != Applied, attempt to apply
     using the profile data in Sheet1, and update Status / Bot Notes /
     Missing Info Required accordingly.
"""
from __future__ import annotations

import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from playwright.sync_api import sync_playwright

from automation.form_filler import apply_naukri_one_click
from integrations.google_sheets import SheetsClient
from scrapers.naukri_scraper import scrape_naukri_jobs
from utils.config import Config
from utils.cookies import parse_cookie_string
from utils.logger import get_logger

logger = get_logger("job_bot_main")


def run_daily_scrape():
    logger.info("Starting daily scrape...")
    sheets = SheetsClient()
    sheets.ensure_headers()

    existing_links = sheets.get_existing_source_links()

    all_jobs = []
    try:
        all_jobs.extend(scrape_naukri_jobs())
    except Exception:
        logger.exception("Naukri scrape failed")

    new_jobs = [j for j in all_jobs if j.get("source_link") not in existing_links]
    logger.info(f"Found {len(all_jobs)} total, {len(new_jobs)} new after de-duping")

    for job in new_jobs:
        sheets.append_job(job)

    logger.info("Daily scrape complete")


def run_apply_loop_once():
    sheets = SheetsClient()
    to_apply = sheets.get_rows_marked_for_apply()
    if not to_apply:
        return

    logger.info(f"{len(to_apply)} job(s) marked 'Order to Apply' — attempting now")
    profile = sheets.get_profile()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=Config.HEADLESS)
        context = browser.new_context()

        # Load the logged-in Naukri session so one-click apply runs as the
        # actual candidate account instead of hitting a login wall. This is
        # just a cookie string the user captured from their own browser —
        # never a password.
        if Config.NAUKRI_COOKIES:
            context.add_cookies(
                parse_cookie_string(Config.NAUKRI_COOKIES, ".naukri.com")
            )

        page = context.new_page()

        for row_number, record in to_apply:
            app_link = record.get("Application Link") or record.get("Source Link")
            if not app_link:
                sheets.update_status(row_number, "Failed", notes="No application link")
                continue

            try:
                page.goto(app_link, timeout=30000)
            except Exception as exc:  # noqa: BLE001
                sheets.update_status(row_number, "Failed", notes=f"Could not open link: {exc}")
                continue

            if "naukri.com" in app_link:
                result = apply_naukri_one_click(page, profile)
            else:
                result = None

            if result is None:
                sheets.update_status(
                    row_number, "Manual Review Needed",
                    notes="External ATS link — outside automated form-filling scope",
                )
            elif result.success:
                sheets.update_status(row_number, "Applied", notes=result.notes, applied=True)
            elif result.missing:
                sheets.update_status(
                    row_number, "Pending Review",
                    notes=result.notes,
                    missing=", ".join(result.missing),
                )
            else:
                sheets.update_status(row_number, "Failed", notes=result.notes)

        browser.close()


def main():
    problems = Config.validate()
    for p in problems:
        logger.warning(f"Config issue: {p}")
    if not Config.GOOGLE_SHEET_ID or not Config.GOOGLE_CREDENTIALS_JSON:
        logger.error("GOOGLE_SHEET_ID / GOOGLE_CREDENTIALS_JSON are required — exiting")
        sys.exit(1)

    logger.info("✅ Job Application Bot initialized")
    logger.info(f"\U0001F4C5 Scheduled: Daily job scrape at {Config.SCRAPE_HOUR_IST}:00 IST")
    logger.info("\U0001F504 Starting continuous monitoring for 'Order to Apply' entries...")

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        run_daily_scrape,
        CronTrigger(hour=Config.SCRAPE_HOUR_IST, minute=0),
        id="daily_scrape",
    )
    scheduler.add_job(
        run_apply_loop_once,
        "interval",
        minutes=Config.APPLY_LOOP_MINUTES,
        id="apply_loop",
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
