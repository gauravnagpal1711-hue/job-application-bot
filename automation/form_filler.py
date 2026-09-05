"""
Generic application-form auto-filler (Playwright) for Naukri.

Naukri's one-click apply and third-party ATS pages (Greenhouse, Lever,
Workday, etc.) vary in how their forms are structured. This module handles
the common case (Naukri one-click) and does a best-effort generic fill for
anything else by matching visible <label> text against the profile dict's
keys. Any field it cannot confidently match is reported back so the row
gets flagged "Missing Info Required" in the tracker instead of being
submitted with guessed/blank data.
"""
from __future__ import annotations

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger(__name__)


class ApplyResult:
    def __init__(self, success: bool, notes: str = "", missing: list[str] | None = None):
        self.success = success
        self.notes = notes
        self.missing = missing or []


def apply_naukri_one_click(page: Page, profile: dict) -> ApplyResult:
    try:
        apply_btn = page.query_selector("#apply-button, button.apply-button")
        if not apply_btn:
            return ApplyResult(False, notes="No one-click Apply button found — may already be applied or external link")

        apply_btn.click()
        page.wait_for_timeout(2000)

        # Naukri sometimes opens a "chatbot" style Q&A modal for missing info
        missing = _fill_visible_form_fields(page, profile)
        if missing:
            return ApplyResult(False, notes="Naukri asked follow-up questions not covered by profile", missing=missing)

        return ApplyResult(True, notes="Submitted via Naukri one-click apply")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Naukri one-click apply failed")
        return ApplyResult(False, notes=f"Error: {exc}")


def _fill_visible_form_fields(page: Page, profile: dict) -> list[str]:
    """Best-effort: for every visible text input/textarea/select with an
    associated <label>, try to match the label text against a profile key
    (case-insensitive substring match) and fill it in. Returns the list of
    field labels it could NOT match, so the caller can flag them."""
    missing: list[str] = []

    inputs = page.query_selector_all("input[type='text'], input[type='email'], input[type='tel'], textarea, select")
    for field in inputs:
        try:
            field_id = field.get_attribute("id")
            label_text = ""
            if field_id:
                label_el = page.query_selector(f"label[for='{field_id}']")
                if label_el:
                    label_text = label_el.inner_text().strip()

            if not label_text:
                continue

            matched_value = None
            for key, value in profile.items():
                if key.lower() in label_text.lower() or label_text.lower() in key.lower():
                    matched_value = value
                    break

            if matched_value:
                tag = field.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    field.select_option(label=matched_value)
                else:
                    field.fill(matched_value)
            elif not field.input_value():
                missing.append(label_text)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not process a form field: {exc}")

    return missing
