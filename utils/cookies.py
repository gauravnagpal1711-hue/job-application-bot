"""
Small helper for turning a raw browser "Cookie" header string (the kind you
copy from DevTools → Application/Storage → Cookies) into the list-of-dicts
format Playwright's `context.add_cookies()` expects.

This exists so a site session can be handed to the bot as a single env var
(a cookie string) instead of a username/password — the bot never needs your
actual password for Naukri or LinkedIn, only a copy of an already-logged-in
session, which you capture yourself and can revoke/rotate independently by
just logging out.
"""
from __future__ import annotations


def parse_cookie_string(cookie_str: str, domain: str) -> list[dict]:
    """Parse "name1=value1; name2=value2" into Playwright cookie dicts for
    the given domain. Empty/garbled segments are skipped rather than
    raising, so one bad copy-paste doesn't crash the whole apply loop."""
    cookies: list[dict] = []
    if not cookie_str:
        return cookies

    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, value = part.partition("=")
        name, value = name.strip(), value.strip()
        if not name:
            continue
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
        })
    return cookies
