#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time

import pytest

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.piggyback as piggyback
from cmk.utils.type_defs import HostName

piggyback_max_cachefile_age = 3600


@pytest.fixture(autouse=True)
def test_config():
    piggyback_dir = cmk.utils.paths.piggyback_dir
    host_dir = piggyback_dir / "test-host"
    host_dir.mkdir(parents=True, exist_ok=True)

    for f1 in piggyback_dir.glob("*/*"):
        f1.unlink()

    source_file = piggyback_dir / "test-host" / "source1"
    with source_file.open(mode="wb") as f2:
        f2.write(b"<<<check_mk>>>\nlala\n")

    cmk.utils.paths.piggyback_source_dir.mkdir(parents=True, exist_ok=True)
    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    with source_status_file.open("wb") as f3:
        f3.write(b"")
    source_stat = source_status_file.stat()

    os.utime(str(source_file), (source_stat.st_atime, source_stat.st_mtime))


def test_piggyback_default_time_settings():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]
    piggybacked_hostname = HostName("test-host")
    piggyback.get_piggyback_raw_data(piggybacked_hostname, time_settings)
    piggyback.get_source_and_piggyback_hosts(time_settings)
    piggyback.has_piggyback_raw_data(piggybacked_hostname, time_settings)
    piggyback.cleanup_piggyback_files(time_settings)


def test_cleanup_piggyback_files():
    piggyback.cleanup_piggyback_files([(None, "max_cache_age", -1)])
    assert [
        source_host.name
        for piggybacked_dir in cmk.utils.paths.piggyback_dir.glob("*")
        for source_host in piggybacked_dir.glob("*")
    ] == []
    assert list(cmk.utils.paths.piggyback_source_dir.glob("*")) == []


def test_get_piggyback_raw_data_no_data():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]
    assert piggyback.get_piggyback_raw_data(HostName("no-host"), time_settings) == []


@pytest.mark.parametrize(
    "time_settings",
    [
        [
            (None, "max_cache_age", piggyback_max_cachefile_age),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", piggyback_max_cachefile_age),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", piggyback_max_cachefile_age),
            ("not-source", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("test-host", "max_cache_age", piggyback_max_cachefile_age),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", piggyback_max_cachefile_age),
        ],
        [
            (None, "max_cache_age", -1),
            ("test-host", "max_cache_age", piggyback_max_cachefile_age),
            ("not-test-host", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", piggyback_max_cachefile_age),
            ("not-test-host", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", piggyback_max_cachefile_age),
        ],
        [
            (None, "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", piggyback_max_cachefile_age),
            ("~TEST-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", piggyback_max_cachefile_age),
            ("~TEST-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("test-host", "max_cache_age", piggyback_max_cachefile_age),
            ("~test-[hH]ost", "max_cache_age", -1),
        ],
        [
            (None, "max_cache_age", -1),
            ("source1", "max_cache_age", -1),
            ("~test-[hH]ost", "max_cache_age", piggyback_max_cachefile_age),
            ("test-host", "max_cache_age", -1),
        ],
    ],
)
def test_get_piggyback_raw_data_successful(time_settings):
    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is True
        assert raw_data_info.reason == "Successfully processed from source 'source1'"
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_get_piggyback_raw_data_not_updated():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]

    # Fake age the test-host piggyback file
    os.utime(
        str(cmk.utils.paths.piggyback_dir / "test-host" / "source1"),
        (time.time() - 10, time.time() - 10),
    )

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is False
        assert raw_data_info.reason == "Piggyback file not updated by source 'source1'"
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_get_piggyback_raw_data_not_sending():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]

    source_status_file = cmk.utils.paths.piggyback_source_dir / "source1"
    if source_status_file.exists():
        os.remove(str(source_status_file))

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is False
        assert raw_data_info.reason == "Source 'source1' not sending piggyback data"
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_get_piggyback_raw_data_too_old_global():
    time_settings: piggyback.PiggybackTimeSettings = [(None, "max_cache_age", -1)]

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is False
        assert raw_data_info.reason.startswith("Piggyback file too old:")
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_get_piggyback_raw_data_too_old_source():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age),
        ("source1", "max_cache_age", -1),
    ]

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is False
        assert raw_data_info.reason.startswith("Piggyback file too old:")
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_get_piggyback_raw_data_too_old_piggybacked_host():
    time_settings = [
        (None, "max_cache_age", piggyback_max_cachefile_age),
        ("source1", "max_cache_age", piggyback_max_cachefile_age),
        ("test-host", "max_cache_age", -1),
    ]

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is False
        assert raw_data_info.reason.startswith("Piggyback file too old:")
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


