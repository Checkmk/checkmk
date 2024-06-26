#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import HostLabel, Metric, Result, Service, ServiceLabel, State
from cmk.plugins.ceph.agent_based.cephosd import (
    check_cephosd_testable,
    discover_cephosd,
    host_label_cephosd,
    parse_cephosd,
    Section,
)
from cmk.plugins.lib import df

STRING_TABLE = [
    [
        '{"df": {"nodes": [{"id": 0, "device_class": "nvme", "name": "osd.0", "type": "osd", "type'
        '_id": 0, "crush_weight": 6.986297607421875, "depth": 2, "pool_weights": {}, "reweight": 1'
        ', "kb": 7501447168, "kb_used": 2549415696, "kb_used_data": 2535704028, "kb_used_omap": 16'
        '343, "kb_used_meta": 13695144, "kb_avail": 4952031472, "utilization": 33.98565155368165, '
        '"var": 1.205839776982134, "pgs": 29, "status": "up"}, {"id": 1, "device_class": "nvme", "'
        'name": "osd.1", "type": "osd", "type_id": 0, "crush_weight": 6.986297607421875, "depth": '
        '2, "pool_weights": {}, "reweight": 1, "kb": 7501447168, "kb_used": 2112572916, "kb_used_d'
        'ata": 2099667756, "kb_used_omap": 13779, "kb_used_meta": 12891372, "kb_avail": 5388874252'
        ', "utilization": 28.162204821116458, "var": 0.9992189417696034, "pgs": 24, "status": "up"'
        '}, {"id": 2, "device_class": "nvme", "name": "osd.2", "type": "osd", "type_id": 0, "crush'
        '_weight": 6.986297607421875, "depth": 2, "pool_weights": {}, "reweight": 1, "kb": 7501447'
        '168, "kb_used": 2110612680, "kb_used_data": 2100940608, "kb_used_omap": 13934, "kb_used_m'
        'eta": 9658129, "kb_avail": 5390834488, "utilization": 28.1360733833272, "var": 0.99829177'
        '61666061, "pgs": 24, "status": "up"}, {"id": 3, "device_class": "nvme", "name": "osd.3", '
        '"type": "osd", "type_id": 0, "crush_weight": 6.986297607421875, "depth": 2, "pool_weights'
        '": {}, "reweight": 1, "kb": 7501447168, "kb_used": 2019565512, "kb_used_data": 2007913824'
        ', "kb_used_omap": 13347, "kb_used_meta": 11638300, "kb_avail": 5481881656, "utilization":'
        ' 26.922345339112038, "var": 0.9552276744870599, "pgs": 24, "status": "up"}]}, "perf": {"o'
        'sd_perf_infos": [{"id": 0, "perf_stats": {"commit_latency_ms": 0, "apply_latency_ms": 0, '
        '"commit_latency_ns": 0, "apply_latency_ns": 0}}, {"id": 2, "perf_stats": {"commit_latency'
        '_ms": 0, "apply_latency_ms": 0, "commit_latency_ns": 0, "apply_latency_ns": 0}}, {"id": 1'
        ', "perf_stats": {"commit_latency_ms": 0, "apply_latency_ms": 0, "commit_latency_ns": 0, "'
        'apply_latency_ns": 0}}, {"id": 3, "perf_stats": {"commit_latency_ms": 0, "apply_latency_m'
        's": 0, "commit_latency_ns": 0, "apply_latency_ns": 0}}]}}'
    ]
]


def _section() -> Section:
    assert (section := parse_cephosd(STRING_TABLE)) is not None
    return section


def test_host_label_cephosd() -> None:
    assert list(host_label_cephosd(_section())) == [HostLabel("cmk/ceph/osd", "yes")]


def test_discover_cephosd() -> None:
    assert list(discover_cephosd(_section())) == [
        Service(item="0", labels=[ServiceLabel("cephosd/device_class", "nvme")]),
        Service(item="1", labels=[ServiceLabel("cephosd/device_class", "nvme")]),
        Service(item="2", labels=[ServiceLabel("cephosd/device_class", "nvme")]),
        Service(item="3", labels=[ServiceLabel("cephosd/device_class", "nvme")]),
    ]


def test_check_cephosd() -> None:
    now = 1719984586
    value_store = {"0.delta": (now - 60, 0)}
    assert list(
        check_cephosd_testable("0", df.FILESYSTEM_DEFAULT_PARAMS, _section(), value_store, now)
    ) == [
        # unrealistic numbers due to the tests value store initialization
        Metric(
            "fs_used",
            2489663.765625,
            levels=(5860505.599999428, 6593068.799999237),
            boundaries=(0.0, 7325632.0),
        ),
        Metric("fs_free", 4835968.234375, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            33.98565155368165,
            levels=(79.99999999999218, 89.99999999998958),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 33.99% - 2.37 TiB of 6.99 TiB"),
        Metric("fs_size", 7325632.0, boundaries=(0.0, None)),
        Metric("growth", 3585115822.5),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +3.34 PiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +48939.34%"),
        Metric("trend", 3585115822.5),
        Result(state=State.OK, summary="Time left until disk full: 1 minute 57 seconds"),
        Result(state=State.OK, summary="PGs: 29"),
        Metric("num_pgs", 29.0),
        Result(state=State.OK, notice="Status: up"),
        Result(state=State.OK, summary="Apply latency: 0ms"),
        Metric("apply_latency", 0.0),
        Result(state=State.OK, summary="Commit latency: 0ms"),
        Metric("commit_latency", 0.0),
    ]
