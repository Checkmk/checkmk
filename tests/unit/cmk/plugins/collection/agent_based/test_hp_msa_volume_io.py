#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.diskstat_io import check_hp_msa_volume_io

_SECTION = {
    "VMFS_01": {
        "durable-id": "V3",
        "data-read-numeric": "23719999539712",
        "data-written-numeric": "18093374647808",
        "virtual-disk-name": "A",
        "raidtype": "RAID0",
    },
    "VMFS_02": {
        "durable-id": "V4",
        "data-read-numeric": "49943891507200",
        "data-written-numeric": "7384656100352",
        "virtual-disk-name": "A",
        "raidtype": "RAID0",
    },
}


def test_io_check_item() -> None:
    assert list(check_hp_msa_volume_io("VMFS_01", {"flex_levels": "irrelevant"}, _SECTION)) == [
        Result(state=State.OK, summary="A (RAID0)"),
    ]
