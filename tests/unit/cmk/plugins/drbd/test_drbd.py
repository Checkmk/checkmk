#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.drbd.agent_based import drbd

# <<<drbd>>>
# version: 8.3.8 (api:88/proto:86-94)
# GIT-hash: d78846e52224fd00562f7c225bcc25b2d422321d build by cssint@erzc20, 2010-06-17 14:47:26
#  0: cs:SyncSource ro:Primary/Secondary ds:UpToDate/Inconsistent C r----
#     ns:12031428 nr:0 dw:12031364 dr:1175992347 al:2179 bm:71877 lo:37 pe:0 ua:37 ap:0 ep:1 wo:b oos:301729988
#       [=======>............] sync'ed: 42.4% (294656/510908)M delay_probe: 145637
#       finish: 1:23:28 speed: 60,172 (51,448) K/sec

SECTION = [
    ["version:", "8.3.8", "(api:88/proto:86-94)"],
    [
        "GIT-hash:",
        "d78846e52224fd00562f7c225bcc25b2d422321d",
        "build",
        "by",
        "cssint@erzc20,",
        "2010-06-17",
        "14:47:26",
    ],
    ["0:", "cs:SyncSource", "ro:Primary/Secondary", "ds:UpToDate/Inconsistent", "C", "r----"],
    [
        "ns:12031428",
        "nr:0",
        "dw:12031364",
        "dr:1175992347",
        "al:2179",
        "bm:71877",
        "lo:37",
        "pe:0",
        "ua:37",
        "ap:0",
        "ep:1",
        "wo:b",
        "oos:301729988",
    ],
    ["[=======>............]", "sync'ed:", "42.4%", "(294656/510908)M", "delay_probe:", "145637"],
    ["finish:", "1:23:28", "speed:", "60,172", "(51,448)", "K/sec"],
]
UNCONFIGURED_SECTION = [*SECTION[:2], ["0:", "cs:Unconfigured", *SECTION[2][2:]], *SECTION[3:]]


@pytest.fixture(scope="function")
def patch_get_value_store_zero_change(monkeypatch: pytest.MonkeyPatch) -> None:
    zero_change_value_store = {
        "in": (0, 0),
        "out": (0, 12031428),
        "read": (0, 1175992347),
        "write": (0, 12031364),
    }
    monkeypatch.setattr(drbd, "get_value_store", lambda: zero_change_value_store)


class TestGeneralCheckType:
    def test_inventory_drbd(self) -> None:
        value = list(drbd.inventory_drbd(SECTION, "drbd"))
        expected = [
            (
                "drbd0",
                {
                    "diskstates_inventory": [
                        "UpToDate",
                        "Inconsistent",
                    ],
                    "roles_inventory": [
                        "Primary",
                        "Secondary",
                    ],
                },
            )
        ]
        assert value == expected

    def test_inventory_drbd_unconfigured_skipped(self) -> None:
        assert not list(drbd.inventory_drbd(UNCONFIGURED_SECTION, "drbd"))

    def test_check_drbd_with_params(self) -> None:
        params = {"diskstates_inventory": None, "roles_inventory": None}
        value = list(drbd.check_drbd_general("drbd0", params, SECTION))
        expected = [
            Result(state=State.WARN, summary="Connection State: SyncSource"),
            Result(state=State.OK, summary="Roles: Primary/Secondary"),
            Result(state=State.OK, summary="Diskstates: UpToDate/Inconsistent"),
        ]
        assert value == expected

    def test_check_drbd_without_params(self) -> None:
        value = list(drbd.check_drbd_general("drbd0", {}, SECTION))
        expected = [
            Result(
                state=State.WARN,
                summary="Connection State: SyncSource",
            ),
            Result(
                state=State.UNKNOWN,
                summary="Roles: Primary/Secondary (Check requires a new service discovery)",
            ),
            Result(
                state=State.WARN,
                summary="Diskstates: UpToDate/Inconsistent (Secondary/Inconsistent)",
            ),
        ]
        assert value == expected

    def test_check_drbd_missing_input_data(self) -> None:
        value = list(drbd.check_drbd_general("drbd0", {}, [[]]))
        expected = [Result(state=State.UNKNOWN, summary="Undefined state")]
        assert value == expected

    def test_check_drbd_unconfigured(self) -> None:
        value = list(drbd.check_drbd_general("drbd0", {}, UNCONFIGURED_SECTION))
        expected = [Result(state=State.CRIT, summary='The device is "Unconfigured"')]
        assert value == expected


