#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.hr_fs import (
    check_hr_fs_testable,
    discover_hr_fs,
    parse_hr_fs,
    Section,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS


@pytest.fixture(name="section", scope="module")
def section_fixture() -> Section:
    return parse_hr_fs(
        [
            [".1.3.6.1.2.1.25.2.1.2", "Physical memory", "1024", "4029888", "3844692"],
            [".1.3.6.1.2.1.25.2.1.3", "Virtual memory", "1024", "28572340", "5750840"],
            [".1.3.6.1.2.1.25.2.1.1", "Memory buffers", "1024", "4029888", "69616"],
            [".1.3.6.1.2.1.25.2.1.1", "Cached memory", "1024", "1641072", "1641072"],
            [".1.3.6.1.2.1.25.2.1.1", "Shared memory", "1024", "126948", "126948"],
            [".1.3.6.1.2.1.25.2.1.3", "Swap space", "1024", "24542452", "1906148"],
            [".1.3.6.1.2.1.25.2.1.4", "/new_root", "4096", "102400", "77380"],
            [".1.3.6.1.2.1.25.2.1.4", "/proc", "4096", "0", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/dev/pts", "4096", "0", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/sys", "4096", "0", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/tmp", "4096", "16384", "778"],
            [".1.3.6.1.2.1.25.2.1.4", "/dev/shm", "4096", "503736", "39"],
            [".1.3.6.1.2.1.25.2.1.4", "/share", "4096", "4096", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/mnt/boot_config", "4096", "2007", "10"],
            [".1.3.6.1.2.1.25.2.1.4", "/mnt/snapshot/export", "4096", "4096", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/mnt/HDA_ROOT", "4096", "126325", "40055"],
            [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup", "4096", "503736", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup/memory", "4096", "0", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/mnt/pool1", "4096", "564962", "875"],
            [".1.3.6.1.2.1.25.2.1.4", "/share/CACHEDEV1_DATA", "8192", "1415469511", "685296421"],
            [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup/cpu", "4096", "0", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/mnt/ext", "4096", "106746", "104033"],
            [".1.3.6.1.2.1.25.2.1.4", "/samba_third_party", "4096", "8192", "6975"],
            [".1.3.6.1.2.1.25.2.1.4", "/share/.quftp_client", "4096", "256", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/tmp/default_dav_root", "4096", "1", "0"],
            [".1.3.6.1.2.1.25.2.1.4", "/proc/fs/nfsd", "4096", "0", "0"],
            [
                ".1.3.6.1.2.1.25.2.1.4",
                "/lib/modules/5.10.60-qnap/container-station",
                "8192",
                "1415469511",
                "685296421",
            ],
            [".1.3.6.1.2.1.25.2.1.4", "/sys/fs/cgroup/systemd", "4096", "0", "0"],
        ]
    )


def test_discover_hr_fs_do_not_discover() -> None:
    # Some devices don't report hrStorageDescr (SUP-14525)
    section = [("", 1255.21484375, 185.06640625, 0)]
    assert sorted(discover_hr_fs([{"groups": []}], section)) == []


def test_discover_hr_fs(section: Section) -> None:
    assert sorted(discover_hr_fs([{"groups": []}], section)) == [
        Service(item="/dev/shm"),
        Service(item="/lib/modules/5.10.60-qnap/container-station"),
        Service(item="/mnt/HDA_ROOT"),
        Service(item="/mnt/boot_config"),
        Service(item="/mnt/ext"),
        Service(item="/mnt/pool1"),
        Service(item="/mnt/snapshot/export"),
        Service(item="/new_root"),
        Service(item="/samba_third_party"),
        Service(item="/share"),
        Service(item="/share/.quftp_client"),
        Service(item="/share/CACHEDEV1_DATA"),
        Service(item="/sys/fs/cgroup"),
        Service(item="/tmp"),
        Service(item="/tmp/default_dav_root"),
    ]


def test_check_hr_fs(section: Section) -> None:
    value_store: dict[str, object] = {
        "/mnt/pool1.trend": (1676554542.4808888, 1676556884.145195, 0.0),
        "/mnt/pool1.delta": (1676556884.145195, 3.41796875),
    }

    assert list(
        check_hr_fs_testable(
            "/mnt/pool1",
            FILESYSTEM_DEFAULT_PARAMS,
            section,
            value_store,
        )
    ) == [
        Metric(
            "fs_used",
            3.41796875,
            levels=(1765.5062494277954, 1986.1945304870605),
            boundaries=(0.0, 2206.8828125),
        ),
        Metric("fs_free", 2203.46484375, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            0.15487767318863924,
            levels=(79.99999997407181, 89.9999999654291),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 0.15% - 3.42 MiB of 2.16 GiB"),
        Metric("fs_size", 2206.8828125, boundaries=(0.0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
    ]


def test_check_hr_fs_free_levels() -> None:
    value_store: dict[str, object] = {
        "/some/small/fs.delta": (1713882925.0620046, 0.00012969970703125),
        "/some/small/fs.trend": (1713882925.0620046, 1713882925.0620046, 0.0),
    }

    assert list(
        check_hr_fs_testable(
            "/some/small/fs",
            dict(FILESYSTEM_DEFAULT_PARAMS) | {"levels": [(1, (-15.0, -10.0))]},
            [("/some/small/fs", 0.390625, 0.39049530029296875, 0)],
            value_store,
        )
    ) == [
        Metric(
            "fs_used",
            0.00012969970703125,
            levels=(0.33203125, 0.3515625),
            boundaries=(0.0, 0.390625),
        ),
        Metric("fs_free", 0.39049530029296875, boundaries=(0.0, None)),
        Metric("fs_used_percent", 0.033203125, levels=(85.0, 90.0), boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Used: 0.03% - 136 B of 400 KiB"),
        Metric("fs_size", 0.390625, boundaries=(0.0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
    ]
