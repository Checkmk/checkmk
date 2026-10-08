#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import pprint
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.hostaddress import HostAddress
from cmk.piggyback import backend
from cmk.piggyback.backend._storage import _remove_files_older_than, _remove_folder_if_empty

_TEST_HOST_NAME = HostAddress("test-host")

_PAYLOAD = (
    b"pay",
    b"load",
)

_REF_TIME = 1640000000.0


def _get_only_raw_data_element(host_name: HostAddress) -> backend.PiggybackMessage:
    first, *other = backend.get_messages_for(host_name, cmk.utils.paths.omd_root)
    assert not other
    return first


def test_get_piggyback_raw_data_no_data() -> None:
    assert not backend.get_messages_for(HostAddress("no-host"), cmk.utils.paths.omd_root)


def test_store_piggyback_raw_data_simple() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source"),
        {_TEST_HOST_NAME: (b"line1", b"line2")},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )

    stored = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert stored.meta.source == HostAddress("source")
    assert stored.meta.last_update == _REF_TIME
    assert stored.raw_data == b"line1\nline2\n"


def test_get_piggyback_raw_data_not_updated() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {_TEST_HOST_NAME: _PAYLOAD},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {HostAddress("some-other-host"): _PAYLOAD},
        message_timestamp=_REF_TIME + 10,
        contact_timestamp=_REF_TIME + 10,
        omd_root=cmk.utils.paths.omd_root,
    )

    info = _get_only_raw_data_element(_TEST_HOST_NAME).meta

    assert info.source == HostAddress("source1")
    assert info.last_contact == _REF_TIME + 10
    assert info.last_update == _REF_TIME


def test_get_piggyback_raw_data_not_sending() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {_TEST_HOST_NAME: _PAYLOAD},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {},
        message_timestamp=_REF_TIME,
        contact_timestamp=None,
        omd_root=cmk.utils.paths.omd_root,
    )

    info = _get_only_raw_data_element(_TEST_HOST_NAME).meta

    assert info.source == "source1"
    assert info.last_contact is None
    assert info.last_update == _REF_TIME


def test_remove_source_status_file_not_existing() -> None:
    assert (
        backend.remove_source_status_file(HostAddress("nosource"), cmk.utils.paths.omd_root)
        is False
    )


def test_remove_source_status_file() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {_TEST_HOST_NAME: (b"",)},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )
    assert (
        backend.remove_source_status_file(HostAddress("source1"), cmk.utils.paths.omd_root) is True
    )


def test_store_piggyback_raw_data_second_source() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {_TEST_HOST_NAME: _PAYLOAD},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )

    backend.store_piggyback_raw_data(
        HostAddress("source2"),
        {_TEST_HOST_NAME: _PAYLOAD},
        message_timestamp=_REF_TIME + 10.0,
        contact_timestamp=_REF_TIME + 10.0,
        omd_root=cmk.utils.paths.omd_root,
    )

    raw_data_map = {
        rd.meta.source: rd.meta
        for rd in backend.get_messages_for(_TEST_HOST_NAME, cmk.utils.paths.omd_root)
    }
    assert len(raw_data_map) == 2

    assert (raw1 := raw_data_map[HostAddress("source1")]).last_update == _REF_TIME
    assert raw1.last_contact == _REF_TIME
    assert (raw2 := raw_data_map[HostAddress("source2")]).last_update == _REF_TIME + 10.0
    assert raw2.last_contact == _REF_TIME + 10.0


def test_store_piggyback_raw_data_different_timestamp() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {_TEST_HOST_NAME: _PAYLOAD},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME + 10.0,
        omd_root=cmk.utils.paths.omd_root,
    )
    raw_data_map = {
        rd.meta.source: rd.meta
        for rd in backend.get_messages_for(_TEST_HOST_NAME, cmk.utils.paths.omd_root)
    }

    assert (raw1 := raw_data_map[HostAddress("source1")]).last_update == _REF_TIME
    assert raw1.last_contact == _REF_TIME + 10.0


