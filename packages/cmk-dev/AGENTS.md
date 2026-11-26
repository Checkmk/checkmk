# cmk-dev

Developer tools for working on Checkmk. Design decisions for this package are
recorded as ADRs (Architecture Decision Records) in `docs/adr/`; see
[docs/adr/README.md](docs/adr/README.md).

## ADRs

- Before a design change, write an ADR: copy `docs/adr/template.md` to the
  next free number.
- Push each ADR as a Gerrit change of its own, holding only the ADR. Write it
  with `status: accepted`: submitting the change accepts it. If the reviewers
  reject it, amend the change to `status: rejected`, add a `## Rejection`
  section with their reason and submit it.
- Never edit an accepted ADR. Supersede it with a new one that sets
  `supersedes`. In the same change, the old ADR gets `superseded_by` and
  `status: superseded`, its only edits.
- Implementation commits name the ADR they follow, e.g. `ADR-0002`.
