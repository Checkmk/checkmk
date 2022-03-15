#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Iterable

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib import on_time

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.piggyback as piggyback
from cmk.utils.type_defs import HostName

_PIGGYBACK_MAX_CACHEFILE_AGE = 3600

_TEST_HOST_NAME = HostName("test-host")

_PAYLOAD = b"<<<check_mk>>>\nlala\n"

_REF_TIME = 1640000000.0


@pytest.fixture(autouse=True)
def _fixture_setup(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterable[None]:
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

    with on_time(_REF_TIME + 10.0, "UTC"):
        yield


def test_piggyback_default_time_settings() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]
    piggyback.get_piggyback_raw_data(_TEST_HOST_NAME, time_settings)
    piggyback.get_source_and_piggyback_hosts(time_settings)
    piggyback.has_piggyback_raw_data(_TEST_HOST_NAME, time_settings)
    piggyback.cleanup_piggyback_files(time_settings)


def test_cleanup_piggyback_files() -> None:
    piggyback.cleanup_piggyback_files([(None, "max_cache_age", -1)])
    assert not any(
        list(piggybacked_dir.glob("*"))
        for piggybacked_dir in cmk.utils.paths.piggyback_dir.glob("*")
    )
    assert not list(cmk.utils.paths.piggyback_source_dir.glob("*"))


def test_get_piggyback_raw_data_no_data() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]
    assert not piggyback.get_piggyback_raw_data(HostName("no-host"), time_settings)


def _get_only_raw_data_element(
    host_name: HostName,
    time_setting: piggyback.PiggybackTimeSettings,
) -> piggyback.PiggybackRawDataInfo:
    raw_data_sequence = piggyback.get_piggyback_raw_data(host_name, time_setting)
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
def test_get_piggyback_raw_data_successful(time_settings: piggyback.PiggybackTimeSettings) -> None:
    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is True
    assert raw_data.info.message == "Successfully processed from source 'source1'"
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_not_updated() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]

    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / str(_TEST_HOST_NAME) / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is False
    assert raw_data.info.message == "Piggyback file not updated by source 'source1'"
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_not_sending() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]

    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is False
    assert raw_data.info.message == "Source 'source1' not sending piggyback data"
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_too_old_global() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [(None, "max_cache_age", -1)]

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is False
    assert raw_data.info.message.startswith("Piggyback file too old:")
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_too_old_source() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ("source1", "max_cache_age", -1),
    ]

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is False
    assert raw_data.info.message.startswith("Piggyback file too old:")
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_get_piggyback_raw_data_too_old_piggybacked_host() -> None:
    time_settings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ("source1", "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
        ("test-host", "max_cache_age", -1),
    ]

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is False
    assert raw_data.info.message.startswith("Piggyback file too old:")
    assert raw_data.info.status == 0
    assert raw_data.raw_data == _PAYLOAD


def test_has_piggyback_raw_data_no_data() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]
    assert piggyback.has_piggyback_raw_data(HostName("no-host"), time_settings) is False


def test_has_piggyback_raw_data() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]
    assert piggyback.has_piggyback_raw_data(_TEST_HOST_NAME, time_settings) is True


def test_remove_source_status_file_not_existing() -> None:
    assert piggyback.remove_source_status_file(HostName("nosource")) is False


def test_remove_source_status_file():
    assert piggyback.remove_source_status_file(HostName("source1")) is True


