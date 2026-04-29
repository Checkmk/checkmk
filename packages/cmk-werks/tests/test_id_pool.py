#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.werks.id_pool import (
    add_id_to_stash,
    dump_stash_to_file,
    load_legacy_stash_from_file,
    make_paths_object,
    pick_id_from_stash,
)
from cmk.werks.schemas.werk import LegacyStash, Stash, WerkId

# ---------------------------------------------------------------------------
# Stash unit tests
# ---------------------------------------------------------------------------


def test_stash_count_empty() -> None:
    assert Stash().count() == 0


def test_stash_count() -> None:
    assert Stash(ids=[1, 2, 3]).count() == 3


def test_stash_pick_id_returns_smallest() -> None:
    stash = Stash(ids=[30, 10, 20])
    assert stash.pick_id() == WerkId(10)


def test_stash_pick_id_empty_raises() -> None:
    with pytest.raises(RuntimeError, match="no Werk IDs"):
        Stash().pick_id()


def test_stash_free_id_removes_it() -> None:
    stash = Stash(ids=[1, 2, 3])
    stash.free_id(WerkId(2))
    assert stash.ids == [1, 3]


def test_stash_free_id_unknown_raises() -> None:
    stash = Stash(ids=[1, 2])
    with pytest.raises(RuntimeError, match="Could not find werk_id"):
        stash.free_id(WerkId(99))


def test_stash_add_ids() -> None:
    stash = Stash(ids=[1])
    stash.add_ids([WerkId(2), WerkId(3)])
    assert stash.ids == [1, 2, 3]


# ---------------------------------------------------------------------------
# load_legacy_stash_from_file tests
# ---------------------------------------------------------------------------


def test_load_legacy_stash_missing_file(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    stash = load_legacy_stash_from_file(paths)
    assert stash.count() == 0


def test_load_legacy_stash_empty_file(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.legacy_stash_file.write_text("", encoding="utf-8")
    stash = load_legacy_stash_from_file(paths)
    assert stash.count() == 0


def test_load_legacy_stash_json_format(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    legacy = LegacyStash(ids_by_project={"cmk": [10, 11, 12]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")
    stash = load_legacy_stash_from_file(paths)
    assert stash.ids_by_project == {"cmk": [10, 11, 12]}


def test_load_legacy_stash_list_format(tmp_path: Path) -> None:
    # Old cmk-project format: bare Python list
    paths = make_paths_object(tmp_path)
    paths.legacy_stash_file.write_text("[10, 11, 12]", encoding="utf-8")
    stash = load_legacy_stash_from_file(paths)
    assert stash.ids_by_project == {"cmk": [10, 11, 12]}


# ---------------------------------------------------------------------------
# dump_stash_to_file tests
# ---------------------------------------------------------------------------


def test_dump_and_load_legacy_stash(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    legacy = LegacyStash(ids_by_project={"cmk": [1, 2]})
    dump_stash_to_file(paths, legacy)
    assert paths.legacy_stash_file.exists()
    loaded = load_legacy_stash_from_file(paths)
    assert loaded.ids_by_project == {"cmk": [1, 2]}


def test_dump_new_stash_writes_to_stash_file(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    stash = Stash(ids=[5, 6, 7])
    dump_stash_to_file(paths, stash)
    assert paths.stash_file.exists()
    loaded = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
    assert loaded.ids == [5, 6, 7]


# ---------------------------------------------------------------------------
# pick_id_from_stash / add_id_to_stash tests
# ---------------------------------------------------------------------------


def test_pick_id_from_legacy_stash() -> None:
    stash = LegacyStash(ids_by_project={"cmk": [10, 20, 5]})
    assert pick_id_from_stash(stash, "cmk") == WerkId(5)


def test_pick_id_from_new_stash() -> None:
    stash = Stash(ids=[10, 20, 5])
    assert pick_id_from_stash(stash, "cmk") == WerkId(5)


def test_add_id_to_legacy_stash() -> None:
    stash = LegacyStash(ids_by_project={"cmk": [1]})
    add_id_to_stash(stash, WerkId(2), "cmk")
    assert 2 in stash.ids_by_project["cmk"]


def test_add_id_to_new_stash() -> None:
    stash = Stash(ids=[1])
    add_id_to_stash(stash, WerkId(2), "cmk")
    assert 2 in stash.ids


# ---------------------------------------------------------------------------
# Paths tests
# ---------------------------------------------------------------------------


def test_paths_object(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    assert paths.legacy_stash_file == tmp_path / ".cmk-werk-ids"
    assert paths.stash_file == tmp_path / ".local/cmk-werks/reserved-ids"
    assert paths.secret_file == tmp_path / ".local/cmk-werks/secret"


def test_active_stash_file_without_secret(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    assert paths.active_stash_file == paths.legacy_stash_file


def test_active_stash_file_with_secret(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    assert paths.active_stash_file == paths.stash_file
