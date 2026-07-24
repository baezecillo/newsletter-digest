# Setup: fetch_newsletters.py (Gmail API, OAuth)

## 1. Google Cloud Console (one-time, manual)

1. Go to `https://console.cloud.google.com/` and create a new project (any name, e.g. "newsletter-digest").
2. Go to **APIs & Services > Library**, search for "Gmail API", click it, click **Enable**.
3. Go to **APIs & Services > OAuth consent screen**.
   - User type: External.
   - Fill in app name, your email as support/contact.
   - Scopes: add `.../auth/gmail.readonly`.
   - Test users: add your own Gmail address.
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Desktop app**.
   - Download the JSON file, rename it `credentials.json`, and put it in this project folder.

## 2. WSL2 Ubuntu setup

```bash
git clone https://github.com/baezecillo/newsletter-digest.git
cd newsletter-digest
python3 -m venv venv          # creates an isolated Python environment
source venv/bin/activate      # switches your current shell session into that environment
pip install -r requirements.txt
```

## 3. Edit `senders.txt`

Replace the placeholder addresses with your real newsletter senders (one per line).

## 4. First run (authenticates + fetches)

```bash
python3 fetch_newsletters.py --senders senders.txt --days 7 --output fetched
```

- A browser tab should open asking you to log in and grant read-only access.
- If it doesn't open automatically in WSL2, copy the URL printed in the terminal into any browser — WSL2 forwards `localhost` to Windows, so the redirect back to the script will still work.
- After you approve, a `token.json` is cached so you won't have to log in again (it auto-refreshes).

You should see output like:

```txt
Gmail query: after:2026/07/17 (from:newsletter@example.com OR from:digest@another-example.com)
Found 3 matching message(s).
  wrote 2026-07-18_newsletter_example_com_Weekly_Roundup.txt
  ...
Done. 3 newsletter(s) written to fetched/
```

## 5. Files NOT to commit to git

Add to `.gitignore`:

```txt
credentials.json
token.json
venv/
fetched/
```

`credentials.json` and `token.json` both grant access to your inbox — keep them out of version control.
