---
status: superseded
date: 2026-11-10
supersedes:
superseded_by: '0003'
---

# cmk-dev-site Moves Into Checkmk Unchanged and Unpublished

## Motivation

cmk-dev-site (install Checkmk versions, create dev sites, mock OIDC provider)
lives in its own repo and is published to PyPI from there. It is built,
tested and reviewed differently from checkmk. It is to grow into the repo
package `packages/cmk-dev` and be refactored for testability; the refactoring
needs the code here first, guarded by an end-to-end test. Publishing from
checkmk is not decided yet, so the move must not depend on it.

Developers reading the moved code should still see who wrote what and why:
`git log` and `git blame` should show the cmk-dev-site history with its
original authors.

## Decision

The code moves unchanged into its final repo package `packages/cmk-dev`, as
module `cmk_dev_site`, so it never moves between repo packages. Behaviour
does not change and nothing is published from checkmk.

- History: the cmk-dev-site commits, moved below `packages/cmk-dev/` and with
  the uploader as committer, are pushed once to a sandbox branch; the move is
  then one merge change on master with that branch as second parent. `git log`
  and `git blame` show the full history with its original authors and dates,
  and Gerrit opens one review change for it. Version tags are not imported.
- The merge change also holds the adaptations, all without effect at runtime:
  GPLv2 headers, Bazel `BUILD` and requirements files, and the removal of the
  standalone repo's own tooling (its Bazel module, lock files, CI, release
  snippets and changelog, `pyproject.toml`, `LICENSE`). mypy and lint findings
  whose fix would change behaviour or output are suppressed there; they are
  fixed in the refactoring that follows the move.
- Two changes follow the merge: the launchers below, and fixes for the lint
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
  package, frozen to bug fixes from the day the merge is submitted, so the
  VS Code extension and pipx users keep working.
- Limitation: two copies of the code until publishing moves to checkmk; each
  later bug fix is cherry-picked into checkmk as its own change.
- The code is relicensed from GPL-3.0-only to GPLv2. Checkmk GmbH holds the
  copyright, since all authors are employees, so the copy here is licensed
  under GPLv2. The versions published on PyPI stay GPLv3.
- Limitation: `git log --format=fuller` shows the uploader as committer of the
  imported commits; authors and dates are kept.
- No module layer rules apply while the module is `cmk_dev_site`; they start
  with the rename to `cmk.dev.<part>`.
- Follow-up: an end-to-end test guards everything after the move.

## Rejected Ideas

### Plain copy

One simple change, but `git log` and `git blame` would stop at one "copy"
commit; the history and its authors would only be in the old repo.

### Push the imported history for review directly

Importing with `git filter-repo` and pushing the merge for review gives the
full history too, but Gerrit would open one review change per imported commit
(135).
