#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import override

import pytest
import requests

from cmk.werks.tool.cli.id_pool import (
    _ensure_stash_file_writable,
    _server_error_message,
    add_id_to_stash,
    dump_stash_to_file,
    load_legacy_stash_from_file,
    load_or_update_stash,
    load_stash_from_file,
    make_paths_object,
    migrate_werk_ids_file,
    Paths,
    pick_id_from_stash,
    ServerStatus,
    WerkIDsClient,
    write_secret,
)
from cmk.werks.tool.cli.stash import LegacyStash, Stash
from cmk.werks.tool.cli.werk import WerkId


def _write_secret(paths: Paths) -> None:
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")


def _make_stash_location_unwritable(paths: Paths) -> None:
    # A regular file where the stash directory belongs is the one unwritable state that
    # mode bits cannot express: root may write any file, but no user can create one below
    # a file. Tests relying on modes alone would silently skip whenever they run as root.
    paths.stash_file.parent.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.parent.write_text("", encoding="utf-8")


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
    assert paths.stash_file == tmp_path / ".local/state/cmk-werks/reserved-ids"
    assert paths.secret_file == tmp_path / ".config/cmk-werks/secret"


def test_paths_object_migrates_old_locations(tmp_path: Path) -> None:
    old_secret = tmp_path / ".config/cmk-werk-ids-secret"
    old_stash = tmp_path / ".local/state/cmk-werk-ids-reserved"
    old_secret.parent.mkdir(parents=True, exist_ok=True)
    old_stash.parent.mkdir(parents=True, exist_ok=True)
    old_secret.write_text("secret", encoding="utf-8")
    old_stash.write_text("reserved", encoding="utf-8")

    paths = make_paths_object(tmp_path)

    assert not old_secret.exists()
    assert not old_stash.exists()
    assert paths.secret_file.read_text(encoding="utf-8") == "secret"
    assert paths.stash_file.read_text(encoding="utf-8") == "reserved"


def test_paths_object_migration_does_not_overwrite_new_locations(tmp_path: Path) -> None:
    old_secret = tmp_path / ".config/cmk-werk-ids-secret"
    old_secret.parent.mkdir(parents=True, exist_ok=True)
    old_secret.write_text("old", encoding="utf-8")
    new_secret = tmp_path / ".config/cmk-werks/secret"
    new_secret.parent.mkdir(parents=True, exist_ok=True)
    new_secret.write_text("new", encoding="utf-8")

    paths = make_paths_object(tmp_path)

    assert old_secret.read_text(encoding="utf-8") == "old"
    assert paths.secret_file.read_text(encoding="utf-8") == "new"


def test_write_secret_creates_it_readable_by_the_owner_only(tmp_path: Path) -> None:
    secret_file = make_paths_object(tmp_path).secret_file

    write_secret(secret_file, "s3cret")

    assert secret_file.read_text(encoding="utf-8") == "s3cret"
    assert secret_file.stat().st_mode & 0o777 == 0o600


def test_write_secret_restricts_a_file_that_is_already_there(tmp_path: Path) -> None:
    # os.open() only applies its mode while creating, so rotating a secret used to keep
    # the mode of the existing file
    secret_file = make_paths_object(tmp_path).secret_file
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text("old", encoding="utf-8")
    secret_file.chmod(0o664)

    write_secret(secret_file, "s3cret")

    assert secret_file.read_text(encoding="utf-8") == "s3cret"
    assert secret_file.stat().st_mode & 0o777 == 0o600


def test_paths_object_migration_survives_cross_device_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    old_secret = tmp_path / ".config/cmk-werk-ids-secret"
    old_secret.parent.mkdir(parents=True, exist_ok=True)
    old_secret.write_text("secret", encoding="utf-8")

    def _fail_rename(*_args: object, **_kwargs: object) -> Path:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(Path, "rename", _fail_rename)

    paths = make_paths_object(tmp_path)

    assert old_secret.read_text(encoding="utf-8") == "secret"
    assert not paths.secret_file.exists()
    assert "could not migrate" in capsys.readouterr().err


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
    @override
    def reserve_werk_ids(self, _secret_file_path: Path, _stored_werk_ids: int) -> Sequence[int]:
        return [30, 40]


class FakeEmptyServerClient(WerkIDsClient):
    @override
    def reserve_werk_ids(self, _secret_file_path: Path, _stored_werk_ids: int) -> Sequence[int]:
        return []


class FakeForbiddenServerClient(WerkIDsClient):
    @override
    def reserve_werk_ids(self, _secret_file_path: Path, _stored_werk_ids: int) -> Sequence[int]:
        raise AssertionError("the werk IDs server must not be contacted")


def _prepare_stash(tmp_path: Path, stash: Stash) -> Paths:
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(stash.model_dump_json(by_alias=True), encoding="utf-8")
    return paths