def test_has_piggyback_raw_data_no_data():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]
    assert piggyback.has_piggyback_raw_data(HostName("no-host"), time_settings) is False


def test_has_piggyback_raw_data():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]
    assert piggyback.has_piggyback_raw_data(HostName("test-host"), time_settings) is True


def test_remove_source_status_file_not_existing():
    assert piggyback.remove_source_status_file(HostName("nosource")) is False


def test_remove_source_status_file():
    assert piggyback.remove_source_status_file(HostName("source1")) is True


def test_store_piggyback_raw_data_new_host():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age),
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

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("pig"), time_settings):
        assert raw_data_info.source_hostname == "source2"
        assert raw_data_info.file_path.endswith("/pig/source2")
        assert raw_data_info.successfully_processed is True
        assert raw_data_info.reason.startswith("Successfully processed from source 'source2'")
        assert raw_data_info.reason_status == 0
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_store_piggyback_raw_data_second_source():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age),
    ]

    piggyback.store_piggyback_raw_data(
        HostName("source2"),
        {
            HostName("test-host"): [
                b"<<<check_mk>>>",
                b"lulu",
            ]
        },
    )

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname in ["source1", "source2"]
        if raw_data_info.source_hostname == "source1":
            assert raw_data_info.file_path.endswith("/test-host/source1")
            assert raw_data_info.successfully_processed is True
            assert raw_data_info.reason.startswith("Successfully processed from source 'source1'")
            assert raw_data_info.reason_status == 0
            assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"

        else:  # source2
            assert raw_data_info.file_path.endswith("/test-host/source2")
            assert raw_data_info.successfully_processed is True
            assert raw_data_info.reason.startswith("Successfully processed from source 'source2'")
            assert raw_data_info.reason_status == 0
            assert raw_data_info.raw_data == b"<<<check_mk>>>\nlulu\n"


def test_get_source_and_piggyback_hosts():
    time_settings: piggyback.PiggybackTimeSettings = [
        (None, "max_cache_age", piggyback_max_cachefile_age)
    ]
    cmk.utils.paths.piggyback_source_dir.mkdir(parents=True, exist_ok=True)

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
        (time.time() - 10, time.time() - 10),
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
                (None, "max_cache_age", piggyback_max_cachefile_age),
                ("source1", "validity_period", 1000),
            ],
            True,
            "Source 'source1' not sending piggyback data (still valid",
            0,
        ),
        (
            [
                (None, "max_cache_age", piggyback_max_cachefile_age),
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

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is successfully_processed
        assert raw_data_info.reason.startswith(reason)
        assert raw_data_info.reason_status == reason_status
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", piggyback_max_cachefile_age),
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

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is successfully_processed
        assert raw_data_info.reason == reason
        assert raw_data_info.reason_status == reason_status
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", piggyback_max_cachefile_age),
                ("source1", "validity_period", -1),
                ("test-host", "validity_period", 1000),
            ],
            True,
            "Piggyback file not updated by source 'source1' (still valid",
            0,
        ),
        (
            [
                (None, "max_cache_age", piggyback_max_cachefile_age),
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
        (time.time() - 10, time.time() - 10),
    )

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is successfully_processed
        assert raw_data_info.reason.startswith(reason)
        assert raw_data_info.reason_status == reason_status
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


@pytest.mark.parametrize(
    "time_settings, successfully_processed, reason, reason_status",
    [
        (
            [
                (None, "max_cache_age", piggyback_max_cachefile_age),
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
        (time.time() - 10, time.time() - 10),
    )

    for raw_data_info in piggyback.get_piggyback_raw_data(HostName("test-host"), time_settings):
        assert raw_data_info.source_hostname == "source1"
        assert raw_data_info.file_path.endswith("/test-host/source1")
        assert raw_data_info.successfully_processed is successfully_processed
        assert raw_data_info.reason == reason
        assert raw_data_info.reason_status == reason_status
        assert raw_data_info.raw_data == b"<<<check_mk>>>\nlala\n"


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
