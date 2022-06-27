#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

import pytest

from cmk.base.plugins.agent_based import storcli_cache_vault as mcv
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

OUTPUT: Final = """
CLI Version = 007.0916.0000.0000 Apr 05, 2019
Operating system = Linux 5.3.18-150300.59.54-default
Controller = 0
Status = Success
Description = None


Cachevault_Info :
===============

--------------------
Property    Value
--------------------
Type        CVPM02
Temperature 23 C
State       Optimal
--------------------


Firmware_Status :
===============

---------------------------------------
Property                         Value
---------------------------------------
NVCache State                    OK
Replacement required             No
No space to cache offload        No
Module microcode update required No
---------------------------------------


GasGaugeStatus :
==============

------------------------------
Property                Value
------------------------------
Pack Energy             252 J
Capacitance             111 %
Remaining Reserve Space 0
------------------------------


Design_Info :
===========

------------------------------------
Property                 Value
------------------------------------
Date of Manufacture      31/07/2020
Serial Number            1864
Manufacture Name         LSI
Design Capacity          288 J
Device Name              CVPM02
tmmFru                   N/A
CacheVault Flash Size    8.000 GB
tmmBatversionNo          0x05
tmmSerialNo              0x8334
tmm Date of Manufacture  09/03/2020
tmmPcbAssmNo             022544412A
tmmPCBversionNo          0x03
tmmBatPackAssmNo         49571-15C
scapBatversionNo         0x00
scapSerialNo             0x0748
scap Date of Manufacture 31/07/2020
scapPcbAssmNo            1700154483
scapPCBversionNo          E
scapBatPackAssmNo        49571-15C
Module Version           6635-02A
------------------------------------


Properties :
==========

--------------------------------------------------------------
Property             Value
--------------------------------------------------------------
Auto Learn Period    27d (2412000 seconds)
Next Learn time      2022/05/06  04:14:20 (705125660 seconds)
Learn Delay Interval 0 hour(s)
Auto-Learn Mode      Transparent
--------------------------------------------------------------


"""

OUTPUT_NO_CV = """
CLI Version = 007.0709.0000.0000 Aug 14, 2018
Operating system = Linux 5.4.0-87-generic
Controller = 0
Status = Failure
Description = None

Detailed Status :
===============

-------------------------------------------------
Ctrl Status Property ErrMsg                ErrCd
-------------------------------------------------
   0 Failed -        Cachevault is absent!    34
-------------------------------------------------

"""

STRING_TABLE: Final = [[line] for line in OUTPUT.splitlines() if line]


STRING_TABLE_NO_CV: Final = [[line] for line in OUTPUT_NO_CV.splitlines() if line]


@pytest.fixture(scope="module", name="section")
def _get_section() -> mcv.Section:
    return mcv.parse_storcli_cache_vault(STRING_TABLE)


@pytest.fixture(scope="module", name="section_no_cv")
def _get_section_no_cv() -> mcv.Section:
    return mcv.parse_storcli_cache_vault(STRING_TABLE_NO_CV)


def test_storcli_cache_vault_no_cv(section_no_cv: mcv.Section) -> None:

    assert not list(mcv.discover_storcli_cache_vault(section_no_cv))
    assert not list(mcv.check_storcli_cache_vault("/c0", section_no_cv))


def test_storcli_cache_vault_discovery(section: mcv.Section) -> None:

    assert list(mcv.discover_storcli_cache_vault(section)) == [
        Service(item="/c0"),
    ]


def test_storcli_cache_vault_check_item_not_found(section: mcv.Section) -> None:
    assert not list(mcv.check_storcli_cache_vault("/c1", section))


def test_storcli_cache_vault_check_ok(section: mcv.Section) -> None:
    assert list(mcv.check_storcli_cache_vault("/c0", section)) == [
        Result(state=State.OK, summary="Optimal"),
        Result(state=State.OK, summary="Capacitance: 111.00%"),
    ]


def test_storcli_cache_vault_check_not_optimal() -> None:
    # I've never seen non-optimal data, but this is what I assume should happen after parsing:
    assert list(
        mcv.check_storcli_cache_vault(
            "/c0",
            {
                "/c0": mcv.CacheVault(state="Hangry", needs_replacement=True, capacitance_perc=0.0),
            },
        )
    ) == [
        Result(state=State.CRIT, summary="Hangry"),
        Result(state=State.OK, summary="Capacitance: 0%"),
        Result(state=State.WARN, summary="Replacement required"),
    ]
