#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os
import pprint
from datetime import datetime, timezone

import time_machine

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress

from cmk import piggyback

_TEST_HOST_NAME = HostAddress("test-host")

_PAYLOAD = b"<<<check_mk>>>\nlala\n"

_REF_TIME = 1640000000.0
_FREEZE_DATETIME = datetime.fromtimestamp(_REF_TIME + 10.0, tz=timezone.utc)


def setup_files() -> None:
    host_dir = cmk.utils.paths.piggyback_dir / str(_TEST_HOST_NAME)
    host_dir.mkdir(parents=True, exist_ok=False)

    source_file = host_dir / "source1"
    with source_file.open(mode="wb") as f2:
        f2.write(_PAYLOAD)

    cmk.utils.paths.piggyback_source_dir.mkdir(parents=True, exist_ok=False)
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    with source_status_file.open("wb") as f3:
        f3.write(b"")

    os.utime(str(source_file), (_REF_TIME, _REF_TIME))
    os.utime(str(source_status_file), (_REF_TIME, _REF_TIME))


def test_get_piggyback_raw_data_no_data() -> None:
    assert not piggyback.get_piggyback_raw_data(HostAddress("no-host"))


def _get_only_raw_data_element(
    host_name: HostAddress,
) -> piggyback.PiggybackRawDataInfo:
    with time_machine.travel(_FREEZE_DATETIME):
        raw_data_sequence = piggyback.get_piggyback_raw_data(host_name)
    assert len(raw_data_sequence) == 1
    return raw_data_sequence[0]


def test_get_piggyback_raw_data_not_updated() -> None:
    setup_files()
    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / str(_TEST_HOST_NAME) / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert raw_data.info.source == HostAddress("source1")
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_not_sending() -> None:
    setup_files()
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert raw_data.info.source == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.raw_data == _PAYLOAD


def test_remove_source_status_file_not_existing() -> None:
    assert piggyback.remove_source_status_file(HostAddress("nosource")) is False


def test_remove_source_status_file() -> None:
    setup_files()
    assert piggyback.remove_source_status_file(HostAddress("source1")) is True


def test_store_piggyback_raw_data_new_host() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source2"),
        {
            HostAddress("pig"): [
                b"<<<check_mk>>>",
                b"lulu",
            ]
        },
    )

    raw_data = _get_only_raw_data_element(HostAddress("pig"))

    assert raw_data.info.source == "source2"
    assert raw_data.info.file_path.parts[-2:] == ("pig", "source2")
    assert raw_data.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_store_piggyback_raw_data_second_source() -> None:
    setup_files()

    with time_machine.travel(_FREEZE_DATETIME):
        piggyback.store_piggyback_raw_data(
            HostAddress("source2"),
            {
                _TEST_HOST_NAME: [
                    b"<<<check_mk>>>",
                    b"lulu",
                ]
            },
        )

        raw_data_map = {
            rd.info.source: rd for rd in piggyback.get_piggyback_raw_data(_TEST_HOST_NAME)
        }
    assert len(raw_data_map) == 2

    raw_data1, raw_data2 = (
        raw_data_map[HostAddress("source1")],
        raw_data_map[HostAddress("source2")],
    )

    assert raw_data1.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source1")
    assert raw_data1.raw_data == _PAYLOAD

    assert raw_data2.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source2")
    assert raw_data2.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_get_source_and_piggyback_hosts() -> None:
    piggyback.store_piggyback_raw_data(
        HostAddress("source1"),
        {
            HostAddress("test-host2"): [
                b"<<<check_mk>>>",
                b"source1",
            ],
            HostAddress("test-host"): [
                b"<<<check_mk>>>",
                b"source1",
            ],
        },
    )

    piggyback.store_piggyback_raw_data(
        HostAddress("source2"),
        {
            HostAddress("test-host2"): [
                b"<<<check_mk>>>",
                b"source2",
            ],
            HostAddress("test-host"): [
                b"<<<check_mk>>>",
                b"source2",
            ],
        },
    )

    # Fake the ages
    os.utime(
        cmk.utils.paths.piggyback_source_dir / "source1",
        (_REF_TIME, _REF_TIME),
    )
    os.utime(
        cmk.utils.paths.piggyback_source_dir / "source2",
        (_REF_TIME, _REF_TIME),
    )
    os.utime(
        cmk.utils.paths.piggyback_dir / "test-host" / "source1",
        (_REF_TIME - 10, _REF_TIME - 10),
    )
    os.utime(
        cmk.utils.paths.piggyback_dir / "test-host" / "source2",
        (_REF_TIME, _REF_TIME),
    )
    os.utime(
        cmk.utils.paths.piggyback_dir / "test-host2" / "source1",
        (_REF_TIME, _REF_TIME),
    )
    os.utime(
        cmk.utils.paths.piggyback_dir / "test-host2" / "source2",
        (_REF_TIME, _REF_TIME),
    )

    with time_machine.travel(_FREEZE_DATETIME):
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
