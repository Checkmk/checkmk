#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.werks.id_pool import (
    add_id_to_stash,
    dump_stash_to_file,
    load_legacy_stash_from_file,
    load_or_update_stash,
    load_stash_from_file,
    make_paths_object,
    migrate_werk_ids_file,
    Paths,
    pick_id_from_stash,
    WerkIDsClient,
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
    assert sorted(stash.ids) == [1, 2, 3]


def test_stash_add_ids_deduplicates() -> None:
    stash = Stash(ids=[1, 2])
    stash.add_ids([WerkId(2), WerkId(3)])
    assert sorted(stash.ids) == [1, 2, 3]


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


def test_load_stash_from_file_no_files_returns_empty_legacy(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    result = load_stash_from_file(paths)
    assert isinstance(result, LegacyStash)
    assert result.count() == 0


def test_load_stash_from_file_no_secret_falls_back_to_legacy(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    legacy = LegacyStash(ids_by_project={"cmk": [10, 20]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")
    result = load_stash_from_file(paths)
    assert isinstance(result, LegacyStash)
    assert result.ids_by_project == {"cmk": [10, 20]}


def test_load_stash_from_file_secret_no_stash_returns_empty_stash(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    result = load_stash_from_file(paths)
    assert isinstance(result, Stash)
    assert result.ids == []


# ---------------------------------------------------------------------------
# load_or_update_stash tests
# ---------------------------------------------------------------------------


class FakeWerkIDsClient(WerkIDsClient):
    def reserve_werk_ids(self, _secret_file_path: Path, _stored_werk_ids: int) -> Sequence[int]:
        return [30, 40]


class FakeEmptyServerClient(WerkIDsClient):
    def reserve_werk_ids(self, _secret_file_path: Path, _stored_werk_ids: int) -> Sequence[int]:
        return []


def test_load_or_update_stash_legacy_stash_skips_server(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    legacy = LegacyStash(ids_by_project={"cmk": [1, 2]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")

    stash = load_or_update_stash(paths, FakeWerkIDsClient())

    assert isinstance(stash, LegacyStash)
    assert stash.ids_by_project == {"cmk": [1, 2]}


def test_load_or_update_stash_no_secret_skips_server(tmp_path: Path) -> None:
    # Without a secret file, load_stash_from_file falls back to LegacyStash, so the server
    # is never contacted (load_or_update_stash returns early for LegacyStash).
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(
        Stash(ids=[10, 20]).model_dump_json(by_alias=True), encoding="utf-8"
    )

    stash = load_or_update_stash(paths, FakeWerkIDsClient())

    assert isinstance(stash, LegacyStash)
    assert stash.count() == 0


def test_load_or_update_stash_reserves_ids_from_server(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    paths.stash_file.write_text(
        Stash(ids=[10, 20]).model_dump_json(by_alias=True), encoding="utf-8"
    )

    stash = load_or_update_stash(paths, FakeWerkIDsClient())

    assert isinstance(stash, Stash)
    assert sorted(stash.ids) == [10, 20, 30, 40]


def test_load_or_update_stash_uses_local_ids_when_server_empty(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    paths.stash_file.write_text(
        Stash(ids=[10, 20]).model_dump_json(by_alias=True), encoding="utf-8"
    )

    stash = load_or_update_stash(paths, FakeEmptyServerClient())

    assert isinstance(stash, Stash)
    assert stash.ids == [10, 20]


def test_load_or_update_stash_no_ids_anywhere_bails_out(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    paths.stash_file.write_text(Stash(ids=[]).model_dump_json(by_alias=True), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_or_update_stash(paths, FakeEmptyServerClient())


def test_load_stash_from_file_prefers_new_stash(tmp_path: Path) -> None:
    # Both stash formats present; new format wins only when secret_file also exists.
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    paths.stash_file.write_text(Stash(ids=[5]).model_dump_json(by_alias=True), encoding="utf-8")
    legacy = LegacyStash(ids_by_project={"cmk": [99]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")

    result = load_stash_from_file(paths)
    assert isinstance(result, Stash)
    assert result.ids == [5]


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


def _write_secret(paths: Paths) -> None:
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")


def test_migrate_no_legacy_file_writes_empty_stash(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    migrate_werk_ids_file(paths)
    assert paths.stash_file.exists()
    assert Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8")).ids == []


def test_migrate_empty_legacy_file_writes_empty_stash(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    paths.legacy_stash_file.write_text("", encoding="utf-8")
    migrate_werk_ids_file(paths)
    assert paths.stash_file.exists()
    assert Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8")).ids == []
    assert not paths.legacy_stash_file.exists()


def test_migrate_json_legacy_file(tmp_path: Path) -> None:
    # Only "cmk" project IDs are migrated; other projects (e.g. "cloudmk") are dropped.
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    legacy = LegacyStash(ids_by_project={"cmk": [10, 11], "cloudmk": [1000]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")

    migrate_werk_ids_file(paths)

    assert paths.stash_file.exists()
    new_stash = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
    assert sorted(new_stash.ids) == [10, 11]
    assert not paths.legacy_stash_file.exists()


def test_migrate_list_legacy_file(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    paths.legacy_stash_file.write_text("[42, 43]", encoding="utf-8")

    migrate_werk_ids_file(paths)

    new_stash = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
    assert sorted(new_stash.ids) == [42, 43]
    assert not paths.legacy_stash_file.exists()


def test_migrate_werk_ids_file_merges_both_files(tmp_path: Path) -> None:
    # When the new stash file already exists, legacy IDs are merged into it.
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(Stash(ids=[1]).model_dump_json(by_alias=True), encoding="utf-8")
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [2]}).model_dump_json(by_alias=True), encoding="utf-8"
    )
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")

    migrate_werk_ids_file(paths)

    new_stash = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
    assert sorted(new_stash.ids) == [1, 2]
    assert not paths.legacy_stash_file.exists()


def test_migrate_werk_ids_file_deduplicates_overlapping_ids(tmp_path: Path) -> None:
    # IDs present in both the new stash and the legacy file must not be duplicated.
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(Stash(ids=[1, 2]).model_dump_json(by_alias=True), encoding="utf-8")
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [2, 3]}).model_dump_json(by_alias=True),
        encoding="utf-8",
    )

    migrate_werk_ids_file(paths)

    new_stash = Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
    assert sorted(new_stash.ids) == [1, 2, 3]
    assert not paths.legacy_stash_file.exists()
