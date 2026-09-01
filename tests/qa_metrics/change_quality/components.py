#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve the source-code component a change belongs to.

Ownership itself comes from :mod:`tests.qa_metrics.components`. Two things this
module adds on top, both specific to walking history:

1. **Historical paths.** A path renamed since the commit that touched it is
   translated to its HEAD name first, or commits older than the last
   reorganisation classify as ``None`` for a source file that merely moved.

2. **One component per change.** A change touches several paths;
   :func:`pick_component` reduces them to the one the row records.
"""

import logging
import os
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Final

from tests.qa_metrics.components import ComponentOwnership, load_ownership

from .detect_test import is_test_path

logger = logging.getLogger(__name__)

# CI is headless -- no keyring, and no terminal for cwz to prompt on -- so it
# passes the Gerrit credentials in these variables. Locally they are unset and
# cwz falls back to ~/.netrc or the keyring.
_GERRIT_USER_VAR: Final = "QA_GERRIT_USER"
_GERRIT_TOKEN_VAR: Final = "QA_GERRIT_PASSWORD"


def lookup_components(paths: Iterable[str], repo: Path) -> dict[str, str | None]:
    """Return ``{path: owning component(s)}``, co-owners ``", "``-joined.

    The value is ``None`` both when nothing owns the path and when the path has no
    equivalent at HEAD -- both mean "cannot be attributed".
    """
    all_paths = sorted(set(paths))
    if not all_paths:
        return {}

    renames = _collapse_renames(_rename_log(repo)) if _any_path_missing(all_paths, repo) else {}
    head_name_per_path = _head_paths(all_paths, repo, renames)

    to_query = _paths_to_query(head_name_per_path)
    if not to_query:
        logger.info("None of the %d path(s) exist at HEAD; nothing to resolve", len(all_paths))
        return dict.fromkeys(all_paths)

    logger.info(
        "Resolving components for %d unique HEAD path(s) (from %d input path(s))",
        len(to_query),
        len(all_paths),
    )
    return _owning_components(
        head_name_per_path,
        load_ownership(to_query, credentials=_credentials(os.environ)),
    )


def pick_component(
    files_changed: Iterable[str], component_map: Mapping[str, str | None]
) -> str | None:
    """Return the majority component across the non-test paths in ``files_changed``.

    Test-only paths are excluded so test-heavy changes don't classify as
    "tests/...". Ties are broken alphabetically, and ``None`` means no path
    resolved to a component.
    """
    counts = Counter(
        component
        for path in files_changed
        if not is_test_path(path) and (component := component_map.get(path)) is not None
    )
    if not counts:
        return None
    return min(counts, key=lambda component: (-counts[component], component))


def _any_path_missing(paths: Iterable[str], repo: Path) -> bool:
    """Whether resolving ``paths`` needs HEAD's rename history at all.

    Walking every rename in HEAD's history takes seconds, and answers nothing on
    an incremental run where every input is already at HEAD.
    """
    return any(not (repo / path).is_file() for path in paths)


def _head_paths(
    paths: Sequence[str], repo: Path, renames: Mapping[str, str]
) -> dict[str, Path | None]:
    """Map each path to its equivalent at HEAD, or ``None`` if it has none.

    * a path that exists in ``repo`` maps to itself
    * a path that ``renames`` moves to something that exists maps to the target,
      so e.g. ``cmk/legacy_checks/*.py`` resolves through its move to
      ``cmk/plugins/*``
    * anything else maps to ``None``: deleted without a rename, renamed to a
      target since deleted, or never on HEAD

    The keys stay the strings the caller passed -- they key the rows this ends up
    in -- while a HEAD name becomes a ``Path``, which is what ownership is keyed
    and asked for by. ``renames`` is raw log text on both sides, since its keys
    are looked up by those same input strings.
    """

    def head_name(path: str) -> Path | None:
        if (repo / path).is_file():
            return Path(path)
        candidate = renames.get(path)
        return Path(candidate) if candidate is not None and (repo / candidate).is_file() else None

    return {path: head_name(path) for path in paths}


def _paths_to_query(head_name_per_path: Mapping[str, Path | None]) -> list[Path]:
    """The HEAD names worth asking about, sorted.

    Fewer than the inputs in both directions: a path with no HEAD name is not
    worth a query, and several inputs can share one HEAD name.
    """
    return sorted({head for head in head_name_per_path.values() if head is not None})


def _owning_components(
    head_name_per_path: Mapping[str, Path | None], ownership: ComponentOwnership
) -> dict[str, str | None]:
    """Answer each path with the components owning its HEAD name."""
    return {
        path: None if head is None else ", ".join(ownership.owners_of(head)) or None
        for path, head in head_name_per_path.items()
    }


def _collapse_renames(name_status_lines: Iterable[str]) -> dict[str, str]:
    """``{historical path: final path}`` from ``git log --name-status`` output.

    Expects the ``--diff-filter=R --format=`` output of an oldest-first log, whose
    rename lines read ``R<similarity>\\t<old>\\t<new>``. Anything else is ignored.

    Chains are collapsed, so ``A -> B -> C`` yields both ``A -> C`` and ``B -> C``
    and any historical name resolves in one lookup. A chain stops as soon as it
    revisits a name, so a cycle terminates.
    """
    direct: dict[str, str] = {}
    for line in name_status_lines:
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].startswith("R"):
            continue
        _similarity, old, new = parts
        direct[old] = new

    collapsed: dict[str, str] = {}
    for start in direct:
        if start in collapsed:
            continue
        chain: list[str] = []
        current = start
        while current in direct and current not in chain:
            chain.append(current)
            current = direct[current]
        for path in chain:
            collapsed[path] = current
    return collapsed


def _credentials(env: Mapping[str, str]) -> tuple[str, str] | None:
    """The CI Gerrit credentials in ``env``, or ``None`` to let cwz resolve them.

    Takes the environment rather than reading it, so a test settles which half
    of the pair is the username.
    """
    user, token = env.get(_GERRIT_USER_VAR), env.get(_GERRIT_TOKEN_VAR)
    return (user, token) if user and token else None


def _rename_log(repo: Path) -> list[str]:
    """Every rename reachable from HEAD, oldest first, as raw output lines."""
    proc = subprocess.run(
        ["git", "log", "--reverse", "--diff-filter=R", "--name-status", "--format=", "HEAD"],
        cwd=repo,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    return proc.stdout.splitlines()
