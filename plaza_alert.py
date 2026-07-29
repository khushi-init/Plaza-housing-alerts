#!/usr/bin/env python3
"""
Plaza (newnewnew.space) new-listing EMAIL alert -- GitHub Actions version.
Runs ONE check per invocation; GitHub Actions handles the schedule.
The Gmail app password is read from the GMAIL_APP_PASSWORD repo secret.
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests

# ============================== CONFIG ==============================

ENDPOINT_URL = "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=nl_NL&page=0&sort=%2BreactionData.aangepasteTotaleHuurprijs"

SMTP_USER = "myhousingbot@gmail.com"
EMAIL_TO = "khushiii29991@gmail.com"

# Password comes from the GitHub secret, not from code.
SMTP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ONLY_REGION = "Nederland - Zuid-Holland"
ONLY_CITIES = []

STATE_FILE = "seen_listings.json"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SITE_BASE = "https://plaza.newnewnew.space"

# ===================================================================


def fetch_listings():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }
    resp = requests.get(ENDPOINT_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Response didn't contain a 'data' list of listings.")


def city_of(item):
    return (item.get("city") or {}).get("name") or item.get("gemeenteGeoLocatieNaam") or "?"


def region_of(item):
    return (item.get("regio") or {}).get("name", "")


def passes_filter(item):
    if ONLY_REGION and region_of(item) != ONLY_REGION:
        return False
    if ONLY_CITIES and city_of(item) not in ONLY_CITIES:
        return False
    return True


def describe(item):
    street = (item.get("street") or "").strip()
    nr = str(item.get("houseNumber") or "").strip()
    add = (item.get("houseNumberAddition") or "").strip()
    address = " ".join(p for p in [street, nr, add] if p).strip()
    city = city_of(item)
    rent = item.get("totalRent")
    rent_str = f"EUR {rent}/mo" if rent is not None else "rent n/a"
    dwelling = (item.get("dwellingType") or {}).get("name", "")
    zelf = "self-contained" if item.get("isZelfstandig") else "shared"
    toeslag = "huurtoeslag possible" if item.get("huurLigtOpOfOnderHuurtoeslaggrens") else "no huurtoeslag"
    postcode = (item.get("postalcode") or "").strip()
    loc = f"{address}, {postcode} {city}".strip().strip(",")
    url_key = item.get("urlKey")
    link = (f"{SITE_BASE}/en/availables-places/living-place/details/{url_key}"
            if url_key else f"{SITE_BASE}/aanbod/wonen")
    return f"{loc}\n   {rent_str} | {dwelling} | {zelf} | {toeslag}\n   {link}"


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)


def send_email(new_items):
    blocks = [describe(item) for item in new_items]
    body = "New Plaza listing(s):\n\n" + "\n\n".join(blocks)
    body += f"\n\nAll listings: {SITE_BASE}/aanbod/wonen"

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"[Plaza] {len(new_items)} new listing(s)"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())


def main():
    if not SMTP_PASSWORD:
        sys.exit("GMAIL_APP_PASSWORD secret is not set.")

    seen = load_seen()
    first_run = len(seen) == 0

    listings = [x for x in fetch_listings() if passes_filter(x)]
    ids_now = {str(x.get("id")): x for x in listings}
    new_ids = [i for i in ids_now if i not in seen]

    if new_ids and not first_run:
        new_items = [ids_now[i] for i in new_ids]
        print(f"{len(new_items)} new - emailing.")
        send_email(new_items)
    elif first_run:
        print("first run - recording current listings, no email.")
    else:
        print("no new listings.")

    seen.update(ids_now.keys())
    save_seen(seen)
    print(f"checked {len(listings)} listings, {len(new_ids)} new.")


if __name__ == "__main__":
    main()
