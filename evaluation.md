# Evaluation

## How I evaluated it

I ran the skill in Claude Code with the prompt "Give me my newsletter digest" on 2026-07-26. It
discovered the skill, ran `fetch_newsletters.py`, fetched 20 matching emails across the 11
configured senders for the prior seven days, and produced `digests/2026-07-26-digest.md`: 14
newsletters summarized with substantive bullet points and 6 correctly labeled as administrative
(subscription confirmations and welcome emails) with no fabricated content.

As the "off the shelf" comparison point, I used the pre-existing Cowork artifact this project's
skill was designed to improve on: a plain-prompt automation with no dedicated script, which calls
the Gmail connector live and asks Claude, per sender, to write a short summary, capped at six
issues per sender per week, with no instruction covering what to do with emails that have no real
content. I opened this artifact twice on the same day, about 19 minutes apart (5:49 PM and 6:08
PM), each covering essentially the same seven-day window, and exported both to PDF. The first
export only preserved 2 of 10 populated cards' actual summary text (the rest showed a placeholder
instead of their live content, which I attribute to the PDF export not reliably capturing content
injected asynchronously after each summarization call resolves). The second export captured all
11 senders' cards in full, including the two previously missing, and is the primary basis for the
results below; the first export is used only where it adds a useful data point about run-to-run
consistency.

## Results

**Per-summary content quality was comparable, with no hallucination in either automation.** Across
every newsletter I could compare directly (Elevate, Engineering Leadership, AINews, Latent.Space,
ByteByteGo, Tech Scoop, Geoffrey Huntley, What's AI), both automations correctly captured the
source article's core claims. They differed mainly in emphasis: the artifact's summaries
consistently surfaced concrete named citations (Bob Bemer's 1968 paper and the FANUC/Xiaomi
manufacturing analogy for the Elevate newsletter, for example), matching its prompt's explicit
instruction to cite specific names and numbers, while the skill's summaries more often captured
the article's underlying argument or recommendation (e.g., the "verification capacity is the real
bottleneck" framing and its architecture recommendations, which the artifact's version omitted
entirely). Neither is more "correct"; they are different, reasonable editorial choices.

