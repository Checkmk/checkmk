---
status: accepted
date: 2026-11-27
supersedes: '0002'
superseded_by:
---

# cmk-dev-site Moves Into Checkmk as One Commit

## Motivation

cmk-dev-site (install Checkmk versions, create dev sites, mock OIDC provider)
lives in its own repo and is published to PyPI from there. It is to grow into
the repo package `packages/cmk-dev` and be refactored for testability; the
refactoring needs the code here first, guarded by an end-to-end test.
Publishing from checkmk is not decided yet, so the move must not depend on it.

ADR-0002 brought the code in as a merge with the full cmk-dev-site history.
That puts 135 commits on master that hold no Checkmk and never ran through
its CI, and the merge strains the tools around it. The old repo keeps that
history anyway.

## Decision

The code moves unchanged into its final repo package `packages/cmk-dev`, as
module `cmk_dev_site`, in one commit. Behaviour does not change and nothing is
published from checkmk.

- History: the move is one ordinary commit. Its message names the source,
  `https://github.com/Checkmk/cmk-dev-site` at commit `1688edf` (release
  1.25.0). The history and its authors stay in that repo.
- The commit also holds the adaptations, all without effect at runtime: GPLv2
  headers, Bazel `BUILD` and requirements files, and the removal of the
  standalone repo's own tooling (its Bazel module, lock files, CI, release
  snippets and changelog, `pyproject.toml`, `LICENSE`). mypy and lint findings
  whose fix would change behaviour or output are suppressed there; they are
  fixed in the refactoring that follows the move.
- Two changes follow the move: the launchers below, and fixes for the lint
  findings whose fix keeps behaviour and output the same. "Unchanged" means
  unchanged behaviour, not unchanged source.
- Tests run as checkmk Bazel unit tests; type checking moves from pyright to
  mypy, lint to `bazel lint`.
- Developers with a checkout start the tool through one launcher,
  `scripts/cmk-dev-site.py`, on the repo `.venv`, without `bazel run` and
  without a wheel. Symlinks to it carry the other wheel command names
  (`cmk-dev-install.py`, `cmk-dev-install-site.py`,
  `cmk-dev-site-mock-auth.py`); the name it is started under picks the
  command.

## Consequences

- Users: nothing changes. The standalone repo keeps publishing the PyPI
  package, frozen to bug fixes from the day the move is submitted, so the
  VS Code extension and pipx users keep working.
- Limitation: two copies of the code until publishing moves to checkmk; each
  later bug fix is cherry-picked into checkmk as its own change.
- The code is relicensed from GPL-3.0-only to GPLv2. Checkmk GmbH holds the
  copyright, since all authors are employees, so the copy here is licensed
  under GPLv2. The versions published on PyPI stay GPLv3.
- Limitation: `git log` and `git blame` in checkmk stop at the move commit.
  Older history and its authors are in the standalone repo, up to `1688edf`.
- No module layer rules apply while the module is `cmk_dev_site`; they start
  with the rename to `cmk.dev.<part>`.
- Follow-up: an end-to-end test guards everything after the move.

## Rejected Ideas

### Merge with the full history (ADR-0002)

`git log` and `git blame` would show the whole history here. But master
would hold 135 commits without Checkmk that never ran through its CI, so a
plain `git bisect` can step into them. The medium chain cannot follow the
merge, and every rebase of the merge drops its review vote. The old repo
keeps that history anyway.

### Land the history in CI-ready pieces

Every commit on master would be a tested Checkmk state. But each of the 135
commits would need Bazel targets, license headers and lint fixes, so they
would no longer be the original commits, and each piece would be its own
review change.
