#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from pytest_mock import MockerFixture

from cmk.utils.type_defs import CheckPluginName

from cmk.base import plugin_contexts
from cmk.base.plugins.agent_based import diskstat
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    IgnoreResultsError,
    Metric,
    Result,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state


def test_parse_diskstat_minimum() -> None:
    assert (
        diskstat.parse_diskstat(
            [
                ["12341241243"],
            ]
        )
        == {}
    )


def test_parse_diskstat_predictive(mocker: MockerFixture) -> None:
    # SUP-5924
    DATA = [
        ["1617784511"],
        [
            "259",
            "0",
            "nvme0n1",
            "131855",
            "42275",
            "8019303",
            "34515",
            "386089",
            "166344",
            "13331634",
            "138121",
            "0",
            "185784",
            "177210",
            "0",
            "0",
            "0",
            "0",
            "41445",
            "4574",
        ],
        [
            "53",
            "0",
            "dm-0",
            "172574",
            "0",
            "7980626",
            "74812",
            "548159",
            "0",
            "12443656",
            "706944",
            "0",
            "189576",
            "781756",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
        ],
        [
            "53",
            "1",
            "dm-1",
            "171320",
            "0",
            "7710074",
            "74172",
            "546564",
            "0",
            "12514416",
            "674352",
            "0",
            "186452",
            "748524",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
        ],
        [
            "53",
            "2",
            "dm-2",
            "194",
            "0",
            "8616",
            "68",
            "0",
            "0",
            "0",
            "0",
            "0",
            "72",
            "68",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
        ],
        ["[dmsetup_info]"],
        ["vme0n1p3_crypt", "253:0"],
        ["buntu--vg-swap_1", "253:2", "ubuntu-vg", "swap_1"],
        ["buntu--vg-root", "253:1", "ubuntu-vg", "root"],
    ]

    PARAMS = {
        "average": 300,
        "latency": (80.0, 160.0),
        "read": {
            "horizon": 90,
            "levels_lower": ("absolute", (2.0, 4.0)),
            "levels_upper": ("relative", (10.0, 20.0)),
            "levels_upper_min": (10.0, 15.0),
            "period": "wday",
        },
        "read_ios": (400.0, 600.0),
        "read_latency": (80.0, 160.0),
        "read_wait": (30.0, 50.0),
        "utilization": (80.0, 90.0),
        "write": (50.0, 100.0),
        "write_ios": (300.0, 400.0),
        "write_latency": (80.0, 160.0),
        "write_wait": (30.0, 50.0),
    }

    mocker.patch(
        "cmk.base.check_api._prediction.get_levels", return_value=(None, (2.1, 4.1, None, None))
    )
    with plugin_contexts.current_host("unittest-hn"), plugin_contexts.current_service(
        CheckPluginName("unittest_sd"),
        "unittest_sd_description",
    ):

        with pytest.raises(IgnoreResultsError):
            list(diskstat.check_diskstat("nvme0n1", PARAMS, diskstat.parse_diskstat(DATA), None))
        DATA[0][0] = "1617784512"
        assert list(
            diskstat.check_diskstat(
                "nvme0n1",
                PARAMS,
                diskstat.parse_diskstat(DATA),
                None,
            )
        ) == [
            Result(state=state.OK, notice="All values averaged over 5 minutes 0 seconds"),
            Result(state=state.OK, notice="Utilization: 0%"),
            Metric("disk_utilization", 0.0, levels=(0.8, 0.9)),
            Result(state=state.OK, summary="Read: 0.00 B/s (no reference for prediction yet)"),
            Metric("disk_read_throughput", 0.0, levels=(2.1, 4.1)),  # fake levels are quite low
            Result(state=state.OK, summary="Write: 0.00 B/s"),
            Metric("disk_write_throughput", 0.0, levels=(50000000.0, 100000000.0)),
            Result(state=state.OK, notice="Average wait: 0 seconds"),
            Metric("disk_average_wait", 0.0),
            Result(state=state.OK, notice="Average read wait: 0 seconds"),
            Metric("disk_average_read_wait", 0.0, levels=(0.03, 0.05)),
            Result(state=state.OK, notice="Average write wait: 0 seconds"),
            Metric("disk_average_write_wait", 0.0, levels=(0.03, 0.05)),
            Result(state=state.OK, notice="Average queue length: 0.00"),
            Metric("disk_queue_length", 0.0),
            Result(state=state.OK, notice="Read operations: 0.00/s"),
            Metric("disk_read_ios", 0.0, levels=(400.0, 600.0)),
            Result(state=state.OK, notice="Write operations: 0.00/s"),
            Metric("disk_write_ios", 0.0, levels=(300.0, 400.0)),
            Result(state=state.OK, summary="Latency: 0 seconds"),
            Metric("disk_latency", 0.0, levels=(0.08, 0.16)),
            Metric("disk_average_read_request_size", 0.0),
            Metric("disk_average_request_size", 0.0),
            Metric("disk_average_write_request_size", 0.0),
        ]


