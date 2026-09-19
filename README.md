# Plaza Alert

Email notifier for new housing listings on [Plaza](https://plaza.newnewnew.space) (newnewnew.space).

It polls the Plaza listings API, compares against listings it has already seen, and
emails you the moment a new one shows up. It only reads public listing data — it
never logs in or interacts with the site.

## How it runs

This bot runs automatically via **GitHub Actions** (see
[.github/workflows/check.yml](.github/workflows/check.yml)), on a schedule (every 5
minutes). Each run:

1. Fetches the current listings.
2. Compares them against [seen_listings.json](seen_listings.json) (committed back to
   the repo after each run, so state persists between runs).
3. Emails any new listings to the configured address.

The Gmail App Password used to send mail is stored as the `GMAIL_APP_PASSWORD`
repository secret (Settings → Secrets and variables → Actions) — it is never
hardcoded in the source.

## Configuration

Edit the constants at the top of [plaza_alert.py](plaza_alert.py):

- `ENDPOINT_URL` — the Plaza listings API endpoint (copied from the browser Network
  tab; keep its query filters).
- `SMTP_USER` / `EMAIL_TO` — sending and receiving Gmail addresses.
- `ONLY_REGION` — only email about listings in this region. Set to `""` for every
  region.
- `ONLY_CITIES` — optional extra narrowing by city, e.g. `["Delft", "Rijswijk"]`.
  Leave as `[]` for the whole region.

## Running it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GMAIL_APP_PASSWORD="your 16-character app password"
python3 plaza_alert.py
```

The first run only records the current listings (no email); after that, each run
emails about anything new since the last run.

### Setting up the Gmail App Password

1. Turn on 2-Step Verification: https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords — name it
   "plaza", copy the 16-character password (not your normal Gmail password).
3. For GitHub Actions, add it as a repo secret named `GMAIL_APP_PASSWORD`:
   ```bash
   gh secret set GMAIL_APP_PASSWORD
   ```
4. For local runs, export it as an environment variable (see above) — don't paste it
   into the source file.

## Disclaimer

Personal, unofficial script — not affiliated with Plaza or newnewnew.space. Polls at
a low frequency to be a polite API consumer.
