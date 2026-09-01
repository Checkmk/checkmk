#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.qa_metrics.change_quality import components
from tests.qa_metrics.change_quality.components import (
    _any_path_missing,
    _collapse_renames,
    _credentials,
    _GERRIT_TOKEN_VAR,
    _GERRIT_USER_VAR,
    _head_paths,
    _owning_components,
    _paths_to_query,
    _rename_log,
    lookup_components,
    pick_component,
)
from tests.qa_metrics.components import ComponentOwnership, load_ownership


def _touch(root: Path, *relative: str) -> None:
    for path in relative:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("x = 1\n")


def _git(repo: Path, *args: str) -> None:
    """Run git in ``repo`` with an identity, since the environment carries none."""
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _repo_with_rename(root: Path) -> None:
    """A repository whose history renames ``cmk/old.py`` to ``cmk/new.py``.

    Only the rename matters, so the file keeps its content across it -- that is
    what makes `git log --diff-filter=R` report it as R100 rather than a
    delete/add pair.
    """
    _git(root, "init", "--quiet")
    (root / "cmk").mkdir()
    (root / "cmk/old.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "add")
    _git(root, "mv", "cmk/old.py", "cmk/new.py")
    _git(root, "commit", "--quiet", "-a", "-m", "rename")


# --- _collapse_renames: the parsing, exercised on the raw output --------------


def test_collapse_renames_of_no_output_is_empty() -> None:
    assert _collapse_renames([]) == {}


def test_collapse_renames_reads_one_rename() -> None:
    assert _collapse_renames(["R100\tcmk/old.py\tcmk/new.py"]) == {"cmk/old.py": "cmk/new.py"}


def test_collapse_renames_keeps_independent_renames_apart() -> None:
    assert _collapse_renames(["R100\ta.py\tb.py", "R090\tc.py\td.py"]) == {
        "a.py": "b.py",
        "c.py": "d.py",
    }


def test_collapse_renames_follows_a_chain_to_its_end() -> None:
    """A -> B -> C: every historical name must resolve to C in one lookup."""
    assert _collapse_renames(["R100\ta.py\tb.py", "R100\tb.py\tc.py"]) == {
        "a.py": "c.py",
        "b.py": "c.py",
    }


def test_collapse_renames_follows_a_long_chain() -> None:
    log = ["R100\ta.py\tb.py", "R100\tb.py\tc.py", "R100\tc.py\td.py"]
    assert _collapse_renames(log) == {"a.py": "d.py", "b.py": "d.py", "c.py": "d.py"}


def test_collapse_renames_terminates_on_a_cycle() -> None:
    """A file renamed away and back must not loop the chain walk forever.

    Which name wins is not arbitrary. The log is oldest-first, so the walk enters
    the cycle at the name renamed away first and comes back round to it -- and
    that is the name the file carries at HEAD. Entering anywhere else would hand
    :func:`_head_paths` a name it finds nowhere on disk, so the path would
    resolve to nothing and its row would lose its component.
    """
    assert _collapse_renames(["R100\ta.py\tb.py", "R100\tb.py\ta.py"]) == {
        "a.py": "a.py",
        "b.py": "a.py",
    }


def test_collapse_renames_ignores_blank_lines() -> None:
    assert _collapse_renames(["", "R100\ta.py\tb.py", "  ", ""]) == {"a.py": "b.py"}


def test_collapse_renames_ignores_other_statuses() -> None:
    """Only renames carry an old and a new name; M/A/D lines have one path."""
    assert _collapse_renames(["M\ta.py", "A\tb.py", "D\tc.py"]) == {}


def test_collapse_renames_ignores_a_line_with_too_few_fields() -> None:
    assert _collapse_renames(["R100\tonly_one_path.py"]) == {}


def test_collapse_renames_ignores_a_line_with_too_many_fields() -> None:
    assert _collapse_renames(["R100\ta.py\tb.py\tc.py"]) == {}


def test_collapse_renames_ignores_a_status_that_merely_starts_differently() -> None:
    assert _collapse_renames(["C100\tcopied_from.py\tcopied_to.py"]) == {}


def test_collapse_renames_reads_a_real_rename_log(tmp_path: Path) -> None:
    """The one test that runs the git command the parsing above assumes.

    Everything else feeds `_collapse_renames` hand-written lines, so a change to
    the log's flags or format would go unnoticed without a real repository.
    """
    _repo_with_rename(tmp_path)
    assert _collapse_renames(_rename_log(tmp_path)) == {"cmk/old.py": "cmk/new.py"}


# --- _any_path_missing: whether the rename log is worth fetching ---------------


def test_any_path_missing_is_false_when_every_path_exists(tmp_path: Path) -> None:
    """Walking every rename in HEAD's history is multi-second work; skip it."""
    _touch(tmp_path, "cmk/gui/main.py", "cmk/here.py")
    assert not _any_path_missing(["cmk/gui/main.py", "cmk/here.py"], tmp_path)


def test_any_path_missing_is_true_for_a_path_not_on_disk(tmp_path: Path) -> None:
    _touch(tmp_path, "cmk/here.py")
    assert _any_path_missing(["cmk/here.py", "cmk/gone.py"], tmp_path)


# --- _head_paths: applying a rename map -------------------------------------


def test_head_paths_maps_an_existing_path_to_itself(tmp_path: Path) -> None:
    _touch(tmp_path, "cmk/gui/main.py")
    assert _head_paths(["cmk/gui/main.py"], tmp_path, {}) == {
        "cmk/gui/main.py": Path("cmk/gui/main.py")
    }


def test_head_paths_treats_a_directory_as_missing(tmp_path: Path) -> None:
    """Only a file can be resolved to a component."""
    (tmp_path / "cmk").mkdir()
    assert _head_paths(["cmk"], tmp_path, {}) == {"cmk": None}


def test_head_paths_follows_a_rename_to_an_existing_file(tmp_path: Path) -> None:
    """Regression: paths missing from disk used to be dropped outright, so commits
    older than the last reorganisation classified as no component at all even
    when the source file had simply moved."""
    _touch(tmp_path, "cmk/new/subdir/thing.py")
    rename_map = {"cmk/old/thing.py": "cmk/new/subdir/thing.py"}
    assert _head_paths(["cmk/old/thing.py"], tmp_path, rename_map) == {
        "cmk/old/thing.py": Path("cmk/new/subdir/thing.py")
    }


def test_head_paths_yields_none_when_the_rename_target_is_gone(tmp_path: Path) -> None:
    """A rename whose destination has since been deleted resolves to nothing."""
    assert _head_paths(["cmk/a.py"], tmp_path, {"cmk/a.py": "cmk/b.py"}) == {"cmk/a.py": None}


def test_head_paths_yields_none_for_a_missing_path_with_no_rename(tmp_path: Path) -> None:
    assert _head_paths(["cmk/gone.py"], tmp_path, {}) == {"cmk/gone.py": None}


def test_head_paths_prefers_the_file_on_disk_over_a_rename(tmp_path: Path) -> None:
    """A path that still exists is its own HEAD name, even if a later rename
    moved something of the same name elsewhere."""
    _touch(tmp_path, "cmk/a.py", "cmk/b.py")
    assert _head_paths(["cmk/a.py"], tmp_path, {"cmk/a.py": "cmk/b.py"}) == {
        "cmk/a.py": Path("cmk/a.py")
    }


def test_head_paths_covers_every_input_path(tmp_path: Path) -> None:
    _touch(tmp_path, "cmk/here.py")
    assert _head_paths(["cmk/here.py", "cmk/gone.py"], tmp_path, {}) == {
        "cmk/here.py": Path("cmk/here.py"),
        "cmk/gone.py": None,
    }


def test_head_paths_resolves_a_file_that_is_not_utf_8(tmp_path: Path) -> None:
    """No content is read, so a binary path votes instead of abstaining.

    The pre-image filtered these out; the commit that dropped the filter says so,
    and this is what would notice a content gate creeping back in.
    """
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents/blob.py").write_bytes(b"\xff\xfe not utf-8\n")
    assert _head_paths(["agents/blob.py"], tmp_path, {}) == {
        "agents/blob.py": Path("agents/blob.py")
    }


# --- _paths_to_query: what the ownership fetch is asked about -----------------


def test_paths_to_query_asks_about_the_head_name() -> None:
    """A renamed path is resolved under the name it carries at HEAD.

    Ownership comes from HEAD's OWNERS files, which know nothing of the old name.
    """
    assert _paths_to_query({"cmk/old.py": Path("cmk/new.py")}) == [Path("cmk/new.py")]


def test_paths_to_query_asks_about_a_shared_head_name_once() -> None:
    """Two inputs resolving to one file are one query, in a stable order."""
    assert _paths_to_query({"cmk/b.py": Path("cmk/b.py"), "cmk/old_b.py": Path("cmk/b.py")}) == [
        Path("cmk/b.py")
    ]


def test_paths_to_query_is_sorted() -> None:
    assert _paths_to_query({"cmk/b.py": Path("cmk/b.py"), "cmk/a.py": Path("cmk/a.py")}) == [
        Path("cmk/a.py"),
        Path("cmk/b.py"),
    ]


def test_paths_to_query_skips_a_path_without_a_head_name() -> None:
    """An unresolvable path is not worth a lookup."""
    assert _paths_to_query({"cmk/here.py": Path("cmk/here.py"), "cmk/deleted.py": None}) == [
        Path("cmk/here.py")
    ]


def test_paths_to_query_is_empty_when_nothing_has_a_head_name() -> None:
    assert _paths_to_query({"cmk/deleted.py": None}) == []


# --- _owning_components: attributing the fetched ownership -------------------


def _ownership(owners_by_path: Mapping[str, Sequence[str]]) -> ComponentOwnership:
    """Ownership as the fetch returns it, without fetching."""
    return ComponentOwnership(
        owners_by_path={Path(path): owners for path, owners in owners_by_path.items()},
        component_ids=frozenset(
            component for owners in owners_by_path.values() for component in owners
        ),
    )


def test_owning_components_maps_a_path_to_its_owner() -> None:
    assert _owning_components(
        {"cmk/bi/trees.py": Path("cmk/bi/trees.py")},
        _ownership({"cmk/bi/trees.py": ("business_intelligence",)}),
    ) == {"cmk/bi/trees.py": "business_intelligence"}


def test_owning_components_joins_the_owners_of_a_co_owned_path() -> None:
    """The spelling the rows in cmk_change_tested already use."""
    assert _owning_components(
        {"cmk/shared.py": Path("cmk/shared.py")},
        _ownership({"cmk/shared.py": ("business_intelligence", "ui_setup")}),
    ) == {"cmk/shared.py": "business_intelligence, ui_setup"}


def test_owning_components_keys_the_answer_by_the_input_path() -> None:
    """Ownership comes back under the HEAD name; the caller asked about the old one."""
    assert _owning_components(
        {"cmk/old.py": Path("cmk/new.py")},
        _ownership({"cmk/new.py": ("business_intelligence",)}),
    ) == {"cmk/old.py": "business_intelligence"}


def test_owning_components_maps_an_unowned_path_to_none() -> None:
    assert _owning_components(
        {"cmk/orphan.py": Path("cmk/orphan.py"), "cmk/bi/trees.py": Path("cmk/bi/trees.py")},
        _ownership({"cmk/orphan.py": (), "cmk/bi/trees.py": ("business_intelligence",)}),
    ) == {"cmk/orphan.py": None, "cmk/bi/trees.py": "business_intelligence"}


def test_owning_components_maps_a_path_without_a_head_name_to_none() -> None:
    """It was never asked about, so the ownership data has no entry for it."""
    assert _owning_components(
        {"cmk/deleted.py": None, "cmk/bi/trees.py": Path("cmk/bi/trees.py")},
        _ownership({"cmk/bi/trees.py": ("business_intelligence",)}),
    ) == {"cmk/deleted.py": None, "cmk/bi/trees.py": "business_intelligence"}


def test_owning_components_accepts_a_batch_in_which_nothing_is_owned() -> None:
    """A batch touching only unowned paths is a legitimate result.

    It must resolve to None rather than abort the run, or an incremental run
    whose commits happen to miss every OWNERS rule would fail instead of pushing
    the honest answer.
    """
    assert _owning_components(
        {"doc/notes.py": Path("doc/notes.py"), "doc/other.py": Path("doc/other.py")},
        _ownership({"doc/notes.py": (), "doc/other.py": ()}),
    ) == {"doc/notes.py": None, "doc/other.py": None}


# --- lookup_components: the composition ---------------------------------------


def test_lookup_components_of_no_path_is_empty(tmp_path: Path) -> None:
    assert lookup_components([], tmp_path) == {}


def test_lookup_components_maps_every_path_to_none_when_none_resolves_at_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo_with_rename(tmp_path)
    monkeypatch.setattr(
        components,
        load_ownership.__name__,
        lambda *_, **__: pytest.fail("ownership fetched although nothing resolves at HEAD"),
    )
    assert lookup_components(["cmk/gone.py", "cmk/also_gone.py"], tmp_path) == {
        "cmk/gone.py": None,
        "cmk/also_gone.py": None,
    }


def test_lookup_components_asks_ownership_about_head_names_with_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The HEAD name reaches the fetch, the answer comes back under the input name."""
    _repo_with_rename(tmp_path)
    monkeypatch.setenv(_GERRIT_USER_VAR, "user")
    monkeypatch.setenv(_GERRIT_TOKEN_VAR, "token")
    asked: list[tuple[Sequence[Path], object]] = []

    def fake_load_ownership(paths: Sequence[Path], **kwargs: object) -> ComponentOwnership:
        asked.append((paths, kwargs.get("credentials")))
        return _ownership({"cmk/new.py": ("business_intelligence",)})

    monkeypatch.setattr(components, load_ownership.__name__, fake_load_ownership)

    assert lookup_components(["cmk/old.py"], tmp_path) == {"cmk/old.py": "business_intelligence"}
    assert asked == [([Path("cmk/new.py")], ("user", "token"))]


def test_lookup_components_skips_the_rename_log_when_every_path_is_at_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Walking the history is the expensive part of an incremental run."""
    _touch(tmp_path, "cmk/a.py")
    monkeypatch.setattr(
        components,
        _rename_log.__name__,
        lambda _repo: pytest.fail("rename log read although nothing is missing"),
    )
    monkeypatch.setattr(
        components,
        load_ownership.__name__,
        lambda _paths, **_: _ownership({"cmk/a.py": ("checkmk",)}),
    )

    assert lookup_components(["cmk/a.py"], tmp_path) == {"cmk/a.py": "checkmk"}


# --- pick_component ---------------------------------------------------------


def test_pick_component_picks_the_majority() -> None:
    assert (
        pick_component(
            ["cmk/gui/a.py", "cmk/gui/b.py", "cmk/base/c.py"],
            {
                "cmk/gui/a.py": "ui_framework",
                "cmk/gui/b.py": "ui_framework",
                "cmk/base/c.py": "automation_engine",
            },
        )
        == "ui_framework"
    )


def test_pick_component_ignores_test_paths() -> None:
    assert (
        pick_component(
            ["tests/unit/test_x.py", "tests/unit/test_y.py", "cmk/base/c.py"],
            {
                "tests/unit/test_x.py": "ui_framework",
                "tests/unit/test_y.py": "ui_framework",
                "cmk/base/c.py": "automation_engine",
            },
        )
        == "automation_engine"
    )


def test_pick_component_returns_none_when_no_path_resolves() -> None:
    assert (
        pick_component(
            ["cmk/gui/main.py", "cmk/base/config.py"],
            {"cmk/gui/main.py": None, "cmk/base/config.py": None},
        )
        is None
    )


def test_pick_component_returns_none_for_paths_absent_from_the_map() -> None:
    assert pick_component(["cmk/gui/main.py"], {}) is None


def test_pick_component_breaks_ties_alphabetically() -> None:
    assert (
        pick_component(
            ["cmk/gui/main.py", "cmk/base/config.py"],
            {"cmk/gui/main.py": "ui_framework", "cmk/base/config.py": "automation_engine"},
        )
        == "automation_engine"
    )


def test_pick_component_counts_a_co_owned_path_as_one_value() -> None:
    """The joined spelling is a value of its own, not a vote for each owner.

    Two paths owned by ``automation_engine`` alone would otherwise be beaten by
    nothing; here the single co-owned path stays a single vote and loses.
    """
    assert (
        pick_component(
            ["cmk/shared.py", "cmk/base/c.py", "cmk/base/d.py"],
            {
                "cmk/shared.py": "automation_engine, ui_framework",
                "cmk/base/c.py": "automation_engine",
                "cmk/base/d.py": "automation_engine",
            },
        )
        == "automation_engine"
    )


def test_credentials_returns_the_user_before_the_token() -> None:
    """The pair becomes (username, password); swapping it 401s every CI run."""
    assert _credentials({_GERRIT_USER_VAR: "ci-user", _GERRIT_TOKEN_VAR: "secret"}) == (
        "ci-user",
        "secret",
    )


def test_credentials_of_a_half_configured_environment_are_none() -> None:
    """Half a pair cannot authenticate, so let cwz try its own resolution."""
    assert _credentials({_GERRIT_USER_VAR: "ci-user"}) is None
    assert _credentials({_GERRIT_TOKEN_VAR: "secret"}) is None


def test_credentials_of_an_unset_environment_are_none() -> None:
    assert _credentials({}) is None
