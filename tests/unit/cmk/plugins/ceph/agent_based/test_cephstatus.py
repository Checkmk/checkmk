#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import HostLabel, Metric, Result, Service, State
from cmk.plugins.ceph.agent_based.cephstatus import (
    check_cephstatus_testable,
    discover_cephstatus,
    host_label_cephstatus,
    parse_cephstatus,
)
from cmk.plugins.lib import df

STRING_TABLE = [
    [
        '{"fsid": "3e11fc83-29f7-4168-9bca-fe9257deb638", "health": {"status": "HEALTH_OK", "check'
        's": {}, "mutes": []}, "election_epoch": 700, "quorum": [0, 1, 2, 3], "quorum_names": ["pv'
        'e-fra-001", "pve-fra-002", "pve-fra-003", "pve-fra-004"], "quorum_age": 86762, "monmap": '
        '{"epoch": 8, "min_mon_release_name": "reef", "num_mons": 4}, "osdmap": {"epoch": 132814, '
        '"num_osds": 16, "num_up_osds": 16, "osd_up_since": 1719846756, "num_in_osds": 16, "osd_in'
        '_since": 1719846756, "num_remapped_pgs": 0}, "pgmap": {"pgs_by_state": [{"state_name": "a'
        'ctive+clean", "count": 129}], "num_pgs": 129, "num_pools": 2, "num_objects": 3044984, "da'
        'ta_bytes": 12067035856361, "bytes_used": 34639450083328, "bytes_avail": 88264260317184, "'
        'bytes_total": 122903710400512, "read_bytes_sec": 36996575, "write_bytes_sec": 30095073, "'
        'read_op_per_sec": 374, "write_op_per_sec": 581}, "fsmap": {"epoch": 1, "by_rank": [], "up'
        ':standby": 0}, "mgrmap": {"available": true, "num_standbys": 3, "modules": ["iostat", "re'
        'stful"], "services": {}}, "servicemap": {"epoch": 1117520, "modified": "2024-07-03T09:16:'
        '01.149462+0200", "services": {"osd": {"daemons": {"summary": "", "0": {"start_epoch": 0, '
        '"start_stamp": "0.000000", "gid": 0, "addr": "(unrecognized address family 0)/0", "metada'
        'ta": {}, "task_status": {}}, "1": {"start_epoch": 0, "start_stamp": "0.000000", "gid": 0,'
        ' "addr": "(unrecognized address family 0)/0", "metadata": {}, "task_status": {}}, "2": {"'
        'start_epoch": 0, "start_stamp": "0.000000", "gid": 0, "addr": "(unrecognized address fami'
        'ly 0)/0", "metadata": {}, "task_status": {}}, "3": {"start_epoch": 0, "start_stamp": "0.0'
        '00000", "gid": 0, "addr": "(unrecognized address family 0)/0", "metadata": {}, "task_stat'
        'us": {}}, "4": {"start_epoch": 0, "start_stamp": "0.000000", "gid": 0, "addr": "(unrecogn'
        'ized address family 0)/0", "metadata": {}, "task_status": {}}, "5": {"start_epoch": 0, "s'
        'tart_stamp": "0.000000", "gid": 0, "addr": "(unrecognized address family 0)/0", "metadata'
        '": {}, "task_status": {}}, "6": {"start_epoch": 0, "start_stamp": "0.000000", "gid": 0, "'
        'addr": "(unrecognized address family 0)/0", "metadata": {}, "task_status": {}}, "7": {"st'
        'art_epoch": 0, "start_stamp": "0.000000", "gid": 0, "addr": "(unrecognized address family'
        ' 0)/0", "metadata": {}, "task_status": {}}}}}}, "progress_events": {}}'
    ]
]


def test_host_label_cephstatus() -> None:
    assert list(host_label_cephstatus(parse_cephstatus(STRING_TABLE))) == [
        HostLabel("cmk/ceph/mon", "yes")
    ]


def test_discover_cephstatus() -> None:
    assert list(discover_cephstatus(parse_cephstatus(STRING_TABLE))) == [Service(item="Status")]


def test_check_cephstatus() -> None:
    now = 1719984586
    value_store = {
        "Status.delta": (now - 60, 0),
    }
    assert list(
        check_cephstatus_testable(
            "Status",
            df.FILESYSTEM_DEFAULT_PARAMS,
            parse_cephstatus(STRING_TABLE),
            now,
            value_store,
        )
    ) == [
        Result(state=State.OK, summary="Overall health OK"),
        Metric(
            "fs_used",
            33034753.87890625,
            levels=(93768089.59999943, 105489100.79999924),
            boundaries=(0.0, 117210112.0),
        ),
        Metric("fs_free", 84175358.12109375, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            28.184218336815725,
            levels=(79.99999999999952, 89.99999999999935),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 28.18% - 31.5 TiB of 112 TiB"),
        Metric("fs_size", 117210112.0, boundaries=(0.0, None)),
        Metric("growth", 47570045585.625),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +44.3 PiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +40585.27%"),
        Metric("trend", 47570045585.625),
        Result(state=State.OK, summary="Time left until disk full: 2 minutes 33 seconds"),
        Result(state=State.OK, summary="Objects: 3044984"),
        Metric("num_objects", 3044984.0),
        Result(state=State.OK, summary="Placement groups: 129"),
        Metric("num_pgs", 129.0),
        Result(state=State.OK, summary="PGs in active+clean: 129"),
        Metric("active_clean", 129.0),
    ]