def test_store_piggyback_raw_data_new_host() -> None:
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
    ]

    piggyback.store_piggyback_raw_data(
        HostName("source2"),
        {
            HostName("pig"): [
                b"<<<check_mk>>>",
                b"lulu",
            ]
        },
    )

    raw_data = _get_only_raw_data_element(HostName("pig"), time_settings)

    assert raw_data.info.source_hostname == "source2"
    assert raw_data.info.file_path.parts[-2:] == ("pig", "source2")
    assert raw_data.info.successfully_processed is True
    assert raw_data.info.message.startswith("Successfully processed from source 'source2'")
    assert raw_data.info.status == 0
    assert raw_data.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_store_piggyback_raw_data_second_source():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
    ]

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
        rd.info.source_hostname: rd
        for rd in piggyback.get_piggyback_raw_data(_TEST_HOST_NAME, time_settings)
    }
    assert len(raw_data_map) == 2

    raw_data1, raw_data2 = raw_data_map["source1"], raw_data_map["source2"]

    assert raw_data1.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source1")
    assert raw_data1.info.successfully_processed is True
    assert raw_data1.info.message.startswith("Successfully processed from source 'source1'")
    assert raw_data1.info.status == 0
    assert raw_data1.raw_data == _PAYLOAD

    assert raw_data2.info.file_path.parts[-2:] == (str(_TEST_HOST_NAME), "source2")
    assert raw_data2.info.successfully_processed is True
    assert raw_data2.info.message.startswith("Successfully processed from source 'source2'")
    assert raw_data2.info.status == 0
    assert raw_data2.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_get_source_and_piggyback_hosts():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE)
    ]

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

    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    piggyback.store_piggyback_raw_data(
        HostName("source1"),
        {
            HostName("test-host2"): [
                b"<<<check_mk>>>",
                b"source1",
            ]
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

    assert sorted(list(piggyback.get_source_and_piggyback_hosts(time_settings))) == sorted(
        [
            (HostName("source1"), HostName("test-host2")),
            (HostName("source2"), HostName("test-host")),
            (HostName("source2"), HostName("test-host2")),
        ]
    )


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", 1000),
            ],
            True,
            "Source 'source1' not sending piggyback data (still valid",
            0,
        ),
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", 1000),
                ("source1", "validity_state", 1),
            ],
            True,
            "Source 'source1' not sending piggyback data (still valid",
            1,
        ),
    ],
)
def test_get_piggyback_raw_data_source_validity(
    time_settings, successfully_processed, reason, reason_status
):
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is successfully_processed
    assert raw_data.info.message.startswith(reason)
    assert raw_data.info.status == reason_status
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", -1),
            ],
            False,
            "Source 'source1' not sending piggyback data",
            0,
        ),
    ],
)
def test_get_piggyback_raw_data_source_validity2(
    time_settings, successfully_processed, reason, reason_status
):
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is successfully_processed
    assert raw_data.info.message == reason
    assert raw_data.info.status == reason_status
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", -1),
                ("test-host", "validity_period", 1000),
            ],
            True,
            "Piggyback file not updated by source 'source1' (still valid",
            0,
        ),
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", -1),
                ("source1", "validity_state", 2),
                ("test-host", "validity_period", 1000),
                ("test-host", "validity_state", 1),
            ],
            True,
            "Piggyback file not updated by source 'source1' (still valid",
            1,
        ),
    ],
)
def test_get_piggyback_raw_data_piggybacked_host_validity(
    time_settings, successfully_processed, reason, reason_status
):
    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is successfully_processed
    assert raw_data.info.message.startswith(reason)
    assert raw_data.info.status == reason_status
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", _PIGGYBACK_MAX_CACHEFILE_AGE),
                ("source1", "validity_period", 1000),
                ("source1", "validity_state", 2),
                ("test-host", "validity_period", -1),
                ("test-host", "validity_state", 1),
            ],
            False,
            "Piggyback file not updated by source 'source1'",
            0,
        ),
    ],
)
def test_get_piggyback_raw_data_piggybacked_host_validity2(
    time_settings, successfully_processed, reason, reason_status
):
    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
        (_REF_TIME - 10, _REF_TIME - 10),
    )

    raw_data = _get_only_raw_data_element(_TEST_HOST_NAME, time_settings)

    assert raw_data.info.source_hostname == "source1"
    assert raw_data.info.file_path.parts[-2:] == ("test-host", "source1")
    assert raw_data.info.successfully_processed is successfully_processed
    assert raw_data.info.message.startswith(reason)
    assert raw_data.info.status == reason_status
    assert raw_data.raw_data == _PAYLOAD


@pytest.mark.parametrize(
    "time_settings, expected_time_setting_keys",
    [
        ([], {}),
        ([(None, "key", "value")], [(None, "key")]),
        ([("source-host", "key", "value")], [("source-host", "key")]),
        ([("piggybacked-host", "key", "value")], [("piggybacked-host", "key")]),
        ([("~piggybacked-[hH]ost", "key", "value")], [("piggybacked-host", "key")]),
        ([("not-source-host", "key", "value")], []),
        ([("not-piggybacked-host", "key", "value")], []),
        ([("~PIGGYBACKED-[hH]ost", "key", "value")], []),
    ],
)
def test_get_piggyback_matching_time_settings(time_settings, expected_time_setting_keys):
    assert sorted(
        piggyback._get_matching_time_settings(
            [HostName("source-host")], HostName("piggybacked-host"), time_settings
        ).keys()
    ) == sorted(expected_time_setting_keys)
