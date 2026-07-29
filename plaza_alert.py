

#!/usr/bin/env python3
"""
Plaza (newnewnew.space) new-listing EMAIL alert -- tuned to the real data format.

Polls the Plaza listings endpoint and emails you the moment a NEW listing appears.
It only READS. It does not log in or react to anything.

--------------------------------------------------------------------------
SETUP
--------------------------------------------------------------------------
1. Gmail App Password:
   a. Turn on 2-Step Verification: https://myaccount.google.com/security
   b. Create an App Password: https://myaccount.google.com/apppasswords
      Name it "plaza", copy the 16-character password (NOT your normal password).

2. Fill in the CONFIG section below (endpoint URL, your Gmail, the app password).

3. Run it in the VS Code terminal:  python3 plaza_alert.py
   The FIRST run is silent (records what's already listed); after that you get
   emailed only about listings posted AFTER you start it.
--------------------------------------------------------------------------
"""

import json
import os
import smtplib
import sys
import time
from email.mime.text import MIMEText

import requests

# ========================== CONFIG - EDIT THESE ==========================

# The listings endpoint URL you copied from the Network tab (keep its filters,
# e.g. the Zuid-Holland region). Paste it between the quotes.
ENDPOINT_URL = "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=nl_NL&page=0&sort=%2BreactionData.aangepasteTotaleHuurprijs"

# --- Gmail settings ---
SMTP_USER = "myhousingbot@gmail.com"        # the Gmail that SENDS the mail
SMTP_PASSWORD = "[REDACTED-ROTATED]"  # App Password, NOT your login
EMAIL_TO = "khushiii29991@gmail.com"         # where alerts go (can be the same)

# How often to check, in seconds. 60 is polite.
POLL_SECONDS = 60

# This endpoint returns listings from ALL regions, so we filter here.
# Only email about listings in this region. Set to "" to get EVERY region.
ONLY_REGION = "Nederland - Zuid-Holland"

# Optional extra narrowing by city. Leave empty [] to get the whole region above.
# Example to restrict to Delft + Rijswijk only:  ["Delft", "Rijswijk"]
ONLY_CITIES = []

STATE_FILE = "seen_listings.json"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SITE_BASE = "https://plaza.newnewnew.space"

# =========================================================================


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
    # This site nests the listings under "data".
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Response didn't contain a 'data' list of listings.")


def city_of(item):
    city = item.get("city") or {}
    return city.get("name") or item.get("gemeenteGeoLocatieNaam") or "?"


def describe(item):
    street = item.get("street", "").strip()
    nr = str(item.get("houseNumber", "")).strip()
    add = (item.get("houseNumberAddition") or "").strip()
    address = " ".join(p for p in [street, nr, add] if p).strip()

    city = city_of(item)
    rent = item.get("totalRent")
    rent_str = f"EUR {rent}/mo" if rent is not None else "rent n/a"

    dwelling = (item.get("dwellingType") or {}).get("name", "")
    zelfstandig = "self-contained" if item.get("isZelfstandig") else "shared"
    toeslag = "huurtoeslag possible" if item.get("huurLigtOpOfOnderHuurtoeslaggrens") else "no huurtoeslag"

    url_key = item.get("urlKey")
    postcode = (item.get("postalcode") or "").strip()
    loc = f"{address}, {postcode} {city}".strip().strip(",")
    link = (f"{SITE_BASE}/en/availables-places/living-place/details/{url_key}"
            if url_key else f"{SITE_BASE}/aanbod/wonen")
    return (f"{loc}\n"
            f"   {rent_str} | {dwelling} | {zelfstandig} | {toeslag}\n"
            f"   {link}")

def region_of(item):
    return (item.get("regio") or {}).get("name", "")


def passes_filter(item):
    if ONLY_REGION and region_of(item) != ONLY_REGION:
        return False
    if ONLY_CITIES and city_of(item) not in ONLY_CITIES:
        return False
    return True


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
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
    if ENDPOINT_URL.startswith("PASTE"):
        sys.exit("Set ENDPOINT_URL first (paste the URL from the Network tab).")
    if SMTP_PASSWORD == "your_16_char_app_password":
        sys.exit("Set SMTP_PASSWORD to your Gmail App Password first.")

    seen = load_seen()
    first_run = len(seen) == 0
    print(f"Started. Checking every {POLL_SECONDS}s. Alerts -> {EMAIL_TO}")
    if ONLY_REGION:
        print(f"Filtering to region: {ONLY_REGION}")
    if ONLY_CITIES:
        print(f"Filtering to cities: {', '.join(ONLY_CITIES)}")
    if first_run:
        print("(first run - recording current listings, no emails this time)")

    while True:
        try:
            listings = [x for x in fetch_listings() if passes_filter(x)]
            ids_now = {str(x.get("id")): x for x in listings}
            new_ids = [i for i in ids_now if i not in seen]

            if new_ids and not first_run:
                new_items = [ids_now[i] for i in new_ids]
                print(f"{time.strftime('%H:%M:%S')}  {len(new_items)} new - emailing.")
                try:
                    send_email(new_items)
                except Exception as mail_err:
                    print("  ! email failed:", mail_err)

            seen.update(ids_now.keys())
            save_seen(seen)
            first_run = False
            print(f"{time.strftime('%H:%M:%S')}  checked, {len(listings)} listings, "
                  f"{len(new_ids)} new.")

        except Exception as err:
            print(f"{time.strftime('%H:%M:%S')}  error: {err}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()