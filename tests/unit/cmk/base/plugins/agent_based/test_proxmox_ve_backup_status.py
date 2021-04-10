#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

BACKUP_DATA = [[
    '{"last_backup": {'
    '    "started_time": "2020-04-16 22:20:43",'
    '    "total_duration": 120,'
    '    "archive_name": "/tmp/vdump-qemu-115-2020_04_16-22_20_43.vma.lzo",'
    '    "archive_size": 1099511627776,'
    '    "transfer_size": 2199023255552,'
    '    "transfer_time": 1000}}'
]]


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
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA),
        (
            Result(state=State.OK, summary='Age: 18 hours 39 minutes'),
            Metric('age', 67157.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 0 seconds'),
            Result(state=State.OK, summary='Name: /tmp/vdump-qemu-115-2020_04_16-22_20_43.vma.lzo'),
            Result(state=State.OK, summary='Size: 1.00 TiB'),
            Result(state=State.OK, summary='Bandwidth: 2.20 GB/s'),
        ),
    ),
    (
        {
            'age_levels_upper': (43200, 86400)
        },
        parse_proxmox_ve_vm_backup_status(BACKUP_DATA),
        (
            Result(
                state=State.WARN,
                summary='Age: 18 hours 39 minutes (warn/crit at 12 hours 0 minutes/1 day 0 hours)',
            ),
            Metric('age', 67157.0, levels=(43200.0, 86400.0), boundaries=(0.0, None)),
            Result(state=State.OK, summary='Time: 2020-04-16 22:20:43'),
            Result(state=State.OK, summary='Duration: 2 minutes 0 seconds'),
            Result(state=State.OK, summary='Name: /tmp/vdump-qemu-115-2020_04_16-22_20_43.vma.lzo'),
            Result(state=State.OK, summary='Size: 1.00 TiB'),
            Result(state=State.OK, summary='Bandwidth: 2.20 GB/s'),
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
