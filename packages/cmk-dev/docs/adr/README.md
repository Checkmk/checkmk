# Architecture Decision Records

An ADR (Architecture Decision Record) is one short, numbered file per design
decision of `packages/cmk-dev`. How the process works is itself an ADR,
[ADR-0001](0001-decisions-are-recorded-as-adrs.md); its Metadata section
describes the fields at the top of each file.

## Writing an ADR

1. Copy [template.md](template.md) to `NNNN-short-title.md`, using the next
   free number.
2. Fill in Motivation, Decision, Consequences and Rejected Ideas, and set
   `date`. Keep `status: accepted`: the open change is the proposal, and
   submitting it accepts the ADR.
3. Push it as a Gerrit change of its own, holding only the ADR.
4. If the reviewers reject it, amend the same change: set `status: rejected`,
   add a `## Rejection` section at the end that says why and submit it, so the
   reason stays on record.

An accepted ADR is never edited. A later decision gets a new ADR with
`supersedes: 'NNNN'`; in the same change, the old one gets `superseded_by` and
`status: superseded`.