def test_parse_diskstat_simple() -> None:
    assert diskstat.parse_diskstat(
        [
            ["1439297971"],
            [
                "8",
                "0",
                "sda",
                "83421",
                "32310",
                "3426701",
                "108964",
                "24516",
                "35933",
                "639474",
                "32372",
                "0",
                "18532",
                "141496",
            ],
            ["8", "16", "sdb", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0"],
            ["[dmsetup_info]"],
            ["No", "devices", "found"],
        ]
    ) == {
        "sda": {
            "timestamp": 1439297971,
            "read_ticks": 108.964,
            "write_ticks": 32.372,
            "read_ios": 83421,
            "write_ios": 24516,
            "read_throughput": 1754470912,
            "write_throughput": 327410688,
            "utilization": 18.532,
            "queue_length": 0,
        },
        "sdb": {
            "timestamp": 1439297971,
            "read_ticks": 0.0,
            "write_ticks": 0.0,
            "read_ios": 0,
            "write_ios": 0,
            "read_throughput": 0,
            "write_throughput": 0,
            "utilization": 0.0,
            "queue_length": 0,
        },
    }


def test_parse_diskstat_dmsetup() -> None:
    assert diskstat.parse_diskstat(
        [
            ["1596025224"],
            [
                "259",
                "0",
                "nvme0n1",
                "1497491",
                "455400",
                "113361605",
                "1143198",
                "773329",
                "599538",
                "37988658",
                "1395234",
                "0",
                "604316",
                "1097280",
                "0",
                "0",
                "0",
                "0",
            ],
            [
                "253",
                "0",
                "dm-0",
                "1951297",
                "0",
                "113329354",
                "2084064",
                "1339672",
                "0",
                "37988424",
                "12603352",
                "0",
                "608364",
                "14687416",
                "0",
                "0",
                "0",
                "0",
            ],
            [
                "253",
                "1",
                "dm-1",
                "1876633",
                "0",
                "112723490",
                "2074720",
                "1025893",
                "0",
                "35617992",
                "7615504",
                "0",
                "587960",
                "9690224",
                "0",
                "0",
                "0",
                "0",
            ],
            [
                "253",
                "2",
                "dm-2",
                "74620",
                "0",
                "604024",
                "12548",
                "309840",
                "0",
                "2478720",
                "4781108",
                "0",
                "23492",
                "4793656",
                "0",
                "0",
                "0",
                "0",
            ],
            ["[dmsetup_info]"],
            ["nvme0n1p3_crypt", "253:0"],
            ["ubuntu--vg-swap_1", "253:2", "ubuntu-vg", "swap_1"],
            ["ubuntu--vg-root", "253:1", "ubuntu-vg", "root"],
        ]
    ) == {
        "nvme0n1": {
            "timestamp": 1596025224,
            "read_ticks": 1143.198,
            "write_ticks": 1395.234,
            "read_ios": 1497491,
            "write_ios": 773329,
            "read_throughput": 58041141760,
            "write_throughput": 19450192896,
            "utilization": 604.316,
            "queue_length": 0,
        },
        "DM nvme0n1p3_crypt": {
            "timestamp": 1596025224,
            "read_ticks": 2084.064,
            "write_ticks": 12603.352,
            "read_ios": 1951297,
            "write_ios": 1339672,
            "read_throughput": 58024629248,
            "write_throughput": 19450073088,
            "utilization": 608.364,
            "queue_length": 0,
        },
        "LVM ubuntu--vg-root": {
            "timestamp": 1596025224,
            "read_ticks": 2074.72,
            "write_ticks": 7615.504,
            "read_ios": 1876633,
            "write_ios": 1025893,
            "read_throughput": 57714426880,
            "write_throughput": 18236411904,
            "utilization": 587.96,
            "queue_length": 0,
        },
        "LVM ubuntu--vg-swap_1": {
            "timestamp": 1596025224,
            "read_ticks": 12.548,
            "write_ticks": 4781.108,
            "read_ios": 74620,
            "write_ios": 309840,
            "read_throughput": 309260288,
            "write_throughput": 1269104640,
            "utilization": 23.492,
            "queue_length": 0,
        },
    }


def test_parse_diskstat_vx_dsk() -> None:
    assert diskstat.parse_diskstat(
        [
            ["1439883623"],
            [
                "253",
                "0",
                "dm-0",
                "5888172",
                "0",
                "49638154",
                "234782",
                "19476903",
                "0",
                "155815224",
                "13469572",
                "0",
                "5663303",
                "13713680",
            ],
            [
                "253",
                "1",
                "dm-1",
                "5851194",
                "0",
                "46809552",
                "154378",
                "0",
                "0",
                "0",
                "0",
                "0",
                "154404",
                "154405",
            ],
            [
                "65",
                "192",
                "sdac",
                "1677718",
                "2543608",
                "8858709",
                "200958",
                "4217589",
                "28",
                "251814166",
                "1133920",
                "0",
                "1059518",
                "1333205",
            ],
            [
                "253",
                "2",
                "dm-2",
                "5857900",
                "0",
                "47115410",
                "183023",
                "560857145",
                "0",
                "4486857160",
                "81720481",
                "0",
                "18413486",
                "81960804",
            ],
            [
                "253",
                "3",
                "dm-3",
                "5851198",
                "0",
                "46809578",
                "162306",
                "12883365",
                "0",
                "103066920",
                "25366952",
                "0",
                "910764",
                "25529266",
            ],
            [
                "199",
                "3000",
                "VxVM3000",
                "595084",
                "173",
                "8680186",
                "174091",
                "72847857",
                "500306960",
                "4585269136",
                "212664111",
                "0",
                "80648985",
                "212785322",
            ],
            [
                "199",
                "7000",
                "VxVM7000",
                "479267",
                "152",
                "4033890",
                "103249",
                "12690313",
                "92841124",
                "844251992",
                "28260756",
                "0",
                "26058778",
                "28358884",
            ],
            [
                "199",
                "8000",
                "VxVM8000",
                "543077",
                "291",
                "37131250",
                "274160",
                "19336020",
                "281685620",
                "2408182752",
                "155722978",
                "0",
                "30286244",
                "155989384",
            ],
            [
                "66",
                "160",
                "sdaq",
                "239411",
                "559267",
                "1921823",
                "131489",
                "1710651",
                "286",
                "119899732",
                "1040265",
                "0",
                "509307",
                "1171318",
            ],
            [
                "199",
                "11000",
                "VxVM11000",
                "209312",
                "96",
                "1747658",
                "48511",
                "6223668",
                "52087993",
                "466495304",
                "16982595",
                "0",
                "10872733",
                "17028919",
            ],
            [
                "199",
                "28000",
                "VxVM28000",
                "971",
                "7834",
                "70442",
                "4614",
                "4142",
                "407556",
                "3293584",
                "26623",
                "0",
                "9388",
                "31237",
            ],
            ["[dmsetup_info]"],
            ["VGlocal-LVvar", "253:2", "VGlocal", "LVvar"],
            ["VGlocal-LVswap", "253:1", "VGlocal", "LVswap"],
            ["VGlocal-LVroot", "253:0", "VGlocal", "LVroot"],
            ["VGlocal-LVtmp", "253:3", "VGlocal", "LVtmp"],
            ["[vx_dsk]"],
            ["c7", "bb8", "/dev/vx/dsk/db01dg/db01vol"],
            ["c7", "1f40", "/dev/vx/dsk/db02dg/db02vol"],
            ["c7", "1b58", "/dev/vx/dsk/db03dg/db03vol"],
            ["c7", "6d60", "/dev/vx/dsk/db04dg/db04vol"],
            ["c7", "2af8", "/dev/vx/dsk/db05dg/db05vol"],
        ]
    ) == {
        "LVM VGlocal-LVroot": {
            "timestamp": 1439883623,
            "read_ticks": 234.782,
            "write_ticks": 13469.572,
            "read_ios": 5888172,
            "write_ios": 19476903,
            "read_throughput": 25414734848,
            "write_throughput": 79777394688,
            "utilization": 5663.303,
            "queue_length": 0,
        },
        "LVM VGlocal-LVswap": {
            "timestamp": 1439883623,
            "read_ticks": 154.378,
            "write_ticks": 0.0,
            "read_ios": 5851194,
            "write_ios": 0,
            "read_throughput": 23966490624,
            "write_throughput": 0,
            "utilization": 154.404,
            "queue_length": 0,
        },
        "sdac": {
            "timestamp": 1439883623,
            "read_ticks": 200.958,
            "write_ticks": 1133.92,
            "read_ios": 1677718,
            "write_ios": 4217589,
            "read_throughput": 4535659008,
            "write_throughput": 128928852992,
            "utilization": 1059.518,
            "queue_length": 0,
        },
        "LVM VGlocal-LVvar": {
            "timestamp": 1439883623,
            "read_ticks": 183.023,
            "write_ticks": 81720.481,
            "read_ios": 5857900,
            "write_ios": 560857145,
            "read_throughput": 24123089920,
            "write_throughput": 2297270865920,
            "utilization": 18413.486,
            "queue_length": 0,
        },
        "LVM VGlocal-LVtmp": {
            "timestamp": 1439883623,
            "read_ticks": 162.306,
            "write_ticks": 25366.952,
            "read_ios": 5851198,
            "write_ios": 12883365,
            "read_throughput": 23966503936,
            "write_throughput": 52770263040,
            "utilization": 910.764,
            "queue_length": 0,
        },
        "VxVM db01dg-db01vol": {
            "timestamp": 1439883623,
            "read_ticks": 174.091,
            "write_ticks": 212664.111,
            "read_ios": 595084,
            "write_ios": 72847857,
            "read_throughput": 4444255232,
            "write_throughput": 2347657797632,
            "utilization": 80648.985,
            "queue_length": 0,
        },
        "VxVM db03dg-db03vol": {
            "timestamp": 1439883623,
            "read_ticks": 103.249,
            "write_ticks": 28260.756,
            "read_ios": 479267,
            "write_ios": 12690313,
            "read_throughput": 2065351680,
            "write_throughput": 432257019904,
            "utilization": 26058.778,
            "queue_length": 0,
        },
        "VxVM db02dg-db02vol": {
            "timestamp": 1439883623,
            "read_ticks": 274.16,
            "write_ticks": 155722.978,
            "read_ios": 543077,
            "write_ios": 19336020,
            "read_throughput": 19011200000,
            "write_throughput": 1232989569024,
            "utilization": 30286.244,
            "queue_length": 0,
        },
        "sdaq": {
            "timestamp": 1439883623,
            "read_ticks": 131.489,
            "write_ticks": 1040.265,
            "read_ios": 239411,
            "write_ios": 1710651,
            "read_throughput": 983973376,
            "write_throughput": 61388662784,
            "utilization": 509.307,
            "queue_length": 0,
        },
        "VxVM db05dg-db05vol": {
            "timestamp": 1439883623,
            "read_ticks": 48.511,
            "write_ticks": 16982.595,
            "read_ios": 209312,
            "write_ios": 6223668,
            "read_throughput": 894800896,
            "write_throughput": 238845595648,
            "utilization": 10872.733,
            "queue_length": 0,
        },
        "VxVM db04dg-db04vol": {
            "timestamp": 1439883623,
            "read_ticks": 4.614,
            "write_ticks": 26.623,
            "read_ios": 971,
            "write_ios": 4142,
            "read_throughput": 36066304,
            "write_throughput": 1686315008,
            "utilization": 9.388,
            "queue_length": 0,
        },
    }


def test_diskstat_convert_info() -> None:
    section_diskstat = {
        "cciss/c0d0": {
            "timestamp": 1409133356,
            "read_ticks": 901.512,
            "write_ticks": 4073930.388,
            "read_ios": 125400,
            "write_ios": 1079896095,
            "read_throughput": 1275086848,
            "write_throughput": 5993542580224,
            "utilization": 69379.184,
            "queue_length": 0,
        },
        "LVM system-root": {
            "timestamp": 1409133356,
            "read_ticks": 892.232,
            "write_ticks": 1846226.648,
            "read_ios": 115663,
            "write_ios": 1462420653,
            "read_throughput": 1170125824,
            "write_throughput": 5990074994688,
            "utilization": 69226.548,
            "queue_length": 0,
        },
        "LVM system-swap": {
            "timestamp": 1409133356,
            "read_ticks": 19.9,
            "write_ticks": 67.868,
            "read_ios": 8140,
            "write_ios": 14068,
            "read_throughput": 33341440,
            "write_throughput": 57622528,
            "utilization": 5.824,
            "queue_length": 0,
        },
        "DM mpath13": {
            "timestamp": 1409133356,
            "read_ticks": 2.436,
            "write_ticks": 0.0,
            "read_ios": 1114,
            "write_ios": 0,
            "read_throughput": 4820992,
            "write_throughput": 0,
            "utilization": 2.428,
            "queue_length": 0,
        },
        "DM mpath15": {
            "timestamp": 1409133356,
            "read_ticks": 1.892,
            "write_ticks": 0.0,
            "read_ios": 1114,
            "write_ios": 0,
            "read_throughput": 4820992,
            "write_throughput": 0,
            "utilization": 1.884,
            "queue_length": 0,
        },
        "DM mpath14": {
            "timestamp": 1409133356,
            "read_ticks": 10082.612,
            "write_ticks": 1742912.4,
            "read_ios": 2048843,
            "write_ios": 202656149,
            "read_throughput": 90293874688,
            "write_throughput": 1600380375040,
            "utilization": 99769.308,
            "queue_length": 0,
        },
        "DM mpath16": {
            "timestamp": 1409133356,
            "read_ticks": 12853.872,
            "write_ticks": 1671595.44,
            "read_ios": 2915671,
            "write_ios": 368558876,
            "read_throughput": 106471072768,
            "write_throughput": 10528268193792,
            "utilization": 503331.176,
            "queue_length": 0,
        },
        "DM mpath12": {
            "timestamp": 1409133356,
            "read_ticks": 1493.216,
            "write_ticks": 1751473.56,
            "read_ios": 593318,
            "write_ios": 681004243,
            "read_throughput": 19158647808,
            "write_throughput": 21510421164032,
            "utilization": 1133126.844,
            "queue_length": 1,
        },
        "LVM system-varlog": {
            "timestamp": 1409133356,
            "read_ticks": 8.568,
            "write_ticks": 4015.592,
            "read_ios": 3980,
            "write_ios": 828430,
            "read_throughput": 36975616,
            "write_throughput": 3393249280,
            "utilization": 2046.96,
            "queue_length": 0,
        },
        "sdaaa": {
            "timestamp": 1409133356,
            "read_ticks": 1.44,
            "write_ticks": 0.0,
            "read_ios": 434,
            "write_ios": 0,
            "read_throughput": 1863680,
            "write_throughput": 0,
            "utilization": 1.44,
            "queue_length": 0,
        },
        "sdb": {
            "timestamp": 1409133356,
            "read_ticks": 1.244,
            "write_ticks": 0.0,
            "read_ios": 434,
            "write_ios": 0,
            "read_throughput": 1863680,
            "write_throughput": 0,
            "utilization": 1.244,
            "queue_length": 0,
        },
        "sdc": {
            "timestamp": 1409133356,
            "read_ticks": 2674.232,
            "write_ticks": 222881.076,
            "read_ios": 391664,
            "write_ios": 124759625,
            "read_throughput": 4504944640,
            "write_throughput": 973232500736,
            "utilization": 58008.712,
            "queue_length": 0,
        },
        "sdd": {
            "timestamp": 1409133356,
            "read_ticks": 3811.452,
            "write_ticks": 555108.148,
            "read_ios": 1126218,
            "write_ios": 246253123,
            "read_throughput": 23959610368,
            "write_throughput": 8094497849344,
            "utilization": 329254.888,
            "queue_length": 0,
        },
        "sde": {
            "timestamp": 1409133356,
            "read_ticks": 808.304,
            "write_ticks": 1032964.44,
            "read_ios": 365813,
            "write_ios": 464498715,
            "read_throughput": 9453720576,
            "write_throughput": 16365300596736,
            "utilization": 745503.484,
            "queue_length": 1,
        },
        "LVM mysql07-root": {
            "timestamp": 1409133356,
            "read_ticks": 50.36,
            "write_ticks": 3965588.936,
            "read_ios": 9325,
            "write_ios": 1064771349,
            "read_throughput": 205435904,
            "write_throughput": 4358962614272,
            "utilization": 86222.472,
            "queue_length": 0,
        },
        "LVM mysql07-data": {
            "timestamp": 1409133356,
            "read_ticks": 314.828,
            "write_ticks": 404242.68,
            "read_ios": 73370,
            "write_ios": 172356607,
            "read_throughput": 2218411008,
            "write_throughput": 680170520576,
            "utilization": 129437.816,
            "queue_length": 2,
        },
        "LVM mysql06-root": {
            "timestamp": 1409133356,
            "read_ticks": 49.088,
            "write_ticks": 1099798.292,
            "read_ios": 8677,
            "write_ios": 18299867,
            "read_throughput": 188589056,
            "write_throughput": 74956255232,
            "utilization": 7133.66,
            "queue_length": 0,
        },
        "LVM mysql06-data": {
            "timestamp": 1409133356,
            "read_ticks": 2512.724,
            "write_ticks": 3197155.008,
            "read_ios": 591198,
            "write_ios": 586722600,
            "read_throughput": 6654764032,
            "write_throughput": 2403215769600,
            "utilization": 101162.948,
            "queue_length": 0,
        },
        "LVM mysql05-root": {
            "timestamp": 1409133356,
            "read_ticks": 34.16,
            "write_ticks": 24749.504,
            "read_ios": 8175,
            "write_ios": 2129040,
            "read_throughput": 183297024,
            "write_throughput": 8720547840,
            "utilization": 1148.668,
            "queue_length": 0,
        },
        "LVM mysql05-data": {
            "timestamp": 1409133356,
            "read_ticks": 1268.176,
            "write_ticks": 1858563.892,
            "read_ios": 185863,
            "write_ios": 32671643,
            "read_throughput": 2171491328,
            "write_throughput": 134263599104,
            "utilization": 13810.156,
            "queue_length": 0,
        },
        "sdf": {
            "timestamp": 1409133356,
            "read_ticks": 0.508,
            "write_ticks": 0.0,
            "read_ios": 13,
            "write_ios": 0,
            "read_throughput": 53248,
            "write_throughput": 0,
            "utilization": 0.508,
            "queue_length": 0,
        },
        "sdg": {
            "timestamp": 1409133356,
            "read_ticks": 1.352,
            "write_ticks": 0.0,
            "read_ios": 13,
            "write_ios": 0,
            "read_throughput": 53248,
            "write_throughput": 0,
            "utilization": 1.352,
            "queue_length": 0,
        },
        "sdh": {
            "timestamp": 1409133356,
            "read_ticks": 0.504,
            "write_ticks": 0.0,
            "read_ios": 13,
            "write_ios": 0,
            "read_throughput": 53248,
            "write_throughput": 0,
            "utilization": 0.504,
            "queue_length": 0,
        },
        "sdi": {
            "timestamp": 1409133356,
            "read_ticks": 0.34,
            "write_ticks": 0.0,
            "read_ios": 13,
            "write_ios": 0,
            "read_throughput": 53248,
            "write_throughput": 0,
            "utilization": 0.34,
            "queue_length": 0,
        },
        "sdj": {
            "timestamp": 1409133356,
            "read_ticks": 0.372,
            "write_ticks": 0.0,
            "read_ios": 13,
            "write_ios": 0,
            "read_throughput": 53248,
            "write_throughput": 0,
            "utilization": 0.372,
            "queue_length": 0,
        },
    }
    section_multipath = {
        "SDataCoreSANsymphony_VVol735": {
            "paths": ["sdi", "sdd"],
            "broken_paths": [],
            "luns": ["4:0:4:3(sdi)", "0:0:4:3(sdd)"],
            "uuid": "SDataCoreSANsymphony_VVol735",
            "state": "prio=-1status=active",
            "numpaths": 2,
            "device": "dm-5",
            "alias": "mpath16",
        },
        "SDataCoreSANsymphony_VVol733": {
            "paths": ["sdb", "sdg"],
            "broken_paths": [],
            "luns": ["0:0:4:1(sdb)", "4:0:4:1(sdg)"],
            "uuid": "SDataCoreSANsymphony_VVol733",
            "state": "prio=-1status=enabled",
            "numpaths": 2,
            "device": "dm-3",
            "alias": "mpath15",
        },
        "SDataCoreSANsymphony_VVol734": {
            "paths": ["sdc", "sdh"],
            "broken_paths": [],
            "luns": ["0:0:4:2(sdc)", "4:0:4:2(sdh)"],
            "uuid": "SDataCoreSANsymphony_VVol734",
            "state": "prio=-1status=enabled",
            "numpaths": 2,
            "device": "dm-4",
            "alias": "mpath14",
        },
        "SDataCoreSANsymphony_VVol732": {
            "paths": ["sda", "sdf"],
            "broken_paths": [],
            "luns": ["0:0:4:0(sda)", "4:0:4:0(sdf)"],
            "uuid": "SDataCoreSANsymphony_VVol732",
            "state": "prio=-1status=enabled",
            "numpaths": 2,
            "device": "dm-2",
            "alias": "mpath13",
        },
        "SDataCoreSANsymphony_VVol795": {
            "paths": ["sdj", "sde"],
            "broken_paths": [],
            "luns": ["4:0:4:4(sdj)", "0:0:4:4(sde)"],
            "uuid": "SDataCoreSANsymphony_VVol795",
            "state": "prio=-1status=active",
            "numpaths": 2,
            "device": "dm-6",
            "alias": "mpath12",
        },
    }
    converted_section = {
        "cciss/c0d0": {
            "timestamp": 1409133356,
            "read_ticks": 901.512,
            "write_ticks": 4073930.388,
            "read_ios": 125400,
            "write_ios": 1079896095,
            "read_throughput": 1275086848,
            "write_throughput": 5993542580224,
            "utilization": 69379.184,
            "queue_length": 0,
        },
        "LVM system-root": {
            "timestamp": 1409133356,
            "read_ticks": 892.232,
            "write_ticks": 1846226.648,
            "read_ios": 115663,
            "write_ios": 1462420653,
            "read_throughput": 1170125824,
            "write_throughput": 5990074994688,
            "utilization": 69226.548,
            "queue_length": 0,
        },
        "LVM system-swap": {
            "timestamp": 1409133356,
            "read_ticks": 19.9,
            "write_ticks": 67.868,
            "read_ios": 8140,
            "write_ios": 14068,
            "read_throughput": 33341440,
            "write_throughput": 57622528,
            "utilization": 5.824,
            "queue_length": 0,
        },
        "LVM system-varlog": {
            "timestamp": 1409133356,
            "read_ticks": 8.568,
            "write_ticks": 4015.592,
            "read_ios": 3980,
            "write_ios": 828430,
            "read_throughput": 36975616,
            "write_throughput": 3393249280,
            "utilization": 2046.96,
            "queue_length": 0,
        },
        "sdaaa": {
            "timestamp": 1409133356,
            "read_ticks": 1.44,
            "write_ticks": 0.0,
            "read_ios": 434,
            "write_ios": 0,
            "read_throughput": 1863680,
            "write_throughput": 0,
            "utilization": 1.44,
            "queue_length": 0,
        },
        "LVM mysql07-root": {
            "timestamp": 1409133356,
            "read_ticks": 50.36,
            "write_ticks": 3965588.936,
            "read_ios": 9325,
            "write_ios": 1064771349,
            "read_throughput": 205435904,
            "write_throughput": 4358962614272,
            "utilization": 86222.472,
            "queue_length": 0,
        },
        "LVM mysql07-data": {
            "timestamp": 1409133356,
            "read_ticks": 314.828,
            "write_ticks": 404242.68,
            "read_ios": 73370,
            "write_ios": 172356607,
            "read_throughput": 2218411008,
            "write_throughput": 680170520576,
            "utilization": 129437.816,
            "queue_length": 2,
        },
        "LVM mysql06-root": {
            "timestamp": 1409133356,
            "read_ticks": 49.088,
            "write_ticks": 1099798.292,
            "read_ios": 8677,
            "write_ios": 18299867,
            "read_throughput": 188589056,
            "write_throughput": 74956255232,
            "utilization": 7133.66,
            "queue_length": 0,
        },
        "LVM mysql06-data": {
            "timestamp": 1409133356,
            "read_ticks": 2512.724,
            "write_ticks": 3197155.008,
            "read_ios": 591198,
            "write_ios": 586722600,
            "read_throughput": 6654764032,
            "write_throughput": 2403215769600,
            "utilization": 101162.948,
            "queue_length": 0,
        },
        "LVM mysql05-root": {
            "timestamp": 1409133356,
            "read_ticks": 34.16,
            "write_ticks": 24749.504,
            "read_ios": 8175,
            "write_ios": 2129040,
            "read_throughput": 183297024,
            "write_throughput": 8720547840,
            "utilization": 1148.668,
            "queue_length": 0,
        },
        "LVM mysql05-data": {
            "timestamp": 1409133356,
            "read_ticks": 1268.176,
            "write_ticks": 1858563.892,
            "read_ios": 185863,
            "write_ios": 32671643,
            "read_throughput": 2171491328,
            "write_throughput": 134263599104,
            "utilization": 13810.156,
            "queue_length": 0,
        },
        "SDataCoreSANsymphony_VVol735": {
            "timestamp": 1409133356,
            "read_ticks": 12853.872,
            "write_ticks": 1671595.44,
            "read_ios": 2915671,
            "write_ios": 368558876,
            "read_throughput": 106471072768,
            "write_throughput": 10528268193792,
            "utilization": 503331.176,
            "queue_length": 0,
        },
        "SDataCoreSANsymphony_VVol733": {
            "timestamp": 1409133356,
            "read_ticks": 1.892,
            "write_ticks": 0.0,
            "read_ios": 1114,
            "write_ios": 0,
            "read_throughput": 4820992,
            "write_throughput": 0,
            "utilization": 1.884,
            "queue_length": 0,
        },
        "SDataCoreSANsymphony_VVol734": {
            "timestamp": 1409133356,
            "read_ticks": 10082.612,
            "write_ticks": 1742912.4,
            "read_ios": 2048843,
            "write_ios": 202656149,
            "read_throughput": 90293874688,
            "write_throughput": 1600380375040,
            "utilization": 99769.308,
            "queue_length": 0,
        },
        "SDataCoreSANsymphony_VVol732": {
            "timestamp": 1409133356,
            "read_ticks": 2.436,
            "write_ticks": 0.0,
            "read_ios": 1114,
            "write_ios": 0,
            "read_throughput": 4820992,
            "write_throughput": 0,
            "utilization": 2.428,
            "queue_length": 0,
        },
        "SDataCoreSANsymphony_VVol795": {
            "timestamp": 1409133356,
            "read_ticks": 1493.216,
            "write_ticks": 1751473.56,
            "read_ios": 593318,
            "write_ios": 681004243,
            "read_throughput": 19158647808,
            "write_throughput": 21510421164032,
            "utilization": 1133126.844,
            "queue_length": 1,
        },
    }

    section_diskstat_reference = section_diskstat.copy()

    assert (
        diskstat.diskstat_convert_info(
            {},
            section_multipath,
        )
        == {}
    )

    assert (
        diskstat.diskstat_convert_info(
            section_diskstat,
            None,
        )
        == diskstat.diskstat_convert_info(
            section_diskstat,
            {},
        )
        == section_diskstat
    )
    # check if input section is modified
    assert section_diskstat == section_diskstat_reference

    assert (
        diskstat.diskstat_convert_info(
            section_diskstat,
            section_multipath,
        )
        == converted_section
    )
    assert section_diskstat == section_diskstat_reference


DISK = {
    "timestamp": 1439883623,
    "read_ticks": 234.782,
    "write_ticks": 13469.572,
    "read_ios": 5888172,
    "write_ios": 19476903,
    "read_throughput": 25414734848,
    "write_throughput": 79777394688,
    "utilization": 5663.303,
    "queue_length": 10,
}
DISK_HALF = {k: v / 2 for k, v in DISK.items()}

EXP_METRICS = {
    "queue_length",
    "read_ios",
    "write_ios",
    "read_throughput",
    "write_throughput",
    "utilization",
    "latency",
    "average_wait",
    "average_request_size",
    "average_read_wait",
    "average_read_request_size",
    "average_write_wait",
    "average_write_request_size",
}


def test_compute_rates_single_disk_same_time_same_values() -> None:
    # same timestamp twice --> IgnoreResultsError twice
    with pytest.raises(IgnoreResultsError):
        diskstat._compute_rates_single_disk(
            DISK,
            get_value_store(),
        )
    with pytest.raises(IgnoreResultsError):
        diskstat._compute_rates_single_disk(
            DISK,
            get_value_store(),
        )


def test_compute_rates_single_disk_diff_time_same_values() -> None:
    # different timestamps --> IgnoreResults once
    with pytest.raises(IgnoreResultsError):
        diskstat._compute_rates_single_disk(
            DISK,
            get_value_store(),
        )
    disk_w_rates = diskstat._compute_rates_single_disk(
        {
            **DISK,
            "timestamp": DISK["timestamp"] + 100,
        },
        get_value_store(),
    )
    assert disk_w_rates == {
        **{metric: 0 for metric in EXP_METRICS},
        "queue_length": DISK["queue_length"],
    }


def test_compute_rates_single_disk_diff_time_diff_values() -> None:
    # different timestamps --> IgnoreResults once
    with pytest.raises(IgnoreResultsError):
        diskstat._compute_rates_single_disk(
            DISK_HALF,
            get_value_store(),
        )
    disk_w_rates = diskstat._compute_rates_single_disk(
        DISK,
        get_value_store(),
    )
    assert set(disk_w_rates) == EXP_METRICS
    for k, v in disk_w_rates.items():
        if k == "queue_length":
            assert v == DISK["queue_length"]
        else:
            assert v > 0


def test_check_diskstat_single_item() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "item",
                {},
                {"item": DISK_HALF},
                None,
            )
        )
    assert list(diskstat.check_diskstat("item", {}, {"item": DISK}, None,)) == [
        Result(state=state.OK, notice="Utilization: <0.01%"),
        Metric("disk_utilization", 3.933167173747347e-06),
        Result(state=state.OK, summary="Read: 17.7 B/s"),
        Metric("disk_read_throughput", 17.650547892925093),
        Result(state=state.OK, summary="Write: 55.4 B/s"),
        Metric("disk_write_throughput", 55.40544625529087),
        Result(state=state.OK, notice="Average wait: 540 microseconds"),
        Metric("disk_average_wait", 0.0005402843870952481),
        Result(state=state.OK, notice="Average read wait: 40 microseconds"),
        Metric("disk_average_read_wait", 3.987349554326878e-05),
        Result(state=state.OK, notice="Average write wait: 692 microseconds"),
        Metric("disk_average_write_wait", 0.0006915664158721743),
        Result(state=state.OK, notice="Average queue length: 10.00"),
        Metric("disk_queue_length", 10.0),
        Result(state=state.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.004089338822905689),
        Result(state=state.OK, notice="Write operations: 0.01/s"),
        Metric("disk_write_ios", 0.013526720277170622),
        Result(state=state.OK, summary="Latency: 223 microseconds"),
        Metric("disk_latency", 0.00022327168360432604),
        Metric("disk_average_read_request_size", 4316.235131718299),
        Metric("disk_average_request_size", 4147.124719166019),
        Metric("disk_average_write_request_size", 4096.0),
    ]