def test_get_source_and_piggyback_hosts() -> None:
    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {HostAddress("test-host"): _PAYLOAD},
        message_timestamp=_REF_TIME - 10.0,
        contact_timestamp=_REF_TIME - 10.0,
        omd_root=cmk.utils.paths.omd_root,
    )

    backend.store_piggyback_raw_data(
        HostAddress("source1"),
        {HostAddress("test-host2"): _PAYLOAD},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )

    backend.store_piggyback_raw_data(
        HostAddress("source2"),
        {
            HostAddress("test-host2"): _PAYLOAD,
            HostAddress("test-host"): _PAYLOAD,
        },
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )

    piggybacked = backend.get_piggybacked_host_with_sources(cmk.utils.paths.omd_root)

    pprint.pprint(piggybacked)  # pytest won't show it :-(  # noqa: T203
    assert piggybacked == {
        HostAddress("test-host"): [
            backend.PiggybackMetaData(
                source=HostAddress("source1"),
                piggybacked=HostAddress("test-host"),
                last_update=int(_REF_TIME - 10),
                last_contact=int(_REF_TIME),
            ),
            backend.PiggybackMetaData(
                source=HostAddress("source2"),
                piggybacked=HostAddress("test-host"),
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
        ],
        HostAddress("test-host2"): [
            backend.PiggybackMetaData(
                source=HostAddress("source1"),
                piggybacked=HostAddress("test-host2"),
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
            backend.PiggybackMetaData(
                source=HostAddress("source2"),
                piggybacked=HostAddress("test-host2"),
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
        ],
    }


_MAX_AGE = 3600


def _store_aged(
    omd_root: Path,
    *,
    source: str = "source",
    piggybacked: str = "piggybacked",
    message_age: float = 0.0,
    contact_age: float = 0.0,
) -> None:
    backend.store_piggyback_raw_data(
        HostAddress(source),
        {HostAddress(piggybacked): _PAYLOAD},
        message_timestamp=_REF_TIME - message_age,
        contact_timestamp=_REF_TIME - contact_age,
        omd_root=omd_root,
    )


def _cleanup(
    omd_root: Path,
    max_cache_file_age: int = _MAX_AGE,
    rule_values: Sequence[Mapping[str, object]] = (),
) -> None:
    backend.cleanup_piggyback_files(
        now=_REF_TIME,
        max_cache_file_age=max_cache_file_age,
        all_configured_rule_values=rule_values,
        omd_root=omd_root,
    )


@pytest.mark.parametrize(
    "message_age, expected_sources",
    [
        pytest.param(_MAX_AGE + 1, set(), id="older than cut-off: removed"),
        pytest.param(_MAX_AGE, {"source"}, id="exactly at cut-off: kept"),
        pytest.param(_MAX_AGE - 1, {"source"}, id="newer than cut-off: kept"),
    ],
)
def test_cleanup_removes_payload_older_than_cut_off(
    tmp_path: Path, message_age: float, expected_sources: set[str]
) -> None:
    _store_aged(tmp_path, message_age=message_age)

    _cleanup(tmp_path)

    assert (
        backend.get_current_piggyback_sources_of_host(tmp_path, HostAddress("piggybacked"))
        == expected_sources
    )


@pytest.mark.parametrize(
    "contact_age, expected_last_contact",
    [
        pytest.param(_MAX_AGE + 1, None, id="older than cut-off: removed"),
        pytest.param(_MAX_AGE, int(_REF_TIME - _MAX_AGE), id="exactly at cut-off: kept"),
        pytest.param(_MAX_AGE - 1, int(_REF_TIME - _MAX_AGE + 1), id="newer than cut-off: kept"),
    ],
)
def test_cleanup_removes_source_status_file_older_than_cut_off(
    tmp_path: Path, contact_age: float, expected_last_contact: int | None
) -> None:
    _store_aged(tmp_path, contact_age=contact_age)

    _cleanup(tmp_path)

    (message,) = backend.get_messages_for(HostAddress("piggybacked"), tmp_path)
    assert message.meta.last_contact == expected_last_contact


# fmt: off
@pytest.mark.parametrize(
    "max_cache_file_age, rule_values, effective_max_age",
    [
        pytest.param(3600, [], 3600, id="empty ruleset: global setting applies"),
        pytest.param(3600, [{"global_max_cache_age": 60}], 3600, id="global setting larger than rule"),
        pytest.param(60, [{"global_max_cache_age": 3600}], 3600, id="rule larger than global setting"),
        pytest.param(60, [{"per_piggybacked_host": [{"max_cache_age": 3600}]}], 3600, id="per-host exception larger than global setting"),
        pytest.param(60, [{"global_max_cache_age": 120}, {"global_max_cache_age": 3600}], 3600, id="largest value across rules"),
        pytest.param(60, [{"global_max_cache_age": "global", "per_piggybacked_host": [{"max_cache_age": "global"}]}], 60, id="non-integer values ignored"),
        pytest.param(60, [{"per_piggybacked_host": [{}]}], 60, id="rule without max age ignored"),
    ],
)
# fmt: on
def test_cleanup_cut_off_uses_largest_configured_max_age(
    tmp_path: Path,
    max_cache_file_age: int,
    rule_values: Sequence[Mapping[str, object]],
    effective_max_age: int,
) -> None:
    _store_aged(tmp_path, piggybacked="aged-out", message_age=effective_max_age + 1)
    _store_aged(tmp_path, piggybacked="still-valid", message_age=effective_max_age)

    _cleanup(tmp_path, max_cache_file_age, rule_values)

    assert set(backend.get_piggybacked_host_with_sources(tmp_path)) == {"still-valid"}


def test_cleanup_removes_emptied_piggybacked_host_folder(tmp_path: Path) -> None:
    _store_aged(tmp_path, message_age=_MAX_AGE + 1)

    _cleanup(tmp_path)

    assert not backend.get_piggybacked_host_with_sources(tmp_path)


def test_cleanup_keeps_piggybacked_host_folder_with_fresh_payload(tmp_path: Path) -> None:
    _store_aged(tmp_path, source="stale-source", message_age=_MAX_AGE + 1)
    _store_aged(tmp_path, source="fresh-source")

    _cleanup(tmp_path)

    assert backend.get_current_piggyback_sources_of_host(
        tmp_path, HostAddress("piggybacked")
    ) == {"fresh-source"}


# These two call private functions on purpose: a file or folder vanishing while the
# cleanup runs (another process removing it) can't be provoked through
# cleanup_piggyback_files without patching the filesystem.
def test_remove_files_older_than_continues_after_vanished_file(tmp_path: Path) -> None:
    expired = tmp_path / "expired"
    expired.touch()
    os.utime(expired, (_REF_TIME - 1, _REF_TIME - 1))

    _remove_files_older_than([tmp_path / "vanished", expired], _REF_TIME)

    assert not expired.exists()


def test_remove_folder_if_empty_tolerates_vanished_folder(tmp_path: Path) -> None:
    _remove_folder_if_empty(tmp_path / "vanished")


class TestPiggybackMetaData:
    def test_serialization_roundtrip(self) -> None:
        pmd = backend.PiggybackMetaData(
            source=HostAddress("source1"),
            piggybacked=HostAddress("test-host"),
            last_update=int(_REF_TIME - 10),
            last_contact=int(_REF_TIME),
        )
        assert backend.PiggybackMetaData.deserialize(pmd.serialize()) == pmd

    def test_serialization_roundtrip_with_none(self) -> None:
        pmd = backend.PiggybackMetaData(
            source=HostAddress("source1"),
            piggybacked=HostAddress("test-host"),
            last_update=int(_REF_TIME - 10),
            last_contact=None,
        )
        assert backend.PiggybackMetaData.deserialize(pmd.serialize()) == pmd
