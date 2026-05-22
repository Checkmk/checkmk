---
name: crash-owner-rollup
description: Generate the periodic "unsolved Checkmk check crashes on 2.4+" Slack rollup, grouped by component owner. Composes the crash-report and component-owners skills and emits Slack-ready plain text (no markdown).
---

# crash-owner-rollup

Generate the periodic Slack post that lists open crash groups on Checkmk 2.4+
grouped by the engineer who owns the affected component. The goal is to route
crashes to the actual owner instead of the generic Plugins bucket.

## When to invoke

The user says one of:

- `/crash-owner-rollup`
- "crash owner rollup"
- "unsolved crash rollup"
- "owner rollup for Slack"
- any rewording that combines _crash_ + _owner_ + _Slack/rollup_

## Inputs

No arguments required. Optional:

- Minimum Checkmk version cutoff (default `2.4`)
- Plugins-bucket coordinator (default `moritz.kiemer@checkmk.com`)

## How to run

The skill is implemented as a Python module in the Checkmk repo at
`.github/skills/crash_owner_rollup/`. From the repo root:

```bash
PYTHONPATH=.github/skills .venv/bin/python -m crash_owner_rollup \
  --output /tmp/slack_post.txt
```

The first run authenticates with crash.checkmk.com (Google OAuth); subsequent
runs reuse the cached token. If you see `AuthenticationError`, ask the user to
run `PYTHONPATH=.github/skills .venv/bin/python -m crash_report.authenticate`.

Common flags:

- `--min-version 2.4` (default) — version cutoff.
- `--plugins-coordinator <email>` — who gets the residue bucket.
- `--no-diff` — skip the "Changes since last run" section.
- `--no-cache` — bypass the enrichment cache (forces a full re-fetch).
- `--refresh-components` — bypass the daily `cmk-components info` cache.
- `--output PATH` — write Slack text to a file in addition to stdout.

### Performance

The module caches:

- Per-group enrichment (`~/.cache/cmk-crash-rollup/enrichment.json`) keyed by
  `(group_id, num_crashes)`. The /search listing already returns num_crashes;
  if it hasn't changed, the per-group + per-report HTTP calls are skipped.
- Parsed `cmk-components info` for 24 hours (`components.json`).
- One JSON snapshot per run (`snapshots/<timestamp>.json`) for the diff
  section.

Cold-cache run: ~14 s for the typical ~300 group listing. Warm-cache run: ~3 s.
Pass `--no-cache` if you suspect cached enrichment is stale (group exception
text or plugin_path doesn't change once a group exists, so this is rarely
needed).

### Diff section

By default, the rollup includes a "Changes since <prior timestamp>" block:

- Resolved / aged out groups (in prior, not in current).
- New groups (in current, not in prior).
- Crash count deltas on common groups.

If there's no prior snapshot yet (first run), the section is omitted.

## Output format — Slack plain text (no markdown!)

Slack does **not** render pasted markdown — see `feedback_slack_no_markdown`.
The emitted text uses:

- No `**bold**`, no `[label](url)`, no `#` headings, no markdown bullets.
- **No bullets at all** — not `-`, not `*`, not `•`. Blank lines and `—`
  (em dash) provide structure.
- Raw URLs (Slack auto-links them). Crash count in parens: `https://… (3)`.
- @-mentions as plain `@FirstLast` (the user pastes; Slack resolves on send).

Each group link points to
`https://crash.checkmk.com/gui/crashreportgroupview/show/<id>`.

Per-owner block:

```
@Owner Name — Component A, Component B — N groups, M crashes
family_a:
https://crash.checkmk.com/gui/crashreportgroupview/show/XXXX (count)
…
family_b:
https://crash.checkmk.com/gui/crashreportgroupview/show/YYYY (count)
```

Sort: owners by total crash count desc, then group count desc, then email
(stable tie-break). Families within an owner sort by crash count desc, group
count desc, family name. Groups within a family sort by crash count desc,
group_id asc. Two consecutive runs over the same data produce byte-identical
output.

Plugins-bucket residue goes in a final section addressed to the Plugins
coordinator, with one sub-block per family.

## Pre-send sanity checks

The module already enforces these via its sort + naming logic, but a final
visual scan before handing off:

- Stray punctuation in @-mentions (trailing `.` after a name).
- Missing characters (`heckpoint` → `checkpoint`).
- Missing space between `@Name` and the next word (`@Moritzplease`).
- Any leading bullet character (`•`, `-`, `*`).
- Stray `<` / `>` left over from copied markdown links.
- Counts add up to the headline totals.

## Hand-off

Print the full Slack-ready text in a quadruple-fenced block (since the body
contains a triple-fence for the investigate command) so the user can copy
cleanly.
