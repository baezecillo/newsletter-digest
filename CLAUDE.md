# CLAUDE.md

Context for Claude Code working in this repository.

## What this project is

A CMU 17-636 DevOps assignment (Agentic Engineering, Assignment 5, option 1: write a new
skill). The deliverable is a Claude Code **skill** — `.claude/skills/newsletter-digest/SKILL.md`
— that fetches newsletter emails from a fixed sender list over the last N days and produces a
readable digest. The point of the assignment is to compare this skill-driven workflow against
a plain, undirected prompt asking for the same thing, and analyze the quality difference.

## Architecture / design intent

- `fetch_newsletters.py` is the **non-AI tool**. It authenticates to Gmail via OAuth and queries
  each configured sender individually (so zero-match senders are recorded, not just omitted).
  Addresses are quoted in each query, but that alone does not reliably stop Gmail from matching
  a base address against its own plus-tagged alias (e.g. `swyx@substack.com` vs.
  `swyx+ainews@substack.com`) — the real guarantee against that is downstream deduplication by
  message ID, with any overlap explicitly recorded rather than silently absorbed. The script
  extracts message bodies and writes everything to `fetched/` plus `fetched/manifest.json`.
  Dates are computed in an explicit, fixed timezone (`--timezone`, default `America/New_York`)
  rather than the host machine's local timezone, so results are reproducible regardless of
  where the script runs. It does not use AI in any way.
- `fetched/manifest.json` has three top-level keys: `senders_checked` (every configured sender
  with its raw match count, including `0`), `newsletters` (one entry per unique fetched email,
  already deduplicated across sender queries, each with `date` (raw header), `date_local` (ISO,
  fixed timezone, for sorting), and `date_display` (a precomputed, ready-to-copy display string
  like `"Tue, 21 Jul 2026"` — the skill must use this verbatim rather than reformatting
  `date_local` itself), and `sender_overlaps` (any message that matched more than one configured
  sender's query, typically two addresses aliasing the same inbox). These exist so the skill can
  positively confirm every sender was checked, display dates with zero interpretation left to
  the model, and treat any cross-sender overlap as a fact the script recorded rather than
  something the model has to notice and explain in prose.
- `.claude/skills/newsletter-digest/SKILL.md` is the **workflow spec**. It tells Claude to run
  the script, read `fetched/manifest.json`, and summarize strictly from the fetched `.txt`
  files — never to query Gmail directly, invent content, or merge multiple emails from the
  same sender into one blended entry.
- This split is the core design principle: retrieval/filtering is deterministic and
  reproducible; only summarization is left to the model.

## Working in this repo

- `fetch_newsletters.py` wipes and recreates `fetched/` on every run (see `reset_output_dir`).
  Don't assume old fetched files persist between runs — `manifest.json` is always a full,
  fresh rebuild, not an append.
- Run the script via the project virtualenv directly: `./venv/bin/python3 fetch_newsletters.py
  --senders senders.txt --days 7 --output fetched`. Don't rely on `source venv/bin/activate`
  in generated commands — each shell invocation may not persist activation.
- `senders.txt` and `credentials.json` are gitignored and contain real personal data /
  secrets. Their `.example` counterparts (`senders.txt.example`, `credentials.json.example`)
  are the tracked templates — edit those when changing structure, not the real files.
- `token.json` is a cached OAuth token; never print or log its contents.
- Never read, print, or otherwise expose the contents of `credentials.json` or `token.json`
  in any output, commit message, or summary.

## Assignment deliverables (for context, not code)

- `design.md` and `evaluation.md` (repo root) document the design rationale and the
  skill-vs-plain-prompt comparison required by the assignment. These are written docs, not
  something Claude Code needs to keep in sync with the code automatically.
