# Newsletter Digest Skill

CMU 17-636 (DevOps) Assignment 5 — Agentic Engineering, Option 1: a new Claude Code skill that
specifies a workflow, backed by a non-AI tool.

This project fetches newsletter emails from a configured list of senders over the last N days
and produces a readable, per-email digest — without letting Claude guess at senders, dates, or
Gmail query syntax itself. See `design.md` for the design rationale and `evaluation.md` for how
this was evaluated against a plain-prompt baseline.

## How it works

Retrieval and filtering are entirely deterministic, non-AI code: `fetch_newsletters.py`
authenticates to Gmail via OAuth (read-only scope), queries each configured sender individually
over a fixed day window, extracts each message's plain-text body, and writes one `.txt` file per
newsletter into `fetched/`, plus a `fetched/manifest.json` index recording every sender checked
(including senders with zero matches) and every email found.

Summarization is the only part left to the model. `.claude/skills/newsletter-digest/SKILL.md`
tells Claude Code to run the script, read only what it produced, write one summary entry per
email (never merging multiple issues from the same sender into one blended summary), explicitly
label administrative emails (subscription confirmations, "welcome" emails) instead of inventing
content for them, and confirm every configured sender was checked — with either a summary or a
"no new issue this week" note. The result is saved to `digests/<date>-digest.md`.

## Repo structure

```text
.
├── .claude/skills/newsletter-digest/SKILL.md   the workflow spec Claude Code discovers and runs
├── fetch_newsletters.py                        the non-AI retrieval script
├── requirements.txt                             Python dependencies
├── senders.txt.example                          template sender allowlist (copy to senders.txt)
├── credentials.json.example                     template OAuth client config (copy to credentials.json)
├── SETUP.md                                     Google Cloud Console + local environment setup
├── CLAUDE.md                                     project context for Claude Code
├── design.md                                     assignment deliverable: design + rationale
├── evaluation.md                                 assignment deliverable: evaluation + analysis
├── .gitignore / .gitattributes
└── README.md                                     this file
```

Not tracked in git (see `.gitignore`): `senders.txt` and `credentials.json` (personal data and
secrets — use the `.example` templates), `token.json` (cached OAuth token), and `fetched/` /
`digests/` (regenerated output that would otherwise reveal which newsletters are subscribed to).

## Setup

Follow `SETUP.md` for the one-time Google Cloud Console steps (enabling the Gmail API, creating
an OAuth client, downloading `credentials.json`) and the local Python environment setup.

Quick version, once `credentials.json` and `senders.txt` are in place:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 fetch_newsletters.py --senders senders.txt --days 7 --output fetched
```

## Usage

With the skill in place, prompt Claude Code naturally, e.g.:

```text
Give me my newsletter digest
```

It will run the fetch script, read the results, and write `digests/<date>-digest.md`.

## Assignment deliverables

- `design.md` — what this project started with (a plain-prompt Cowork automation), what was
  built instead, and the design rationale.
- `evaluation.md` — how the skill was evaluated against that baseline, the results, and analysis
  tying those results back to the design.
