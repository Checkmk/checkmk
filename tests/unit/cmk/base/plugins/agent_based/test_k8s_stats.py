#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.k8s_stats_fs import (
    _check__k8s_stats_fs__core,
    discover_k8s_stats_fs,
)
from cmk.base.plugins.agent_based.k8s_stats_network import (
    _check__k8s_stats_network__proxy_results,
    discover_k8s_stats_network,
)
from cmk.base.plugins.agent_based.k8s_stats_section import parse_k8s

discovery = {
    "": [],
    "fs": [("/dev/sda1", {}), ("shm", {})],
    "network": [("cbr0", {}), ("eth0", {})],
}
parsed_data = {
    "filesystem": {
        "tmpfs": [
            {
                "capacity": 1043775488,
                "available": 1043775488,
                "inodes": 254828,
                "inodes_free": 254827,
            }
        ],
        "/dev/sda1": [
            {
                "capacity": 17293533184,
                "available": 12933038080,
                "inodes": 9732096,
                "inodes_free": 9668974,
            }
        ],
        "rootfs": [{"capacity": 0, "available": 0, "inodes": 0, "inodes_free": 0}],
    },
    "interfaces": {
        "eth1": [
            {
                "rx_packets": 573200,
                "tx_packets": 544397,
                "rx_errors": 0,
                "tx_errors": 0,
                "rx_bytes": 371123972,
                "tx_bytes": 1358359683,
                "rx_dropped": 0,
                "tx_dropped": 0,
            }
        ],
        "eth0": [
            {
                "rx_packets": 465930,
                "tx_packets": 184527,
                "rx_errors": 0,
                "tx_errors": 0,
                "rx_bytes": 468641826,
                "tx_bytes": 11076147,
                "rx_dropped": 0,
                "tx_dropped": 0,
            }
        ],
        "sit0": [
            {
                "rx_packets": 0,
                "tx_packets": 0,
                "rx_errors": 0,
                "tx_errors": 0,
                "rx_bytes": 0,
                "tx_bytes": 0,
                "rx_dropped": 0,
                "tx_dropped": 0,
            }
        ],
    },
    "timestamp": 1553765630.0,
}


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        pytest.param(
            "{"
            '"cpu": {"usage": {"total": 63704543240150, "user": 25198590000000, "system": 16755300000000}, "load_average": 0, "schedstat": {"runqueue_time": 0, "run_time": 0, "run_periods": 0}, "cfs": {"throttled_time": 0, "periods": 0, "throttled_periods": 0}}, '
            '"processes": {"process_count": 0, "fd_count": 0}, '
            '"network": {"tx_dropped": 0, "rx_packets": 573200, '
            '  "interfaces": [{"tx_dropped": 0, "rx_packets": 573200, "name": "eth1", "rx_bytes": 371123972, "tx_errors": 0, "tx_bytes": 1358359683, "rx_dropped": 0, "tx_packets": 544397, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 465930, "name": "eth0", "rx_bytes": 468641826, "tx_errors": 0, "tx_bytes": 11076147, "rx_dropped": 0, "tx_packets": 184527, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 0, "name": "sit0", "rx_bytes": 0, "tx_errors": 0, "tx_bytes": 0, "rx_dropped": 0, "tx_packets": 0, "rx_errors": 0}], '
            '  "udp": {"RxQueued": 0, "Listen": 0, "Dropped": 0, "TxQueued": 0}, '
            '  "tcp": {"Established": 0, "TimeWait": 0, "LastAck": 0, "Closing": 0, "SynRecv": 0, "SynSent": 0, "FinWait1": 0, "FinWait2": 0, "CloseWait": 0, "Close": 0, "Listen": 0}, '
            '  "tcp6": {"Established": 0, "TimeWait": 0, "LastAck": 0, "Closing": 0, "SynRecv": 0, "SynSent": 0, "FinWait1": 0, "FinWait2": 0, "CloseWait": 0, "Close": 0, "Listen": 0}, '
            '  "tx_bytes": 1358359683, "rx_dropped": 0, "name": "eth1", "rx_bytes": 371123972, "tx_errors": 0, '
            '  "udp6": {"RxQueued": 0, "Listen": 0, "Dropped": 0, "TxQueued": 0}, '
            '  "rx_errors": 0, "tx_packets": 544397}, '
            '"filesystem": ['
            '  {"available": 1043775488, "capacity": 1043775488, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, '
            '   "inodes_free": 254827, "reads_completed": 0, "read_time": 0, "writes_merged": 0, '
            '   "inodes": 254828, "device": "tmpfs", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, '
            '  {"available": 12933038080, "capacity": 17293533184, "io_time": 3353942, "sectors_read": 2393042, '
            '   "writes_completed": 2479813, "weighted_io_time": 4655694, "inodes_free": 9668974, '
            '   "reads_completed": 37680, "read_time": 58206, "writes_merged": 924180, "inodes": 9732096, "device": "/dev/sda1", "sectors_written": 175754080, "reads_merged": 675, "has_inodes": true, '
            '   "usage": 3347623936, "write_time": 4611717, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, '
            '  {"available": 0, "capacity": 0, "io_time": 0, "sectors_read": 0, "writes_completed": 0, '
            '   "weighted_io_time": 0, "inodes_free": 0, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 0, "device": "rootfs", "sectors_written": 0, "reads_merged": 0, '
            '   "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}], '
            '"timestamp": 1553765630.0, '
            '"memory": {"failcnt": 0, "hierarchical_data": {"pgfault": 36934, "pgmajfault": 1}, "swap": 311656448, "usage": 1865175040, "rss": 963272704, "cache": 901902336, "max_usage": 1473351680, "mapped_file": 234881024, "container_data": {"pgfault": 36934, "pgmajfault": 1}, "working_set": 1772285952}, '
            '"task_stats": {"nr_stopped": 0, "nr_sleeping": 0, "nr_uninterruptible": 0, "nr_running": 0, "nr_io_wait": 0}, '
            '"diskio": {}'
            "}",
            parsed_data,
            id="0",
        ),
        pytest.param(
            '{"network": {"tx_dropped": 0, "rx_packets": 138579713, "name": "eth0eth0eth0", "rx_bytes": 255668578132, "tx_errors": 0, "interfaces": [{"tx_dropped": 0, "rx_packets": 27938601, "name": "eth0", "rx_bytes": 66270703699, "tx_errors": 0, "tx_bytes": 6741313890, "rx_dropped": 0, "tx_packets": 24730953, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 19431812, "name": "cbr0", "rx_bytes": 3937726843, "tx_errors": 0, "tx_bytes": 60270654692, "rx_dropped": 0, "tx_packets": 22147430, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 41698636, "name": "eth0", "rx_bytes": 111016504455, "tx_errors": 0, "tx_bytes": 9524184437, "rx_dropped": 0, "tx_packets": 37783999, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 32033132, "name": "cbr0", "rx_bytes": 5574866151, "tx_errors": 0, "tx_bytes": 102989209987, "rx_dropped": 0, "tx_packets": 36262872, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 68942476, "name": "eth0", "rx_bytes": 78381369978, "tx_errors": 0, "tx_bytes": 14358691723, "rx_dropped": 0, "tx_packets": 65014942, "rx_errors": 0}, {"tx_dropped": 0, "rx_packets": 57242186, "name": "cbr0", "rx_bytes": 6657123557, "tx_errors": 0, "tx_bytes": 59168669231, "rx_dropped": 0, "tx_packets": 59614737, "rx_errors": 0}], "udp": {"RxQueued": 0, "Listen": 0, "Dropped": 0, "TxQueued": 0}, "tcp": {"Established": 0, "FinWait2": 0, "TimeWait": 0, "FinWait1": 0, "LastAck": 0, "CloseWait": 0, "Close": 0, "Closing": 0, "SynSent": 0, "SynRecv": 0, "Listen": 0}, "udp6": {"RxQueued": 0, "Listen": 0, "Dropped": 0, "TxQueued": 0}, "tcp6": {"Established": 0, "FinWait2": 0, "TimeWait": 0, "FinWait1": 0, "LastAck": 0, "CloseWait": 0, "Close": 0, "Closing": 0, "SynSent": 0, "SynRecv": 0, "Listen": 0}, "tx_bytes": 30624190050, "rx_dropped": 0, "tx_packets": 127529894, "rx_errors": 0}, "timestamp": 1550235205.3, "filesystem": [{"available": 6338084864, "capacity": 10340831232, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 1192403, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 1280000, "device": "shm", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 3985969152, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 53166080, "capacity": 60985344, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 72213, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 74444, "device": "tmpfs", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 7819264, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 6338084864, "capacity": 10340831232, "io_time": 44083600, "sectors_read": 1836124319, "writes_completed": 7357899, "weighted_io_time": 132609732, "inodes_free": 1192403, "reads_completed": 27584070, "read_time": 298349136, "writes_merged": 1569161, "inodes": 1280000, "device": "/dev/sda1", "sectors_written": 339114072, "reads_merged": 3830089, "has_inodes": true, "usage": 3985969152, "write_time": 10228632, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 51929088, "capacity": 60985344, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 71718, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 74444, "device": "tmpfs", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 9056256, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 5637185536, "capacity": 10340831232, "io_time": 96157472, "sectors_read": 5500795231, "writes_completed": 10807390, "weighted_io_time": 262362688, "inodes_free": 1191724, "reads_completed": 74970732, "read_time": 468791932, "writes_merged": 2447338, "inodes": 1280000, "device": "/dev/sda1", "sectors_written": 510582792, "reads_merged": 10446189, "has_inodes": true, "usage": 4686868480, "write_time": 10072652, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 67108864, "capacity": 67108864, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 74443, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 74444, "device": "shm", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 7372996608, "capacity": 10340831232, "io_time": 7030452, "sectors_read": 292392161, "writes_completed": 19981660, "weighted_io_time": 24071076, "inodes_free": 1193221, "reads_completed": 3403200, "read_time": 28540088, "writes_merged": 4234349, "inodes": 1280000, "device": "/dev/sda1", "sectors_written": 303279512, "reads_merged": 509925, "has_inodes": true, "usage": 2951057408, "write_time": 11640704, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 67108864, "capacity": 67108864, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 74443, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 74444, "device": "shm", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, {"available": 52400128, "capacity": 60985344, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, "inodes_free": 71989, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 74444, "device": "tmpfs", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 8585216, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}], "task_stats": {"nr_stopped": 0, "nr_sleeping": 0, "nr_uninterruptible": 0, "nr_running": 0, "nr_io_wait": 0}, "diskio": {"io_service_bytes": [{"device": "/dev/sda", "major": 8, "stats": {"Read": 328560128, "Async": 440613425152, "Write": 449184505856, "Total": 449513065984, "Sync": 8899640832}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "/dev/sda", "major": 8, "stats": {"Read": 375639552, "Async": 632165187584, "Write": 645268078592, "Total": 645643718144, "Sync": 13478530560}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}, {"device": "/dev/sda", "major": 8, "stats": {"Read": 417633280, "Async": 146866446336, "Write": 170888749056, "Total": 171306382336, "Sync": 24439936000}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}], "io_serviced": [{"device": "/dev/sda", "major": 8, "stats": {"Read": 17268, "Async": 6519824, "Write": 8609407, "Total": 8626675, "Sync": 2106851}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "/dev/sda", "major": 8, "stats": {"Read": 21887, "Async": 9674169, "Write": 12813376, "Total": 12835263, "Sync": 3161094}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 7}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 6}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 4}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 3}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 1}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 0}, {"device": "/dev/sda", "major": 8, "stats": {"Read": 8707, "Async": 17297911, "Write": 23084989, "Total": 23093696, "Sync": 5795785}, "minor": 0}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 5}, {"device": "", "major": 7, "stats": {"Read": 0, "Async": 0, "Write": 0, "Total": 0, "Sync": 0}, "minor": 2}]}, "memory": {"cache": 50888704, "working_set": 1023115264, "failcnt": 0, "hierarchical_data": {"pgfault": 512213, "pgmajfault": 5917}, "swap": 0, "usage": 1190318080, "rss": 700514304, "container_data": {"pgfault": 512213, "pgmajfault": 5917}, "max_usage": 2352873472}, "cpu": {"usage": {"per_cpu_usage": [86016032804509, 127085001891550, 230915408126829], "total": 444016442822888, "user": 258352170000000, "system": 141379920000000}, "load_average": 0, "cfs": {"throttled_time": 0, "periods": 0, "throttled_periods": 0}}}',
            {
                "filesystem": {
                    "shm": [
                        {
                            "capacity": 10340831232,
                            "available": 6338084864,
                            "inodes": 1280000,
                            "inodes_free": 1192403,
                        },
                        {
                            "capacity": 67108864,
                            "available": 67108864,
                            "inodes": 74444,
                            "inodes_free": 74443,
                        },
                        {
                            "capacity": 67108864,
                            "available": 67108864,
                            "inodes": 74444,
                            "inodes_free": 74443,
                        },
                    ],
                    "tmpfs": [
                        {
                            "capacity": 60985344,
                            "available": 53166080,
                            "inodes": 74444,
                            "inodes_free": 72213,
                        },
                        {
                            "capacity": 60985344,
                            "available": 51929088,
                            "inodes": 74444,
                            "inodes_free": 71718,
                        },
                        {
                            "capacity": 60985344,
                            "available": 52400128,
                            "inodes": 74444,
                            "inodes_free": 71989,
                        },
                    ],
                    "/dev/sda1": [
                        {
                            "capacity": 10340831232,
                            "available": 6338084864,
                            "inodes": 1280000,
                            "inodes_free": 1192403,
                        },
                        {
                            "capacity": 10340831232,
                            "available": 5637185536,
                            "inodes": 1280000,
                            "inodes_free": 1191724,
                        },
                        {
                            "capacity": 10340831232,
                            "available": 7372996608,
                            "inodes": 1280000,
                            "inodes_free": 1193221,
                        },
                    ],
                },
                "interfaces": {
                    "eth0": [
                        {
                            "rx_packets": 27938601,
                            "tx_packets": 24730953,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 66270703699,
                            "tx_bytes": 6741313890,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                        {
                            "rx_packets": 41698636,
                            "tx_packets": 37783999,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 111016504455,
                            "tx_bytes": 9524184437,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                        {
                            "rx_packets": 68942476,
                            "tx_packets": 65014942,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 78381369978,
                            "tx_bytes": 14358691723,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                    ],
                    "cbr0": [
                        {
                            "rx_packets": 19431812,
                            "tx_packets": 22147430,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 3937726843,
                            "tx_bytes": 60270654692,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                        {
                            "rx_packets": 32033132,
                            "tx_packets": 36262872,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 5574866151,
                            "tx_bytes": 102989209987,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                        {
                            "rx_packets": 57242186,
                            "tx_packets": 59614737,
                            "rx_errors": 0,
                            "tx_errors": 0,
                            "rx_bytes": 6657123557,
                            "tx_bytes": 59168669231,
                            "rx_dropped": 0,
                            "tx_dropped": 0,
                        },
                    ],
                },
                "timestamp": 1550235205.3,
            },
            id="1",
        ),
    ],
)
def test_parse_k8s(string_table, expected_parsed_data) -> None:
    assert parse_k8s([[string_table]]) == expected_parsed_data


@pytest.mark.parametrize(
    "section,expected_items",
    [
        (parsed_data, [Service(item="/dev/sda1")]),
    ],
)
def test_discover_k8s_stats_fs(section, expected_items) -> None:
    assert list(discover_k8s_stats_fs(section)) == expected_items


@pytest.mark.parametrize(
    "section,expected_items",
    [
        (parsed_data, [Service(item="eth1"), Service(item="eth0"), Service(item="sit0")]),
    ],
)
def test_discover_k8s_stats_network(section, expected_items) -> None:
    assert list(discover_k8s_stats_network(section, None)) == expected_items


@pytest.mark.parametrize(
    "section,expected_results",
    [
        (
            parsed_data,
            [
                Metric(
                    "fs_used",
                    4158.4921875,
                    levels=(13193.91875, 14843.15859375),
                    boundaries=(0.0, 16492.3984375),
                ),
                Metric("fs_size", 16492.3984375, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    25.21459933956316,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=state.OK, summary="25.21% used (4.06 of 16.1 GiB)"),
            ],
        )
    ],
)
def test__check_k8s_stats_fs(section, expected_results) -> None:
    vs: Dict[str, Any] = {}
    for _ in range(2):
        results = list(
            _check__k8s_stats_fs__core(
                vs,
                "/dev/sda1",
                {},
                section,
            )
        )

    print("\n", "\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize(
    "section,expected_results",
    [
        (
            parsed_data,
            [
                Result(state=state.OK, summary="In: 0.00 Bit/s"),
                Metric("in", 0.0),
                Result(state=state.OK, summary="Out: 0.00 Bit/s"),
                Metric("out", 0.0),
                Metric("if_in_pkts", 0.0, boundaries=(0.0, None)),
                Metric("if_in_errors", 0.0, boundaries=(0.0, None)),
                Result(state=state.OK, summary="Input error rate: 0.00/s"),
                Metric("if_out_pkts", 0.0, boundaries=(0.0, None)),
                Metric("if_out_errors", 0.0, boundaries=(0.0, None)),
                Result(state=state.OK, summary="Output error rate: 0.00/s"),
                Result(state=state.OK, summary="Input Discards: 0.00/s"),
                Metric("if_in_discards", 0.0, boundaries=(0.0, None)),
                Result(state=state.OK, summary="Output Discards: 0.00/s"),
                Metric("if_out_discards", 0.0, boundaries=(0.0, None)),
            ],
        )
    ],
)
def test__check_k8s_stats_network(section, expected_results) -> None:
    vs: Dict[str, Any] = {}
    for _ in range(2):
        section = {
            **section,
            "timestamp": section["timestamp"] + 1,
        }
        results = list(
            _check__k8s_stats_network__proxy_results(
                vs,
                "eth1",
                {},
                section,
                None,
            )
        )

    print("\n", "\n".join(str(r) for r in results))
    assert results == expected_results


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
