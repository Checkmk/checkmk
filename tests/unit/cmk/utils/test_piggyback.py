#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os
import pprint
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import pytest
import time_machine
from pytest import MonkeyPatch

import cmk.utils.log
import cmk.utils.paths
from cmk.utils import piggyback
from cmk.utils.hostaddress import HostAddress, HostName

_PIGGYBACK_MAX_CACHEFILE_AGE = 3600

_TEST_HOST_NAME = HostName("test-host")

_PAYLOAD = b"<<<check_mk>>>\nlala\n"

_REF_TIME = 1640000000.0
_FREEZE_DATETIME = datetime.fromtimestamp(_REF_TIME + 10.0, tz=timezone.utc)


@pytest.fixture(name="setup_files")
def fixture_setup_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.utils.paths.piggyback_dir", tmp_path / "piggyback")
    monkeypatch.setattr("cmk.utils.paths.piggyback_source_dir", tmp_path / "piggyback_source")

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
    assert not piggyback.get_piggyback_raw_data(HostName("no-host"))


def _get_only_raw_data_element(
    host_name: HostName,
) -> piggyback.PiggybackRawDataInfo:
    with time_machine.travel(_FREEZE_DATETIME):
        raw_data_sequence = piggyback.get_piggyback_raw_data(host_name)
    assert len(raw_data_sequence) == 1
    return raw_data_sequence[0]


@pytest.mark.parametrize(
    "time_settings",
    [
        [
            (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("not-source", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("test-host", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ],
        [
            (None, "max_cache_age", -1),
            ("test-host", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("not-test-host", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("not-test-host", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ],
        [
            (None, "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("~TEST-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("~TEST-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("~test-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
            ("test-host", "max_cache_age", -1),
        ],
    ],
)
@pytest.mark.usefixtures("setup_files")
def test_get_piggyback_raw_data_successful(time_settings: piggyback.PiggybackTimeSettings) -> None:
    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert raw_data.info.source == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.usefixtures("setup_files")
def test_get_piggyback_raw_data_not_updated() -> None:
    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / str(_TEST_HOST_NAME) / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert raw_data.info.source == HostName("source1")
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.usefixtures("setup_files")
def test_get_piggyback_raw_data_not_sending() -> None:
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME)

    assert raw_data.info.source == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.raw_data == _PAYLOAD


def test_remove_source_status_file_not_existing() -> None:
    assert piggyback.remove_source_status_file(HostName("nosource")) is False


@pytest.mark.usefixtures("setup_files")
def test_remove_source_status_file() -> None:
    assert piggyback.remove_source_status_file(HostName("source1")) is True


def test_store_piggyback_raw_data_new_host() -> None:
    piggyback.store_piggyback_raw_data(
        HostName("source2"),
        {
            HostName("pig"): [
                b"<<<check_mk>>>",
                b"lulu",
            ]
        },
    )

    raw_data = _get_only_raw_data_element(HostName("pig"))

    assert raw_data.info.source == "source2"
    assert raw_data.info.file_path.parts[-2:] == ("pig", "source2")
    assert raw_data.raw_data == b"<<<check_mk>>>\nlulu\n"


@pytest.mark.usefixtures("setup_files")
def test_store_piggyback_raw_data_second_source() -> None:

    with time_machine.travel(_FREEZE_DATETIME):
        piggyback.store_piggyback_raw_data(
            HostName("source2"),
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

    raw_data1, raw_data2 = raw_data_map[HostName("source1")], raw_data_map[HostName("source2")]

    assert raw_data1.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source1")
    assert raw_data1.raw_data == _PAYLOAD

    assert raw_data2.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source2")
    assert raw_data2.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_get_source_and_piggyback_hosts() -> None:
    piggyback.store_piggyback_raw_data(
        HostName("source1"),
        {
            HostName("test-host2"): [
                b"<<<check_mk>>>",
                b"source1",
            ],
            HostName("test-host"): [
                b"<<<check_mk>>>",
                b"source1",
            ],
        },
    )

    piggyback.store_piggyback_raw_data(
        HostName("source2"),
        {
            HostName("test-host2"): [
                b"<<<check_mk>>>",
                b"source2",
            ],
            HostName("test-host"): [
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
        HostName("test-host"): [
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
        HostName("test-host2"): [
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


@pytest.mark.parametrize(
    "time_settings, expected_time_setting_keys",
    [
        ([], {}),
        ([(None, "key", "value")], [(None, "key")]),
        ([("source-host", "key", "value")], [("source-host", "key")]),
        ([("piggybacked-host", "key", "value")], [("piggybacked-host", "key")]),
        ([("~piggybacked-[hH]ost", "key", "value")], [("piggybacked-host", "key")]),
        ([("~PIGGYBACKED-[hH]ost", "key", "value")], []),
    ],
)
def test_get_piggyback_matching_time_settings(
    time_settings: piggyback.PiggybackTimeSettings,
    expected_time_setting_keys: Iterable[tuple[str | None, str]],
) -> None:
    assert sorted(
        piggyback.Config(HostName("piggybacked-host"), time_settings)._expanded_settings.keys()
    ) == sorted(expected_time_setting_keys)
