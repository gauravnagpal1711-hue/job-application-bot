"""
Wrapper around the two-tab Google Sheet:

  Sheet1 ("Credentials & Profile") — key/value pairs in columns A/B,
  one row per field (e.g. "Resume Link" | "https://drive.google.com/...").
  The bot reads this to fill application forms and to flag which fields
  are still missing.

  Sheet2 ("Job Applications Tracker") — one row per scraped job:
  Date Found | Company Name | Job Title | Location | Source Link |
  Application Link | Order to Apply | Status | Date Applied |
  Bot Notes | Missing Info Required
"""
from __future__ import annotations

import datetime as dt

import gspread
from google.oauth2.service_account import Credentials

from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

TRACKER_HEADERS = [
    "Date Found",
    "Company Name",
    "Job Title",
    "Location",
    "Source Link",
    "Application Link",
    "Order to Apply",
    "Status",
    "Date Applied",
    "Bot Notes",
    "Missing Info Required",
]


class SheetsClient:
    def __init__(self):
        creds = Credentials.from_service_account_info(
            Config.google_credentials_dict(), scopes=SCOPES
        )
        self._gc = gspread.authorize(creds)
        self._spreadsheet = self._gc.open_by_key(Config.GOOGLE_SHEET_ID)
        self.profile_ws = self._spreadsheet.worksheet(Config.SHEET_PROFILE_TAB)
        self.tracker_ws = self._spreadsheet.worksheet(Config.SHEET_TRACKER_TAB)

    # ---------- Profile / credentials (Sheet1) ----------

    def get_profile(self) -> dict:
        """Read the key/value profile sheet into a dict, e.g.
        {"Resume Link": "...", "HRBP Experience (years)": "5", ...}"""
        rows = self.profile_ws.get_all_values()
        profile = {}
        for row in rows:
            if len(row) >= 2 and row[0].strip():
                profile[row[0].strip()] = row[1].strip()
        return profile

    def find_missing_fields(self, profile: dict, required_fields: list[str]) -> list[str]:
        return [f for f in required_fields if not profile.get(f)]

    # ---------- Tracker (Sheet2) ----------

    def ensure_headers(self):
        first_row = self.tracker_ws.row_values(1)
        if first_row != TRACKER_HEADERS:
            self.tracker_ws.update("A1", [TRACKER_HEADERS])

    def get_tracker_rows(self) -> list[dict]:
        return self.tracker_ws.get_all_records()

    def get_existing_source_links(self) -> set[str]:
        records = self.get_tracker_rows()
        return {r.get("Source Link", "") for r in records if r.get("Source Link")}

    def append_job(self, job: dict):
        """job keys: company, title, location, source_link, application_link"""
        row = [
            dt.date.today().isoformat(),
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
            job.get("source_link", ""),
            job.get("application_link", ""),
            "",  # Order to Apply — left for the user
            "Pending Review",
            "",
            "",
            "",
        ]
        self.tracker_ws.append_row(row, value_input_option="USER_ENTERED")

    def get_rows_marked_for_apply(self) -> list[tuple[int, dict]]:
        """Returns (row_number, record) for rows where 'Order to Apply' == YES
        and Status isn't already Applied."""
        records = self.tracker_ws.get_all_records()
        out = []
        for idx, rec in enumerate(records, start=2):  # row 1 = headers
            order = str(rec.get("Order to Apply", "")).strip().upper()
            status = str(rec.get("Status", "")).strip()
            if order == "YES" and status not in ("Applied",):
                out.append((idx, rec))
        return out

    def update_status(self, row_number: int, status: str, notes: str = "",
                       missing: str = "", applied: bool = False):
        updates = {"Status": status}
        if notes:
            updates["Bot Notes"] = notes
        updates["Missing Info Required"] = missing
        if applied:
            updates["Date Applied"] = dt.date.today().isoformat()

        header = self.tracker_ws.row_values(1)
        for col_name, value in updates.items():
            if col_name in header:
                col_idx = header.index(col_name) + 1
                self.tracker_ws.update_cell(row_number, col_idx, value)
