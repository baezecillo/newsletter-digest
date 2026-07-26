---
name: newsletter-digest
description: Fetches newsletter emails from a configured allowlist of senders from the last N days (default 7) and produces a structured digest summarizing each one. Use this when the user asks for their newsletter digest, to catch up on recent newsletters, or to summarize what's come in from their subscribed newsletters.
---

# Newsletter Digest

## Purpose

Turn a pile of newsletter emails from the last N days into one readable digest, without
guessing at which emails count or making up content that isn't in the source text.

Retrieval and filtering are handled entirely by `fetch_newsletters.py` (a deterministic,
non-AI script) so the sender allowlist, date window, timezone, and Gmail query syntax are
never left to interpretation. Your job is only to read what the script produced and
summarize it.

## Workflow

1. **Determine parameters.** Default to `--days 7`. If the user specifies a different window
   ("last 3 days", "since Monday"), pass that instead. Default output directory is `fetched/`,
   default sender list is `senders.txt`, default timezone is `America/New_York` (pass
   `--timezone` only if the user asks for a different one).

2. **Run the fetch script** using the project's virtualenv interpreter directly (don't rely on
   `source venv/bin/activate`, since each Bash call may be a fresh shell):

   ```bash
   ./venv/bin/python3 fetch_newsletters.py --senders senders.txt --days 7 --output fetched
   ```

   If this fails because `credentials.json` is missing or OAuth hasn't been completed yet, stop
   and tell the user exactly what's missing — do not attempt to fetch emails another way.

3. **Read `fetched/manifest.json`.** It has three parts:
   - `senders_checked`: every sender from `senders.txt`, each with a `count` of how many
     matching emails were found (including senders with `count: 0`). This is the authoritative
     record that every configured sender was actually checked, not just the ones with mail.
     Note that if two configured senders are aliases of the same inbox, their counts can each
     be nonzero for overlapping mail — that's expected and explained by `sender_overlaps` below,
     not a bug to work around.
   - `newsletters`: one entry per unique fetched email (filename, sender, subject, `date`,
     `date_local`, `date_display`, `matched_senders`). This is your index into the `.txt` files
     — don't rely on directory listing order. The script already deduplicates messages that
     matched more than one sender's query, so this list has no duplicate files.
     **Use `date_display` verbatim, character for character, as the `<date>` in every digest
     entry.** Do not reformat it, recompute it, or read the date from anywhere else (not the
     `.txt` file's header line, not `date`, not the email body). `date_display` is already a
     ready-to-use string (e.g. `"Tue, 21 Jul 2026"`) computed once by the script in the pinned
     timezone specifically so there is nothing left for you to interpret. Use `date_local` (the
     ISO field) only for sort order in step 5, never for display.
   - `sender_overlaps`: any message that matched more than one configured sender's query
     (almost always two addresses that are aliases of the same inbox). If this is non-empty, add
     one short note near the top of `digest.md` naming the overlapping senders — the script has
     already done the detection, so just report what it found rather than re-deriving it.

4. **Read each fetched `.txt` file** and summarize it using only the content in that file:
   - 2-4 bullet points capturing the substantive claims, findings, or arguments in the piece.
   - If a newsletter is purely administrative (subscription confirmation, "welcome" email,
     "you're on the list") with no real editorial content, label it as administrative and skip
     the bullet summary — do not invent content to fill it out.
   - Never add facts, opinions, or context that aren't present in the source text.
   - Keep one entry per email, even if the same sender has multiple issues this week — do not
     merge multiple emails into a single blended summary. Per-email traceability (which fact
     came from which specific issue) is a deliberate design choice; preserve it.

5. **Compile one `digest.md`** file, sorted strictly by `date_local` descending (newest first,
   no exceptions and no grouping by sender), using this structure per entry:

   ```markdown
   ## <Subject>
   **From:** <sender> · **Date:** <date>

   - <bullet>
   - <bullet>
   - <bullet>
   ```

   Start the file with a header stating the date range covered and how many of the configured
   senders had mail, e.g.
   `# Newsletter Digest — 2026-07-17 to 2026-07-24 (20 newsletters from 9/11 configured senders)`.

6. **Add a "No new issues this week" section** at the end of `digest.md` listing every sender
   from `senders_checked` with `count: 0`, e.g.:

   ```markdown
   ## No new issues this week
   - highgrowthengineer@substack.com
   ```

   If every sender had at least one issue, state that explicitly instead of omitting the
   section (e.g. "All 11 configured senders had at least one issue this week."). The point is
   that the digest always confirms the full sender list was checked — never just silent about
   senders with nothing to report.

7. **Save the digest** to `digests/<YYYY-MM-DD>-digest.md` (create the `digests/` folder if it
   doesn't exist) and tell the user the file path and a one-line count summary
   (e.g. "18 substantive newsletters summarized, 4 administrative emails skipped, 2 senders
   had no new issue this week").

## Guardrails

- Do not fetch or query Gmail directly yourself — always go through `fetch_newsletters.py`.
- Do not summarize a newsletter you haven't actually read from its fetched file.
- Do not fabricate senders, dates, or counts; report exactly what `manifest.json` and the
  script's console output say.
- Never compute, reformat, or paraphrase a date yourself — always copy `date_display` from
  `manifest.json` verbatim for what's shown, and `date_local` only for sorting. This is what
  keeps the digest's dates identical across repeated runs of the same fetched data.
- Always cross-check `digest.md` against `senders_checked` before telling the user you're done
  — every sender must be accounted for, either with newsletter entries or in the "no new
  issues" section.