def test_check_diskstat_summary() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "SUMMARY",
                {},
                {
                    "disk1": DISK_HALF,
                    "disk2": DISK_HALF,
                },
                {},
            )
        )
    results_summary = list(
        diskstat.check_diskstat(
            "SUMMARY",
            {},
            {
                "disk1": DISK,
                "disk2": DISK,
            },
            None,
        )
    )
    assert results_summary == [
        Result(state=state.OK, notice="Utilization: <0.01%"),
        Metric("disk_utilization", 3.933167173747347e-06),
        Result(state=state.OK, summary="Read: 35.3 B/s"),
        Metric("disk_read_throughput", 35.30109578585019),
        Result(state=state.OK, summary="Write: 111 B/s"),
        Metric("disk_write_throughput", 110.81089251058174),
        Result(state=state.OK, notice="Average wait: 540 microseconds"),
        Metric("disk_average_wait", 0.0005402843870952481),
        Result(state=state.OK, notice="Average read wait: 40 microseconds"),
        Metric("disk_average_read_wait", 3.987349554326878e-05),
        Result(state=state.OK, notice="Average write wait: 692 microseconds"),
        Metric("disk_average_write_wait", 0.0006915664158721743),
        Result(state=state.OK, notice="Average queue length: 10.00"),
        Metric("disk_queue_length", 10.0),
        Result(state=state.OK, notice="Read operations: 0.01/s"),
        Metric("disk_read_ios", 0.008178677645811379),
        Result(state=state.OK, notice="Write operations: 0.03/s"),
        Metric("disk_write_ios", 0.027053440554341245),
        Result(state=state.OK, summary="Latency: 223 microseconds"),
        Metric("disk_latency", 0.00022327168360432604),
        Metric("disk_average_read_request_size", 4316.235131718299),
        Metric("disk_average_request_size", 4147.124719166019),
        Metric("disk_average_write_request_size", 4096.0),
    ]

    # compare against single-item output
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "disk1",
                {},
                {
                    "disk1": DISK_HALF,
                    "disk2": DISK_HALF,
                },
                None,
            )
        )
    results_single_disk = list(
        diskstat.check_diskstat(
            "disk1",
            {},
            {
                "disk1": DISK,
                "disk2": DISK,
            },
            None,
        )
    )
    assert len(results_summary) == len(results_single_disk)
    for res_sum, res_single in zip(results_summary, results_single_disk):
        assert isinstance(res_single, type(res_sum))
        if isinstance(res_sum, Metric):
            assert isinstance(res_single, Metric)
            assert res_sum.value >= res_single.value


