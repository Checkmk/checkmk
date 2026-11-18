---
status: accepted
date: 2026-11-10
supersedes:
superseded_by:
---

# Decisions Are Recorded as ADRs

## Motivation

cmk-dev-site moves into this repo and grows into `cmk-dev`, a set of developer
tools in one repo package. Its design decisions need the agreement of a
reviewer before code follows.

## Decision

Design decisions of `packages/cmk-dev` are recorded as ADRs (Architecture
Decision Records): one short, numbered Markdown file per decision in
`packages/cmk-dev/docs/adr/NNNN-short-title.md`. An accepted ADR is never
edited; a later decision supersedes it with a new ADR.

### Review and acceptance

- Each ADR gets its own Gerrit change, holding only the ADR. A superseding
  ADR's change also sets `superseded_by` and `status: superseded` on the old
  ADR.
- An ADR is written with `status: accepted`. The open change is the proposal,
  and submitting it is the acceptance, so master only holds decided ADRs.
- If the reviewers reject an ADR, the same change is amended to
  `status: rejected` and gets a Rejection section that says why. Then it is
  submitted, so the reason stays on record.
- Implementation commits name the ADR they follow (e.g. `ADR-0002`). Design
  review happens on the ADR; implementation changes get the usual code review.

### Metadata

Each ADR starts with a metadata block (YAML front matter, between two `---`
lines) with these fields:

- `status`: `accepted` when written, `rejected` if the review turns it down,
  `superseded` once a later ADR replaces it.
- `date`: the day the ADR was written, as `YYYY-MM-DD`.
- `supersedes`: the number of the ADR this one replaces, or empty. Numbers are
  quoted (`'0001'`), so YAML tools do not read them as octal numbers.
- `superseded_by`: the quoted number of the ADR that replaced this one, or
  empty. Setting it, together with `status: superseded`, is the only edit an
  accepted ADR gets.

The ADR's own number and title are only in its file name, and its status
only in `status`. There is no index file that repeats them.

### Sections

The body has these sections:

- Motivation: why the decision is needed: the problem it solves and the
  constraints it has to meet. It makes the case for deciding at all.
- Decision: what is decided, in enough detail to build it, and why this way.
- Consequences: what changes for users and developers, what the decision does
  not solve, and the work it causes.
- Rejected Ideas: the other ideas, each with the reason it lost, as in a
  Python PEP.
- Rejection: only in a rejected ADR, at the end: why the reviewers turned it
  down.

## Consequences

- Developers find the reasons behind the package's design next to its code.
- Limitation: the series covers only `packages/cmk-dev`.
- Limitation: an open ADR change already says `accepted`; only Gerrit shows
  that it is still under discussion.
- ADR changes and implementation changes both need a vote from a code owner
  of `developer_tools_site_creation`.
- Limitation: decisions made before this ADR are not written down afterwards.
- A README with the steps for writing an ADR, a template with the sections
  above and the ADR rules for agents in `AGENTS.md` come with the change that
  implements this ADR, not with the ADR itself.
- Limitation: there is no overview of which ADRs hold. `ls docs/adr` lists
  them, and `grep status: docs/adr/*.md` shows their status.

## Rejected Ideas

### An index that lists the ADRs by status

A README listing the ADRs under Accepted, Rejected and Superseded gives an
overview at a glance, but it repeats each ADR's status. Every rejection or
supersede would then edit two places that can drift apart, and every ADR
change would touch the index too.

### Push as `proposed`, amend to `accepted` before submit

Master would also hold only decided ADRs, but every decision would cost one
more patch set and a new +2, because Gerrit drops the vote when the content
changes.

### Submit as `proposed`, accept in a follow-up commit

Proposals would show on master early, but master would then also hold
undecided ADRs, and every ADR would need two commits.