def test_load_or_update_stash_legacy_stash_skips_server(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    legacy = LegacyStash(ids_by_project={"cmk": [1, 2]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")

    stash = load_or_update_stash(paths, FakeWerkIDsClient("http://werk-ids.test"))

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

    stash = load_or_update_stash(paths, FakeWerkIDsClient("http://werk-ids.test"))

    assert isinstance(stash, LegacyStash)
    assert stash.count() == 0


def test_load_or_update_stash_reserves_ids_from_server(tmp_path: Path) -> None:
    paths = _prepare_stash(tmp_path, Stash(ids=[10, 20]))

    stash = load_or_update_stash(paths, FakeWerkIDsClient("http://werk-ids.test"))

    assert isinstance(stash, Stash)
    assert stash.ids == [10, 20, 30, 40]


def test_load_or_update_stash_uses_local_ids_when_server_empty(tmp_path: Path) -> None:
    paths = _prepare_stash(tmp_path, Stash(ids=[10, 20]))

    stash = load_or_update_stash(paths, FakeEmptyServerClient("http://werk-ids.test"))

    assert isinstance(stash, Stash)
    assert stash.ids == [10, 20]


def test_load_or_update_stash_no_ids_anywhere_bails_out(tmp_path: Path) -> None:
    paths = _prepare_stash(tmp_path, Stash(ids=[]))

    with pytest.raises(SystemExit):
        load_or_update_stash(paths, FakeEmptyServerClient("http://werk-ids.test"))


def test_load_or_update_stash_unwritable_stash_location_skips_server(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # IDs reserved from the server are lost when the stash they belong in cannot be
    # written, so the server must not be contacted at all in that case.
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    _make_stash_location_unwritable(paths)

    with pytest.raises(SystemExit):
        load_or_update_stash(paths, FakeForbiddenServerClient("http://werk-ids.test"))

    assert str(paths.stash_file) in capsys.readouterr().err


# ---------------------------------------------------------------------------
# _ensure_stash_file_writable tests
# ---------------------------------------------------------------------------


def test_ensure_stash_file_writable_creates_no_stash_file(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    _write_secret(paths)

    _ensure_stash_file_writable(paths)

    assert not paths.stash_file.exists()


def test_ensure_stash_file_writable_keeps_the_stash(tmp_path: Path) -> None:
    paths = _prepare_stash(tmp_path, Stash(ids=[10, 20]))
    raw_stash = paths.stash_file.read_text(encoding="utf-8")

    _ensure_stash_file_writable(paths)

    assert paths.stash_file.read_text(encoding="utf-8") == raw_stash


def test_ensure_stash_file_writable_bails_out_for_an_unwritable_stash_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The stash file does not exist yet, so the directory it will be created in decides.
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    _make_stash_location_unwritable(paths)

    with pytest.raises(SystemExit):
        _ensure_stash_file_writable(paths)

    assert str(paths.stash_file) in capsys.readouterr().err


def test_load_stash_from_file_bails_when_both_files_exist(tmp_path: Path) -> None:
    # Outside of 'werk init', a legacy and a new stash file must not coexist: loading
    # must exit instead of silently ignoring one of them.
    paths = make_paths_object(tmp_path)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("secret", encoding="utf-8")
    paths.stash_file.write_text(Stash(ids=[5]).model_dump_json(by_alias=True), encoding="utf-8")
    legacy = LegacyStash(ids_by_project={"cmk": [99]})
    paths.legacy_stash_file.write_text(legacy.model_dump_json(by_alias=True), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_stash_from_file(paths)


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


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
    _write_secret(paths)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(Stash(ids=[1]).model_dump_json(by_alias=True), encoding="utf-8")
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [2]}).model_dump_json(by_alias=True), encoding="utf-8"
    )

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


def test_migrate_werk_ids_file_is_idempotent(tmp_path: Path) -> None:
    # Running the migration repeatedly must merge old and new IDs once and then
    # leave the result unchanged, without losing IDs.
    paths = make_paths_object(tmp_path)
    _write_secret(paths)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(Stash(ids=[1]).model_dump_json(by_alias=True), encoding="utf-8")
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [2]}).model_dump_json(by_alias=True), encoding="utf-8"
    )

    migrate_werk_ids_file(paths)
    after_first = paths.stash_file.read_text(encoding="utf-8")

    migrate_werk_ids_file(paths)
    after_second = paths.stash_file.read_text(encoding="utf-8")

    assert after_first == after_second
    assert sorted(Stash.model_validate_json(after_second).ids) == [1, 2]
    assert not paths.legacy_stash_file.exists()


# ---------------------------------------------------------------------------
# Server error response handling
# ---------------------------------------------------------------------------


def _make_response(status_code: int, content: bytes) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    # _content is the documented way to seed a Response body in tests.
    response._content = content  # noqa: SLF001
    return response


def test_server_error_message_from_json_error() -> None:
    response = _make_response(400, json.dumps({"error": "Bad input."}).encode("utf-8"))
    assert _server_error_message(response) == "Bad input."


