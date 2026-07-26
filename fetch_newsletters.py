#!/usr/bin/env python3
"""
fetch_newsletters.py

The non-AI "tool" half of the newsletter-digest skill.

What it does, deterministically (no AI involved in this file):
  1. Reads an allowlist of sender email addresses from a text file.
  2. Authenticates to Gmail via OAuth (Gmail API, read-only scope).
  3. Searches for messages from those senders within the last N days.
  4. Extracts the plain-text body of each message.
  5. Writes one .txt file per newsletter into an output folder, plus a
     manifest.json summarizing what was fetched.

Note: the output folder is wiped and recreated on every run, so it always
reflects exactly the current query results -- no stale files pile up from
newsletters that have since aged out of the day window.

Claude (via the skill) is only supposed to READ what this script produces
and summarize it -- it should never guess at senders, dates, or Gmail
query syntax itself. That separation is the whole point of the design.

Usage:
    python3 fetch_newsletters.py --senders senders.txt --days 7 --output fetched
"""

import argparse
import base64
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only scope: this script can never send, delete, or modify email.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def parse_args():
    p = argparse.ArgumentParser(description="Fetch newsletter emails from the last N days.")
    p.add_argument("--senders", default="senders.txt",
                    help="Path to a text file, one sender email per line.")
    p.add_argument("--days", type=int, default=7,
                    help="How many days back to search (default: 7).")
    p.add_argument("--output", default="fetched",
                    help="Directory to write fetched newsletter files into.")
    p.add_argument("--credentials", default="credentials.json",
                    help="Path to the OAuth client secret file from Google Cloud Console.")
    p.add_argument("--token", default="token.json",
                    help="Path where the cached OAuth token is stored after first login.")
    return p.parse_args()


def load_senders(path):
    """Read sender addresses from a file, ignoring blank lines and lines starting with #."""
    if not os.path.exists(path):
        sys.exit(f"ERROR: senders file not found: {path}")
    senders = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                senders.append(line)
    if not senders:
        sys.exit(f"ERROR: no senders listed in {path}")
    return senders


def get_credentials(credentials_path, token_path):
    """
    Handles the OAuth dance. First run: opens a browser for you to grant
    read-only Gmail access, then caches a token so you don't have to log
    in again every time. This is standard boilerplate for the Gmail API --
    you won't need to touch this function.
    """
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                sys.exit(
                    f"ERROR: {credentials_path} not found.\n"
                    "Download it from Google Cloud Console (APIs & Services > "
                    "Credentials > OAuth client ID > Desktop app) and place it here."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            # Opens a local server and (tries to) launch your browser.
            # If a browser doesn't open automatically, copy the printed
            # URL into any browser -- WSL2 forwards localhost to Windows.
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


def build_query(senders, days):
    """Builds a Gmail search query string, e.g.:
    after:2026/07/17 (from:foo@bar.com OR from:baz@qux.com)
    """
    since = datetime.now() - timedelta(days=days)
    date_str = since.strftime("%Y/%m/%d")
    sender_clause = " OR ".join(f"from:{s}" for s in senders)
    return f"after:{date_str} ({sender_clause})"


def strip_html(html):
    """Very small HTML-to-text fallback for newsletters sent as HTML-only."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_body(payload):
    """
    Gmail messages are structured as a tree of MIME parts. This walks the
    tree looking for a text/plain part first, falling back to text/html.
    """
    def decode(data):
        return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("UTF-8", errors="replace")

    if "parts" in payload:
        plain, html = None, None
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            body_data = part.get("body", {}).get("data")
            if mime == "text/plain" and body_data and not plain:
                plain = decode(body_data)
            elif mime == "text/html" and body_data and not html:
                html = decode(body_data)
            elif "parts" in part:
                nested = extract_body(part)
                if nested:
                    return nested
        if plain:
            return plain
        if html:
            return strip_html(html)
        return ""
    else:
        data = payload.get("body", {}).get("data")
        if not data:
            return ""
        text = decode(data)
        if payload.get("mimeType") == "text/html":
            return strip_html(text)
        return text


def header_value(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def safe_filename(s, max_len=60):
    s = re.sub(r"[^\w\s-]", "", s).strip().replace(" ", "_")
    return s[:max_len] if s else "untitled"


def reset_output_dir(path):
    """
    Wipes and recreates the output directory so every run starts from a
    clean slate. Without this, a newsletter that ages out of the day
    window would leave its stale .txt file behind forever, un-tracked by
    manifest.json (which IS fully regenerated each run). This makes the
    folder's contents always match exactly what the current run fetched.
    """
    abs_path = os.path.abspath(path)
    cwd = os.path.abspath(os.getcwd())

    # Guard rail: refuse to wipe the current directory or filesystem root
    # in case --output is ever passed as "." or "/" by mistake.
    if abs_path in (cwd, os.path.abspath(os.sep)):
        sys.exit(
            f"ERROR: refusing to clear '{path}' -- it resolves to your "
            "current directory or filesystem root. Use a dedicated output "
            "folder (e.g. 'fetched')."
        )

    if os.path.exists(abs_path):
        shutil.rmtree(abs_path)
    os.makedirs(abs_path)


def main():
    args = parse_args()
    senders = load_senders(args.senders)
    creds = get_credentials(args.credentials, args.token)
    service = build("gmail", "v1", credentials=creds)

    query = build_query(senders, args.days)
    print(f"Gmail query: {query}")

    reset_output_dir(args.output)

    message_ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=query, pageToken=page_token
        ).execute()
        message_ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Found {len(message_ids)} matching message(s).")

    manifest = []
    for msg_id in message_ids:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = msg["payload"].get("headers", [])
        subject = header_value(headers, "Subject") or "(no subject)"
        sender = header_value(headers, "From")
        date_hdr = header_value(headers, "Date")

        body = extract_body(msg["payload"])

        date_slug = datetime.fromtimestamp(int(msg["internalDate"]) / 1000).strftime("%Y-%m-%d")
        fname = f"{date_slug}_{safe_filename(sender)}_{safe_filename(subject)}.txt"
        fpath = os.path.join(args.output, fname)

        with open(fpath, "w") as f:
            f.write(f"From: {sender}\nSubject: {subject}\nDate: {date_hdr}\n\n{body}")

        manifest.append({
            "file": fname,
            "from": sender,
            "subject": subject,
            "date": date_hdr,
        })
        print(f"  wrote {fname}")

    with open(os.path.join(args.output, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Done. {len(manifest)} newsletter(s) written to {args.output}/")


if __name__ == "__main__":
    main()