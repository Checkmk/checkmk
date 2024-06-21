#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pprint

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress

from cmk import piggyback

_TEST_HOST_NAME = HostAddress("test-host")

_PAYLOAD = (
    b"pay",
    b"load",
)

_REF_TIME = 1640000000.0


def _get_only_raw_data_element(host_name: HostAddress) -> piggyback.PiggybackRawDataInfo:
    first, *other = piggyback.get_piggyback_raw_data(host_name)
    assert not other
    return first


def test_get_piggyback_raw_data_no_data() -> None:
    assert not piggyback.get_piggyback_raw_data(HostAddress("no-host"))


def test_store_piggyback_raw_data_simple() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source"), {_TEST_HOST_NAME: (b"line1", b"line2")}, timestamp=_REF_TIME
    )

    stored = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert stored.info.source == HostAddress("source")
    assert stored.info.last_update == _REF_TIME
    assert stored.raw_data == b"line1\nline2\n"


def test_get_piggyback_raw_data_not_updated() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {_TEST_HOST_NAME: _PAYLOAD}, _REF_TIME
    )
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {HostAddress("some-other-host"): _PAYLOAD}, _REF_TIME + 10
    )

    info = _get_only_raw_data_element(_TEST_HOST_NAME).info

    assert info.source == HostAddress("source1")
    assert info.last_contact == _REF_TIME + 10
    assert info.last_update == _REF_TIME


def test_get_piggyback_raw_data_not_sending() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {_TEST_HOST_NAME: _PAYLOAD}, _REF_TIME
    )
    piggyback.store_piggyback_raw_data(HostAddress("source1"), {}, _REF_TIME)

    info = _get_only_raw_data_element(_TEST_HOST_NAME).info

    assert info.source == "source1"
    assert info.last_contact is None
    assert info.last_update == _REF_TIME


def test_remove_source_status_file_not_existing() -> None:
    assert piggyback.remove_source_status_file(HostAddress("nosource")) is False


def test_remove_source_status_file() -> None:
    piggyback.store_piggyback_raw_data(HostAddress("source1"), {_TEST_HOST_NAME: (b"",)}, _REF_TIME)
    assert piggyback.remove_source_status_file(HostAddress("source1")) is True


def test_store_piggyback_raw_data_second_source() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {_TEST_HOST_NAME: _PAYLOAD}, _REF_TIME
    )

    piggyback.store_piggyback_raw_data(
        HostAddress("source2"), {_TEST_HOST_NAME: _PAYLOAD}, _REF_TIME + 10.0
    )

    raw_data_map = {
        rd.info.source: rd.info for rd in piggyback.get_piggyback_raw_data(_TEST_HOST_NAME)
    }
    assert len(raw_data_map) == 2

    assert (raw1 := raw_data_map[HostAddress("source1")]).last_update == _REF_TIME
    assert raw1.last_contact == _REF_TIME
    assert (raw2 := raw_data_map[HostAddress("source2")]).last_update == _REF_TIME + 10.0
    assert raw2.last_contact == _REF_TIME + 10.0


def test_get_source_and_piggyback_hosts() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {HostAddress("test-host"): _PAYLOAD}, _REF_TIME - 10.0
    )

    piggyback.store_piggyback_raw_data(
        HostAddress("source1"), {HostAddress("test-host2"): _PAYLOAD}, _REF_TIME
    )

    piggyback.store_piggyback_raw_data(
        HostAddress("source2"),
        {
            HostAddress("test-host2"): _PAYLOAD,
            HostAddress("test-host"): _PAYLOAD,
        },
        _REF_TIME,
    )

    piggybacked = piggyback.get_piggybacked_host_with_sources()

    pprint.pprint(piggybacked)  # pytest won't show it :-(
    assert piggybacked == {
        HostAddress("test-host"): [
            piggyback.PiggybackFileInfo(
                source=HostAddress("source1"),
                file_path=cmk.utils.paths.piggyback_dir / "test-host" / "source1",
                last_update=int(_REF_TIME - 10),
                last_contact=int(_REF_TIME),
            ),
            piggyback.PiggybackFileInfo(
                source=HostAddress("source2"),
                file_path=cmk.utils.paths.piggyback_dir / "test-host" / "source2",
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
        ],
        HostAddress("test-host2"): [
            piggyback.PiggybackFileInfo(
                source=HostAddress("source1"),
                file_path=cmk.utils.paths.piggyback_dir / "test-host2" / "source1",
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
            piggyback.PiggybackFileInfo(
                source=HostAddress("source2"),
                file_path=cmk.utils.paths.piggyback_dir / "test-host2" / "source2",
                last_update=int(_REF_TIME),
                last_contact=int(_REF_TIME),
            ),
        ],
    }
