#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.broadcom_storage.agent_based.storcli_vdrives import (
    check_storcli_vdrives,
    discover_storcli_vdrives,
    parse_storcli_vdrives,
)
from cmk.plugins.broadcom_storage.lib.megaraid import LDISKS_DEFAULTS

STRING_TABLE = [
    ["------------------------------------------------------------------------"],
    ["DG/VD", "TYPE", "State", "Access", "Consist", "Cache", "Cac", "sCC", "Size", "Name"],
    ["------------------------------------------------------------------------"],
    ["0/0", "RAID5", "Optl", "RW", "Yes", "NRWBD", "-", "OFF", "4.723", "TB", "TMDCDS01_SR5_N1"],
    ["1/1", "RAID5", "Offline", "RW", "Yes", "RWBD", "-", "OFF", "4.364", "TB", "TMDCDS01_SSD_N1"],
    [
        "2/2",
        "RAID5",
        "Degraded",
        "RW",
        "Yes",
        "NRWBD",
        "-",
        "OFF",
        "2.909",
        "TB",
        "TMDCDS01_SSD_N2",
    ],
    ["------------------------------------------------------------------------"],
    ["EID=Enclosure", "Device", "ID|", "VD=Virtual", "Drive|", "DG=Drive", "Group|Rec=Recovery"],
    ["Cac=CacheCade|OfLn=OffLine|Pdgd=Partially", "Degraded|Dgrd=Degraded"],
    ["Optl=Optimal|RO=Read", "Only|RW=Read", "Write|HD=Hidden|TRANS=TransportReady|B=Blocked|"],
    ["Consist=Consistent|R=Read", "Ahead", "Always|NR=No", "Read", "Ahead|WB=WriteBack|"],
    ["AWB=Always", "WriteBack|WT=WriteThrough|C=Cached", "IO|D=Direct", "IO|sCC=Scheduled"],
    ["Check", "Consistency"],
    ["CLI", "Version", "=", "007.1017.0000.0000", "May", "10,", "2019"],
    ["Operating", "system", "=", "Windows", "Server", "2016"],
    ["Controller", "=", "1"],
    ["Status", "=", "Success"],
    ["Description", "=", "None"],
    ["Virtual", "Drives", ":"],
    ["=============="],
    ["-------------------------------------------------------------------------"],
    ["DG/VD", "TYPE", "State", "Access", "Consist", "Cache", "Cac", "sCC", "Size", "Name"],
    ["-------------------------------------------------------------------------"],
    ["0/0", "RAID1", "Unkn", "RW", "Yes", "RWBC", "-", "OFF", "558.406", "GB", "TMRMDS01_R1_N1"],
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="C0.0/0"),
                Service(item="C0.1/1"),
                Service(item="C0.2/2"),
                Service(item="C1.0/0"),
            ],
            id="For every item in the section, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items, no Services are discovered.",
        ),
    ],
)
def test_discover_storcli_vdrives(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_storcli_vdrives(parse_storcli_vdrives(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            "not_found",
            [],
            id="If the item is not present in the section, there are no result. This leads to state UNKNOWN.",
        ),
        pytest.param(
            STRING_TABLE,
            "C0.0/0",
            [
                Result(state=State.OK, summary="Raid type is RAID5"),
                Result(state=State.OK, summary="Access: RW"),
                Result(state=State.OK, summary="Drive is consistent"),
                Result(state=State.OK, summary="State is Optimal"),
            ],
            id="If the drive is consistent and has an 'Optimal' state, the check results are all OK.",
        ),
        pytest.param(
            STRING_TABLE,
            "C0.1/1",
            [
                Result(state=State.OK, summary="Raid type is RAID5"),
                Result(state=State.OK, summary="Access: RW"),
                Result(state=State.OK, summary="Drive is consistent"),
                Result(state=State.WARN, summary="State is Offline"),
            ],
            id="If the drive state is Offline or Recovery or Partially Degraded, the check result is WARN.",
        ),
        pytest.param(
            STRING_TABLE,
            "C0.2/2",
            [
                Result(state=State.OK, summary="Raid type is RAID5"),
                Result(state=State.OK, summary="Access: RW"),
                Result(state=State.OK, summary="Drive is consistent"),
                Result(state=State.CRIT, summary="State is Degraded"),
            ],
            id="If the drive state is Degraded, the check result is CRIT.",
        ),
        pytest.param(
            STRING_TABLE,
            "C1.0/0",
            [
                Result(state=State.OK, summary="Raid type is RAID1"),
                Result(state=State.OK, summary="Access: RW"),
                Result(state=State.OK, summary="Drive is consistent"),
                Result(state=State.UNKNOWN, summary="State is Unkn (unknown[Unkn])"),
            ],
            id="If the drive state is not known, the check result is UKKNOWN and provides a description.",
        ),
    ],
)
def test_check_storcli_vdrives(
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_storcli_vdrives(
                item=item,
                params=LDISKS_DEFAULTS,
                section=parse_storcli_vdrives(section),
            )
        )
        == expected_check_result
    )