def test_server_error_message_json_without_error_key() -> None:
    response = _make_response(500, json.dumps({"status": "boom"}).encode("utf-8"))
    assert _server_error_message(response) == '{"status": "boom"}'


def test_server_error_message_non_json_body() -> None:
    response = _make_response(502, b"  Bad Gateway  ")
    assert _server_error_message(response) == "Bad Gateway"


# ---------------------------------------------------------------------------
# Injected server
# ---------------------------------------------------------------------------


# Deliberately not a requests.Session subclass: a method that is not implemented here has
# to fail loudly rather than fall through to the real one and reach the network.
class _FakeHttpSession:
    def __init__(
        self, status_code: int = 200, *, unreachable: bool = False, body: bytes = b"{}"
    ) -> None:
        self.status_code = status_code
        self.unreachable = unreachable
        self.body = body
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def _respond(self, url: str, recorded: Mapping[str, object]) -> requests.Response:
        self.calls.append((url, recorded))
        if self.unreachable:
            raise requests.exceptions.ConnectionError("no route to host")
        return _make_response(self.status_code, self.body)

    def get(
        self, url: str, *, headers: Mapping[str, str] | None = None, timeout: float
    ) -> requests.Response:
        return self._respond(url, {"headers": headers, "timeout": timeout})

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Mapping[str, object] | None = None,
        timeout: float,
    ) -> requests.Response:
        return self._respond(url, {"headers": headers, "json": json, "timeout": timeout})


def _secret_file(tmp_path: Path) -> Path:
    paths = make_paths_object(tmp_path)
    paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
    paths.secret_file.write_text("s3cret\n", encoding="utf-8")
    return paths.secret_file


def test_ensure_connection_against_a_healthy_server() -> None:
    server = _FakeHttpSession(200)

    assert WerkIDsClient("http://werk-ids.test", session=server).ensure_connection() is True
    assert server.calls[0][0] == "http://werk-ids.test"


def test_ensure_connection_against_a_failing_server(capsys: pytest.CaptureFixture[str]) -> None:
    client = WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(500))

    assert client.ensure_connection() is False
    assert "could not connect" in capsys.readouterr().err


def test_ensure_connection_against_an_unreachable_server() -> None:
    client = WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(unreachable=True))

    assert client.ensure_connection() is False


def test_test_connection_sends_the_secret_as_a_bearer_token(tmp_path: Path) -> None:
    server = _FakeHttpSession(200)

    result = WerkIDsClient("http://werk-ids.test", session=server).test_connection(
        _secret_file(tmp_path)
    )

    assert result is True
    url, kwargs = server.calls[0]
    assert url == "http://werk-ids.test/v1/connect"
    assert kwargs["headers"] == {"Authorization": "Bearer s3cret"}


def test_test_connection_with_a_rejected_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(401))

    assert client.test_connection(_secret_file(tmp_path)) is False
    assert "rejected the secret" in capsys.readouterr().err


def test_reserve_werk_ids_against_an_injected_server(tmp_path: Path) -> None:
    # the POST goes through the same session, so the whole client is injectable
    server = _FakeHttpSession(200, body=b'{"reserved_werk_ids": [30, 31]}')

    reserved = WerkIDsClient("http://werk-ids.test", session=server).reserve_werk_ids(
        _secret_file(tmp_path), 8
    )

    assert list(reserved) == [30, 31]
    url, kwargs = server.calls[0]
    assert url == "http://werk-ids.test/v1/reserve"
    assert kwargs["json"] == {"local_werk_ids_count": 8}


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        pytest.param(200, ServerStatus.OK, id="200 -> ok"),
        pytest.param(401, ServerStatus.UNAUTHORIZED, id="401 -> unauthorized"),
        pytest.param(403, ServerStatus.UNAUTHORIZED, id="403 -> unauthorized"),
        pytest.param(500, ServerStatus.ERROR, id="500 -> error"),
        pytest.param(502, ServerStatus.ERROR, id="502 -> error"),
    ],
)
def test_check_maps_status_code(tmp_path: Path, status_code: int, expected: ServerStatus) -> None:
    client = WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(status_code))

    assert client.check(_secret_file(tmp_path)) == expected


def test_check_unreachable(tmp_path: Path) -> None:
    client = WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(unreachable=True))

    assert client.check(_secret_file(tmp_path)) == ServerStatus.UNREACHABLE


def test_check_sends_stripped_secret_as_bearer_token(tmp_path: Path) -> None:
    server = _FakeHttpSession(200)

    WerkIDsClient("http://werk-ids.test", session=server).check(_secret_file(tmp_path))

    url, kwargs = server.calls[0]
    assert url == "http://werk-ids.test/v1/connect"
    assert kwargs["headers"] == {"Authorization": "Bearer s3cret"}


def test_check_is_quiet(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    WerkIDsClient("http://werk-ids.test", session=_FakeHttpSession(unreachable=True)).check(
        _secret_file(tmp_path)
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
