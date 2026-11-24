# cmk-dev

Developer tools for working on Checkmk. Design decisions for this package are
recorded as ADRs (Architecture Decision Records) in `docs/adr/`; see
[docs/adr/README.md](docs/adr/README.md).

## Layout

- `cmk_dev_site/`: the cmk-dev-site tool, moved here unchanged from its own
  repo, which keeps its history (ADR-0003). Entry points:
  `cmk_dev_site.cmk_dev_site:main`, `cmk_dev_site.cmk_dev_install:main`,
  `cmk_dev_site.cmk_dev_install_site:main`,
  `cmk_dev_site.saas.oidc_service:run`.
- `tests/`: its unit tests, run by Bazel.
- `docs/adr/`: the ADRs.

The standalone cmk-dev-site repo still publishes the PyPI package and only
takes bug fixes; a fix there is cherry-picked here as its own change.

## Build and test

```
bazel test //packages/cmk-dev/...
bazel lint //packages/cmk-dev/...
bazel build --config=mypy //packages/cmk-dev/...
```

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
