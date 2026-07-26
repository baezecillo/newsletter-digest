---
name: newsletter-digest
description: Fetches newsletter emails from a configured allowlist of senders from the last N days (default 7) and produces a structured digest summarizing each one. Use this when the user asks for their newsletter digest, to catch up on recent newsletters, or to summarize what's come in from their subscribed newsletters.
---

# Newsletter Digest

## Purpose

Turn a pile of newsletter emails from the last N days into one readable digest, without
guessing at which emails count or making up content that isn't in the source text.

Retrieval and filtering are handled entirely by `fetch_newsletters.py` (a deterministic,
non-AI script) so the sender allowlist, date window, and Gmail query syntax are never left
to interpretation. Your job is only to read what the script produced and summarize it.

## Workflow

1. **Determine parameters.** Default to `--days 7`. If the user specifies a different window
   ("last 3 days", "since Monday"), pass that instead. Default output directory is `fetched/`,
   default sender list is `senders.txt`.

2. **Run the fetch script** using the project's virtualenv interpreter directly (don't rely on
   `source venv/bin/activate`, since each Bash call may be a fresh shell):

   ```bash
   ./venv/bin/python3 fetch_newsletters.py --senders senders.txt --days 7 --output fetched
   ```

   If this fails because `credentials.json` is missing or OAuth hasn't been completed yet, stop
   and tell the user exactly what's missing — do not attempt to fetch emails another way.

3. **Read `fetched/manifest.json`** to get the list of fetched newsletters (filename, sender,
   subject, date). This is your index; don't rely on directory listing order alone.

4. **Read each fetched `.txt` file** and summarize it using only the content in that file:
   - 2-4 bullet points capturing the substantive claims, findings, or arguments in the piece.
   - If a newsletter is purely administrative (subscription confirmation, "welcome" email,
     "you're on the list") with no real editorial content, label it as administrative and skip
     the bullet summary — do not invent content to fill it out.
   - Never add facts, opinions, or context that aren't present in the source text.

5. **Compile one `digest.md`** file, newest first, using this structure per entry:

   ```markdown
   ## <Subject>
   **From:** <sender> · **Date:** <date>

   - <bullet>
   - <bullet>
   - <bullet>
   ```

   Start the file with a header stating the date range covered and total count, e.g.
   `# Newsletter Digest — 2026-07-17 to 2026-07-24 (22 newsletters)`.

6. **Save the digest** to `digests/<YYYY-MM-DD>-digest.md` (create the `digests/` folder if it
   doesn't exist) and tell the user the file path and a one-line count summary
   (e.g. "18 substantive newsletters summarized, 4 administrative emails skipped").

## Guardrails

- Do not fetch or query Gmail directly yourself — always go through `fetch_newsletters.py`.
- Do not summarize a newsletter you haven't actually read from its fetched file.
- Do not fabricate senders, dates, or counts; report exactly what the manifest and script
  output say.