class TestNetCheckType:
    def test_inventory_drbd(self) -> None:
        assert list(drbd.inventory_drbd(SECTION, "drbd.net"))[0] == ("drbd0", {})

    def test_inventory_drbd_unconfigured_skipped(self) -> None:
        assert not list(drbd.inventory_drbd(UNCONFIGURED_SECTION, "drbd.net"))

    @pytest.mark.usefixtures("patch_get_value_store_zero_change")
    def test_check_drbd(self) -> None:
        value = list(drbd.check_drbd_net("drbd0", SECTION))
        expected = [
            Result(state=State.OK, summary="In: 0.00 Bit/s"),
            Metric("in", 0.0),
            Result(state=State.OK, summary="Out: 0.00 Bit/s"),
            Metric("out", 0.0),
        ]
        assert value == expected

    def test_check_drbd_missing_input_data(self) -> None:
        value = list(drbd.check_drbd_net("drbd0", [[]]))
        expected = [Result(state=State.UNKNOWN, summary="Undefined state")]
        assert value == expected

    def test_check_drbd_unconfigured(self) -> None:
        value = list(drbd.check_drbd_net("drbd0", UNCONFIGURED_SECTION))
        expected = [Result(state=State.CRIT, summary='The device is "Unconfigured"')]
        assert value == expected


class TestDiskCheckType:
    def test_inventory_drbd(self) -> None:
        assert list(drbd.inventory_drbd(SECTION, "drbd.disk"))[0] == ("drbd0", {})

    def test_inventory_drbd_unconfigured_skipped(self) -> None:
        assert not list(drbd.inventory_drbd(UNCONFIGURED_SECTION, "drbd.disk"))

    @pytest.mark.usefixtures("patch_get_value_store_zero_change")
    def test_check_drbd(self) -> None:
        value = list(drbd.check_drbd_disk("drbd0", SECTION))
        expected = [
            Result(state=State.OK, summary="Write: 0.00 B/s"),
            Metric("write", 0.0),
            Result(state=State.OK, summary="Read: 0.00 B/s"),
            Metric("read", 0.0),
        ]
        assert value == expected

    def test_check_drbd_missing_input_data(self) -> None:
        value = list(drbd.check_drbd_disk("drbd0", [[]]))
        expected = [Result(state=State.UNKNOWN, summary="Undefined state")]
        assert value == expected

    def test_check_drbd_unconfigured(self) -> None:
        value = list(drbd.check_drbd_disk("drbd0", UNCONFIGURED_SECTION))
        expected = [Result(state=State.CRIT, summary='The device is "Unconfigured"')]
        assert value == expected


class TestStatsCheckType:
    def test_inventory_drbd(self) -> None:
        assert list(drbd.inventory_drbd(SECTION, "drbd.stats"))[0] == ("drbd0", {})

    def test_inventory_drbd_unconfigured_skipped(self) -> None:
        assert not list(drbd.inventory_drbd(UNCONFIGURED_SECTION, "drbd.stats"))

    def test_check_drbd(self) -> None:
        value = list(drbd.check_drbd_stats("drbd0", SECTION))
        expected = [
            Result(state=State.OK, summary="activity log updates: 2179"),
            Metric("activity_log_updates", 2179.0),
            Result(state=State.OK, summary="bit map updates: 71877"),
            Metric("bit_map_updates", 71877.0),
            Result(state=State.OK, summary="local count requests: 37"),
            Metric("local_count_requests", 37.0),
            Result(state=State.OK, summary="pending requests: 0"),
            Metric("pending_requests", 0.0),
            Result(state=State.OK, summary="unacknowledged requests: 37"),
            Metric("unacknowledged_requests", 37.0),
            Result(state=State.OK, summary="application pending requests: 0"),
            Metric("application_pending_requests", 0.0),
            Result(state=State.OK, summary="epoch objects: 1"),
            Metric("epoch_objects", 1.0),
            Result(state=State.OK, summary="write order: 0"),
            Metric("write_order", 0.0),
            Result(state=State.OK, summary="kb out of sync: 301729988"),
            Metric("kb_out_of_sync", 301729988.0),
        ]

        assert value == expected

    def test_check_drbd_missing_input_data(self) -> None:
        value = list(drbd.check_drbd_stats("drbd0", [[]]))
        expected = [Result(state=State.UNKNOWN, summary="Undefined state")]
        assert value == expected

    def test_check_drbd_unconfigured(self) -> None:
        value = list(drbd.check_drbd_stats("drbd0", UNCONFIGURED_SECTION))
        expected = [Result(state=State.CRIT, summary='The device is "Unconfigured"')]
        assert value == expected
