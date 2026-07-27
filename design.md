# Design

## What I started with

I already had an ad hoc, prompt-driven newsletter digest running in Cowork: a scheduled task
(`weekly-newsletter-digest`, Sundays at 6 PM ET) whose entire "workflow" is a natural-language
prompt telling Claude which 11 newsletter senders to check and how to phrase a Gmail search
query, plus a companion Cowork artifact that live-fetches the last seven days of mail from each
sender and asks Claude, on page load, to summarize each one. There is no non-AI code anywhere
in that setup — retrieval, filtering, and summarization are all delegated to the model, re-derived
from scratch on every run, with nothing persisted between views. It works reasonably well, but it
has no deterministic core: the exact Gmail query, the date-window math, and the decision about
what counts as "this week's newsletters" are all re-inferred by the model every single time, from
a prompt, rather than fixed in code.

## What I designed

I built a Claude Code skill, `.claude/skills/newsletter-digest/SKILL.md`, backed by a standalone
Python script, `fetch_newsletters.py`. The script is the non-AI tool: it authenticates to Gmail
via OAuth (read-only scope), builds a Gmail search query from a sender allowlist (`senders.txt`)
and a day-count window, extracts the plain-text body of every matching message, and writes one
`.txt` file per newsletter into a `fetched/` directory along with a `manifest.json` index.
It deletes and recreates that directory on every run, so its contents always match exactly what
the current run found — no stale files accumulate as older newsletters age out of the day window.
None of this involves a model call; it is ordinary, testable Python that I can run and verify
independently of Claude entirely.

The skill itself is the thin layer on top: it tells Claude to invoke the script, read
`manifest.json` as the authoritative index of what was fetched, read each `.txt` file, and
summarize strictly from that content into a fixed markdown structure — one entry per newsletter,
2-4 bullet points, newest first. Critically, the skill also tells Claude what *not* to summarize:
if a fetched email is purely administrative (a subscription confirmation, a "welcome" email) with
no editorial content, it should be labeled as such rather than padded out with invented bullet
points. The compiled result is written to `digests/<date>-digest.md`, a durable file rather than
a live, re-computed view.

## Design rationale and agentic engineering principles

The central principle behind this design is separating the parts of the task that should be
deterministic from the parts that genuinely require judgment. Which emails count as newsletters,
what date range to search, and how to query Gmail are not judgment calls — they are exactly
specified by the sender allowlist and the day count, so I pushed all of that into ordinary code
where it can be tested and trusted to behave the same way every time. Summarizing the substance
of an article, by contrast, is exactly the kind of task a model is good at and code is not, so
that stayed with Claude. This split also bounds the model's exposure: it never touches the Gmail
API directly, never constructs a search query itself, and therefore has no opportunity to
misremember sender syntax or silently narrow the date window, the way an undirected prompt can.

A second principle is reducing the model's degrees of freedom through an explicit workflow rather
than trusting it to infer a reasonable process from a one-line request. The original artifact's
prompt tells Claude to summarize newsletters but says nothing about what to do with an email that
has no real content, so it is left to guess. The skill instead states the administrative-versus-
substantive distinction as an explicit rule, which removes an entire class of plausible-sounding
but ungrounded output.

A third principle is treating the automation's output as a durable artifact rather than a
transient answer. The script's reset-and-rebuild behavior and the skill's decision to write a
dated file to `digests/` both reflect the same idea: the result of running this automation should
be something that persists, can be diffed, can be checked into version control's history (with
the sender list and credentials appropriately excluded), and does not depend on any particular
chat session or live browser view still being open. Finally, the design follows least-privilege
practice by scoping the OAuth grant to `gmail.readonly`, so the automation is structurally
incapable of modifying or sending mail, regardless of what either the script or the model is
told to do.
