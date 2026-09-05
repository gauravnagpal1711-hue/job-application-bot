"""
Central configuration loader.

All secrets/config come from environment variables (set as Railway
Variables in production, or a local .env file for development — never
committed to git).
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()  # no-op in production; picks up a local .env file in dev


class Config:
    # --- Google Sheets ---
    GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
    GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

    SHEET_PROFILE_TAB = os.environ.get("SHEET_PROFILE_TAB", "Sheet1")
    SHEET_TRACKER_TAB = os.environ.get("SHEET_TRACKER_TAB", "Sheet2")

    # --- LinkedIn ---
    LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "")

    # --- Naukri (optional separate login) ---
    NAUKRI_EMAIL = os.environ.get("NAUKRI_EMAIL", LINKEDIN_EMAIL)
    NAUKRI_PASSWORD = os.environ.get("NAUKRI_PASSWORD", "")

    # --- Search parameters ---
    JOB_KEYWORDS = os.environ.get("JOB_KEYWORDS", "HR Manager,Talent Acquisition,HRBP")
    JOB_LOCATIONS = os.environ.get("JOB_LOCATIONS", "Delhi NCR,Remote")

    # --- Scheduling ---
    SCRAPE_HOUR_IST = int(os.environ.get("SCRAPE_HOUR_IST", "11"))
    APPLY_LOOP_MINUTES = int(os.environ.get("APPLY_LOOP_MINUTES", "5"))

    # --- Misc ---
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    HEADLESS = os.environ.get("HEADLESS", "true").lower() != "false"

    @classmethod
    def google_credentials_dict(cls) -> dict:
        """Parse the GOOGLE_CREDENTIALS_JSON env var (the full service-account
        JSON key, pasted as a single Railway variable) into a dict."""
        if not cls.GOOGLE_CREDENTIALS_JSON:
            raise RuntimeError(
                "GOOGLE_CREDENTIALS_JSON is not set. Paste the entire contents "
                "of the Google service-account JSON key as this variable's value."
            )
        return json.loads(cls.GOOGLE_CREDENTIALS_JSON)

    @classmethod
    def validate(cls) -> list:
        """Return a list of human-readable problems with the current config
        (empty list = config looks OK). Called at startup so failures show
        up clearly in Railway logs instead of as a stack trace."""
        problems = []
        if not cls.GOOGLE_SHEET_ID:
            problems.append("GOOGLE_SHEET_ID is not set")
        if not cls.GOOGLE_CREDENTIALS_JSON:
            problems.append("GOOGLE_CREDENTIALS_JSON is not set")
        else:
            try:
                cls.google_credentials_dict()
            except Exception as exc:  # noqa: BLE001
                problems.append(f"GOOGLE_CREDENTIALS_JSON is not valid JSON: {exc}")
        if not cls.LINKEDIN_EMAIL or not cls.LINKEDIN_PASSWORD:
            problems.append(
                "LINKEDIN_EMAIL / LINKEDIN_PASSWORD not set — LinkedIn scraping "
                "and auto-apply will be skipped"
            )
        return problems
