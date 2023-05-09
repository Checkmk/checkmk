#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from datetime import datetime
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Metric

from cmk.base.plugins.agent_based.proxmox_ve_backup_status import (
    check_proxmox_ve_vm_backup_status,
    parse_proxmox_ve_vm_backup_status,
)

FROZEN_TIME = datetime.strptime("2020-04-17 17:00:00", '%Y-%m-%d %H:%M:%S')

NO_BACKUP_DATA = [['{"last_backup": null}']]

BACKUP_DATA1 = [[
    '{"last_backup": {'
    '    "started_time": "2020-04-16 22:20:43",'
    '    "total_duration": 120,'
    '    "archive_name": "/some/file.name.vma.lzo",'
    '    "archive_size": 1099511627776,'
    '    "transfer_size": 2199023255552,'
    '    "transfer_time": 1000}}'
]]

BACKUP_DATA2 = [[
    '{"last_backup": {'
    '    "started_time": "2020-04-16 22:20:43",'
    '    "total_duration": 140,'
    '    "archive_name": "/some/file.name.vma.lzo",'
    '    "upload_amount": 10995116277,'
    '    "upload_total": 1099511627776,'
    '    "upload_time": 120'
    '}}'
]]

BACKUP_DATA3 = [[
    '{"last_backup": {'
    '    "started_time": "2020-04-16 22:20:43",'
    '    "total_duration": 140,'
    '    "archive_name": "/some/file.name.vma.lzo",'
    '    "bytes_written_size": 10995116277,'
    '    "bytes_written_bandwidth": 10000'
    '  }}'
]]

BACKUP_DATA4 = [[
    '{"last_backup": {'
    '    "started_time": "2020-04-16 22:20:43",'
    '    "total_duration": 140,'
    '    "archive_name": "/some/file.name.vma.lzo",'
    '    "backup_amount": 10995116277,'
    '    "backup_total": 1099511627776,'
    '    "backup_time": 120'
    '}}'
]]


def set_null_values(backup_data):
    backup_data["last_backup"].update({
        "transfer_time": 0,
        "upload_amount": 0,
        "upload_time": 0,
    })
    return backup_data


@pytest.mark.parametrize("params,section,expected_results", (
    (
        {},
        parse_proxmox_ve_vm_backup_status(NO_BACKUP_DATA),
        (Result(state=State.OK, summary='No backup found and none needed'),),
    ),
    (
        {
            'age_levels_upper': (43200, 86400)
        },
        parse_proxmox_ve_vm_backup_status(NO_BACKUP_DATA),
        (Result(state=State.CRIT, summary='No backup found'),),
    ),
    (
        {},
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA1),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 0 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Size: 1.00 TiB'),
            Result(state=State.OK, summary='Bandwidth: 2.20 GB/s'),
        ),
    ),
    (
        {
            'age_levels_upper': (43200, 86400)
        },
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA1),
        (
            Result(
                state=State.WARN,
                summary='Age: 18 hours 39 minutes (warn/crit at 12 hours 0 minutes/1 day 0 hours)',
            ),
            Metric('age', 67157.0, levels=(43200.0, 86400.0), boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 0 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Size: 1.00 TiB'),
            Result(state=State.OK, summary='Bandwidth: 2.20 GB/s'),
        ),
    ),
    (
        {},
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA2),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 20 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Dedup rate: 100.00'),
            Result(state=State.OK, summary='Bandwidth: 91.6 MB/s'),
        ),
    ),
    (
        {},
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA3),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 20 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Bandwidth: 10.0 kB/s'),
        ),
    ),
    (
        {},
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA4),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 20 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Dedup rate: 100.00'),
            Result(state=State.OK, summary='Bandwidth: 91.6 MB/s'),
        ),
    ),
    (
        {},
        set_null_values(parse_proxmox_ve_vm_backup_status(BACKUP_DATA1)),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 0 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Size: 1.00 TiB'),
        ),
    ),
    (
        {},
        set_null_values(parse_proxmox_ve_vm_backup_status(BACKUP_DATA2)),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 20 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
        ),
    ),
    (
        {},
        set_null_values(parse_proxmox_ve_vm_backup_status(BACKUP_DATA3)),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 20 seconds'),
            Result(state=State.OK, summary='Name: /some/file.name.vma.lzo'),
            Result(state=State.OK, summary='Bandwidth: 10.0 kB/s'),
        ),
    ),
))
def test_check_proxmox_ve_vm_backup_status(params, section, expected_results) -> None:
    results = tuple(check_proxmox_ve_vm_backup_status(FROZEN_TIME, params, section))
    print("\n" + ",\n".join(map(str, results)))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os
    from testlib.utils import cmk_path  # type: ignore[import]
    assert not pytest.main([
        "--doctest-modules",
        os.path.join(cmk_path(), "cmk/base/plugins/agent_based/proxmox_ve_backup_status.py")
    ])
    pytest.main(["-T=unit", "-vvsx", __file__])
