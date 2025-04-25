#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pprint

from cmk.ccc.hostaddress import HostAddress

import cmk.utils.log
import cmk.utils.paths

from cmk.piggyback import backend

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

    pprint.pprint(piggybacked)  # pytest won't show it :-(
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
