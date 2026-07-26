# CLAUDE.md

Context for Claude Code working in this repository.

## What this project is

A CMU 17-636 DevOps assignment (Agentic Engineering, Assignment 5, option 1: write a new
skill). The deliverable is a Claude Code **skill** — `.claude/skills/newsletter-digest/SKILL.md`
— that fetches newsletter emails from a fixed sender list over the last N days and produces a
readable digest. The point of the assignment is to compare this skill-driven workflow against
a plain, undirected prompt asking for the same thing, and analyze the quality difference.

## Architecture / design intent

- `fetch_newsletters.py` is the **non-AI tool**. It authenticates to Gmail via OAuth, runs a
  deterministic query (sender allowlist + date window), extracts message bodies, and writes
  everything to `fetched/` plus `fetched/manifest.json`. It does not use AI in any way.
- `.claude/skills/newsletter-digest/SKILL.md` is the **workflow spec**. It tells Claude to run
  the script, read only `fetched/manifest.json` and the `.txt` files it lists, and summarize
  strictly from that content — never to query Gmail directly or invent content.
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