def test_cluster_check_diskstat_single_item() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.cluster_check_diskstat(
                "disk1",
                {},
                {
                    "node1": {
                        "disk1": DISK_HALF,
                    },
                },
                {
                    "node1": None,
                },
            )
        )
    results_cluster = list(
        diskstat.cluster_check_diskstat(
            "disk1",
            {},
            {
                "node_overwritten": {
                    "disk1": DISK_HALF,
                },
                "node1": {
                    "disk1": DISK,
                },
            },
            {
                "node_overwritten": None,
                "node1": None,
            },
        )
    )
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "disk1",
                {},
                {
                    "disk1": DISK_HALF,
                },
                None,
            )
        )
    results_non_cluster = list(
        diskstat.check_diskstat(
            "disk1",
            {},
            {
                "disk1": DISK,
            },
            None,
        )
    )
    assert results_cluster == results_non_cluster


def test_cluster_check_diskstat_summary() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.cluster_check_diskstat(
                "SUMMARY",
                {},
                {
                    "node1": {
                        "disk1": DISK_HALF,
                    },
                    "node2": {
                        "disk2": DISK_HALF,
                    },
                },
                {
                    "node1": None,
                    "node2": None,
                },
            )
        )
    results_cluster = list(
        diskstat.cluster_check_diskstat(
            "SUMMARY",
            {},
            {
                "node1": {
                    "disk1": DISK,
                },
                "node2": {
                    "disk2": DISK,
                },
            },
            {
                "node1": None,
                "node2": None,
            },
        )
    )
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "SUMMARY",
                {},
                {
                    "disk1": DISK_HALF,
                    "disk2": DISK_HALF,
                },
                None,
            )
        )
    results_non_cluster = list(
        diskstat.check_diskstat(
            "SUMMARY",
            {},
            {
                "disk1": DISK,
                "disk2": DISK,
            },
            None,
        )
    )
    assert results_cluster == results_non_cluster


def test_check_latency_calculation() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            diskstat.check_diskstat(
                "SUMMARY",
                {},
                {
                    "disk1": {
                        "timestamp": 5000000,
                        "average_write_wait": 10000,
                        "average_read_wait": 20000,
                    },
                },
                {},
            )
        )
    results_summary = list(
        diskstat.check_diskstat(
            "SUMMARY",
            {"latency": (3, 5)},
            {
                "disk1": {
                    "timestamp": 10000000,
                    "average_write_wait": 20000,
                    "average_read_wait": 40000,
                },
            },
            None,
        )
    )

    assert results_summary == [
        Result(state=state.OK, notice="Average read wait: 4 milliseconds"),
        Metric("disk_average_read_wait", 0.004),
        Result(state=state.OK, notice="Average write wait: 2 milliseconds"),
        Metric("disk_average_write_wait", 0.002),
        Result(
            state=state.WARN,
            notice="Latency: 4 milliseconds (warn/crit at 3 milliseconds/5 milliseconds)",
        ),
    ]