**One earlier hypothesis did not hold up: the baseline does not fabricate content for
administrative emails.** For both Exaltitude ("You're on the list!" and "Please confirm your
subscription") and The Pragmatic Engineer's welcome email, the artifact explicitly declined to
summarize, stating outright that the emails were transactional/introductory with no editorial
content — the same judgment the skill's explicit administrative-vs-substantive rule was designed
to guarantee. The real difference is not correctness but tone consistency: the skill's uniform
"Administrative — subscription confirmation email, no editorial content" line keeps the same
register as every other entry in the digest, while the artifact's refusal breaks voice, addressing
the reader directly in the first person ("I would need the actual newsletter issue(s)..."), which
reads as an out-of-place apology rather than a digest entry.

**The strongest, most concrete finding is a completeness and reliability gap between two live runs
of the baseline, not between the baseline and the skill.** Comparing the two artifact exports
taken 19 minutes apart: AINews issues found dropped from 5 in the first export to 3 in the second
(missing "AI Cybersecurity becomes top of mind" and "not much happened today"), and Latent.Space
issues dropped from 2 to 1 (missing "Causal Models Need Causal Data"). Nothing about the underlying
inbox or the seven-day window changed meaningfully in that 19-minute gap, so this is not a case of
new mail arriving or old mail aging out — it is the same live-fetch approach returning a smaller,
inconsistent result set on its second run. The artifact's own code offers a likely explanation: it
wraps each per-thread fetch in a try/catch that silently skips failures with no error surfaced to
the user. The skill's single run that same day captured the full set — all 5 AINews issues and
both Latent.Space issues — matching the union of what the two artifact runs found between them,
and its console output (`Found N matching message(s)`) makes the exact count auditable rather than
silently variable.

**The artifact also blends multiple issues from the same sender into one combined narrative,
losing per-email attribution.** Gregor Ojstersek's newsletter published two distinct articles this
week ("Clear Writing Is Becoming a Superpower in the AI Era" and "How Companies Build AI-Native
Engineering Teams"); the artifact merged both into a single overview and bullet list under one
header, and while the merge was factually accurate for both source articles, it's no longer
possible to tell which bullet came from which email without opening the originals. The skill wrote
these as two separate entries, each traceable to exactly one fetched file.

**Two smaller findings from the first evaluation still hold.** The artifact explicitly enumerates
all 11 configured senders, including "No new issue in the last 7 days" for High Growth Engineer;
the skill's digest only lists what it found and is silent about senders with zero matches, which
is a real transparency gap — there's currently no way to distinguish "no new issue" from "a query
bug silently dropped this sender" by reading `digest.md` alone. And a date discrepancy first
noticed between the skill's digest and the artifact (some AINews entries a day apart) is
consistent with a timezone mismatch: the script converts Gmail's `internalDate` using the host
machine's local timezone in Python, while the artifact's JavaScript formats the same timestamp in
the browser's local timezone.

## Analysis

The most important correction from this second evaluation pass is that separating deterministic
retrieval from AI summarization did not need to fix a hallucination problem in the baseline —
there wasn't one. Both automations are backed by a highly capable model, and the assignment's own
framing anticipates that the custom automation may not win outright on raw output quality; here it
mostly didn't. What the separation did produce, and what the evidence now clearly supports, is
reliability: the skill's script returns the same, complete, auditable result set every time it
runs, while the baseline's live per-request fetch produced two different result sets 19 minutes
apart with no visible error to explain the gap. That difference traces directly to a design
choice — the skill's non-AI script performs retrieval as a single deterministic pass with an
explicit, printed count, whereas the baseline's per-thread fetches are wrapped in silent
failure-swallowing inside the artifact's own code. Similarly, the one-file-per-email structure in
`fetch_newsletters.py` and the skill's workflow is the direct reason its digest preserves
per-email attribution where the baseline's sender-level blending does not.

Two gaps the comparison surfaced were fixed before submission: the skill now explicitly enumerates
every configured sender, including those with no matches that week, the way the artifact does; and
`fetch_newsletters.py` now converts Gmail timestamps using an explicit, fixed timezone
(`--timezone`, default `America/New_York`) rather than the host machine's local setting, so digest
dates are reproducible regardless of where the script runs. Both were small, well-scoped fixes
precisely because the workflow is written down in code and in `SKILL.md` rather than left implicit
in a prompt.

That claim was tested immediately: switching to per-sender queries to get the enumeration fix
introduced a new issue, caught on the very next run. Two configured senders (`swyx@substack.com`
and `swyx+ainews@substack.com`) turned out to be aliases of the same inbox, and Gmail's unquoted
`from:` search matched the base address against the plus-tagged one, so the same five AINews
messages matched both senders' queries. The skill's summarization step noticed the duplication in
`manifest.json` and correctly deduplicated it when writing `digest.md`, adding an explanatory note
— but that meant correctness depended on the model catching a problem in the deterministic layer,
which is exactly the dependency this design was built to avoid. The fix attempted at the source
was to quote the address in `build_sender_query` to try to force an exact match; a follow-up run
showed this alone was not sufficient — Gmail still matched the base address against the
plus-tagged one even quoted, most likely because Gmail treats plus-tagged addresses as routing to
(and therefore searchable as) the same underlying mailbox regardless of query syntax. The
guarantee that actually held was the second, independent layer added at the same time:
`fetch_newsletters.py` deduplicates by message ID and records any overlap in a new
`sender_overlaps` field in `manifest.json`, so an alias is a fact the script reports, not one the
model has to infer — and on the next run, it did exactly that, correctly and without any
duplicate output.

A second, more consequential issue turned up on that same follow-up run: the date shown for two
AINews entries shifted by a full day compared to the previous run of the same skill, on the same
underlying emails ("AI Cybersecurity becomes top of mind" moved from Wed 22 Jul to 2026-07-21;
"not much happened today" moved from Tue 21 Jul to 2026-07-20). This is a reproducibility
regression in the skill itself, not just relative to the baseline, and it directly touches the
timezone fix's claim of reproducible dates. The root cause was not the script — `date_local` in
`manifest.json` is computed once, deterministically, in the pinned timezone — but `SKILL.md`,
which never specified which date field to display or that it should be copied rather than
recomputed, leaving the model free to reformat or re-derive a date from raw headers each run. The
first fix made `SKILL.md` explicit — always use `date_local` verbatim, never the raw header, never
a recomputed value — and the very next run showed even that instruction wasn't fully sufficient:
two entries that had shown a consistent one-day gap between them across two prior runs (using two
different date sources) collapsed onto the same day once the model was asked to read and reformat
`date_local` itself. Natural-language instructions to be precise are not the same guarantee as
code that leaves nothing to interpret, so the fix was tightened at the source instead of the
prompt: `fetch_newsletters.py` now precomputes a ready-to-use `date_display` string (e.g. `"Tue,
21 Jul 2026"`) once, in the pinned timezone, and `SKILL.md` requires copying it character for
character rather than deriving anything from `date_local`.

Taken together, these three fixes are supporting evidence for the design's central claim, and a
useful refinement of it: because retrieval logic lives in an inspectable, testable script rather
than an implicit prompt, real correctness gaps were found and root-caused quickly across several
evaluation cycles — but the process also showed that pushing a rule into `SKILL.md`'s prose, even
an explicit one, is not equivalent to pushing it into the deterministic script. The gap only fully
closed once the string the model needed to output already existed verbatim in `manifest.json`,
leaving no computation, however small, for the model to get inconsistently right.
