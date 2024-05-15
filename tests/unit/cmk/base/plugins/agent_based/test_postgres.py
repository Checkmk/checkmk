#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionName
from cmk.utils.translations import TranslationOptions

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.parser import AgentParser, AgentRawDataSectionElem, NO_SELECTION, SectionStore

import cmk.base.api.agent_based.register as agent_based_register

from cmk.agent_based.v1 import Service
from cmk.agent_based.v1.type_defs import StringTable

# from SUP-12594
SECTION_RAW = AgentRawData(
    b"""<<<postgres_stat_database:sep(59)>>>
[[[main]]]
datid;datname;numbackends;xact_commit;xact_rollback;blks_read;blks_hit;tup_returned;tup_fetched;tup_inserted;tup_updated;tup_deleted;datsize
0;;0;117;1;220;639432;202318;152460;315;22;4;
4;template0;0;3219;0;381;135856;1410295;26353;0;249;0;7697199
16400;template1;0;3531;0;817;162459;1426114;39723;21;1234;14;7836463
16401;nnnnnn;13;72481;0;605700;42059122;93186236;19734463;14878;7729;20;754799407
18054;postgres;1;36645;1;1054;13223743;20917633;7315546;21;1234;14;7779119"""
)


def parse(tmp_path: Path, section_raw: AgentRawData) -> StringTable:
    # TODO: if this is a good idea, we should move this code to a different location
    host_name = HostName("test-host")
    logger = logging.getLogger("test")
    store_path = tmp_path / "store"
    store = SectionStore[Sequence[AgentRawDataSectionElem]](store_path, logger=logger)
    parser = AgentParser(
        host_name,
        store,
        host_check_interval=0,
        keep_outdated=True,
        translation=TranslationOptions(),
        encoding_fallback="ascii",
        logger=logger,
    )
    ahs = parser.parse(section_raw, selection=NO_SELECTION)
    assert len(ahs.sections) == 1  # we expect only a single section in the raw data
    sequence_string_table = next(iter(ahs.sections.values()))
    return [list(line) for line in sequence_string_table]


def _get_parsed(tmp_path: Path, fix_register: FixRegister) -> dict[str, dict[str, str | int]]:
    parse_function = fix_register.agent_sections[
        SectionName("postgres_stat_database")
    ].parse_function
    string_table = parse(tmp_path, SECTION_RAW)
    parsed = parse_function(string_table)

    assert parsed == {
        "MAIN/access_to_shared_objects": {
            "blks_hit": 639432,
            "blks_read": 220,
            "datid": "0",  # OID of this database, or 0 for objects belonging to a shared relation
            "datsize": "",
            "numbackends": 0,
            "tup_deleted": 4,
            "tup_fetched": 152460,
            "tup_inserted": 315,
            "tup_returned": 202318,
            "tup_updated": 22,
            "xact_commit": 117,
            "xact_rollback": 1,
        },
        "MAIN/nnnnnn": {
            "blks_hit": 42059122,
            "blks_read": 605700,
            "datid": "16401",
            "datsize": 754799407,
            "numbackends": 13,
            "tup_deleted": 20,
            "tup_fetched": 19734463,
            "tup_inserted": 14878,
            "tup_returned": 93186236,
            "tup_updated": 7729,
            "xact_commit": 72481,
            "xact_rollback": 0,
        },
        "MAIN/postgres": {
            "blks_hit": 13223743,
            "blks_read": 1054,
            "datid": "18054",
            "datsize": 7779119,
            "numbackends": 1,
            "tup_deleted": 14,
            "tup_fetched": 7315546,
            "tup_inserted": 21,
            "tup_returned": 20917633,
            "tup_updated": 1234,
            "xact_commit": 36645,
            "xact_rollback": 1,
        },
        "MAIN/template0": {
            "blks_hit": 135856,
            "blks_read": 381,
            "datid": "4",
            "datsize": 7697199,
            "numbackends": 0,
            "tup_deleted": 0,
            "tup_fetched": 26353,
            "tup_inserted": 0,
            "tup_returned": 1410295,
            "tup_updated": 249,
            "xact_commit": 3219,
            "xact_rollback": 0,
        },
        "MAIN/template1": {
            "blks_hit": 162459,
            "blks_read": 817,
            "datid": "16400",
            "datsize": 7836463,
            "numbackends": 0,
            "tup_deleted": 14,
            "tup_fetched": 39723,
            "tup_inserted": 21,
            "tup_returned": 1426114,
            "tup_updated": 1234,
            "xact_commit": 3531,
            "xact_rollback": 0,
        },
    }

    return parsed


@pytest.mark.parametrize(
    ("check_plugin_name", "expected_discovery_result"),
    [
        pytest.param(
            CheckPluginName("postgres_stat_database_size"),
            [
                Service(item="MAIN/template0"),
                Service(item="MAIN/template1"),
                Service(item="MAIN/nnnnnn"),
                Service(item="MAIN/postgres"),
            ],
            id="size",
        ),
        pytest.param(
            CheckPluginName("postgres_stat_database"),
            [
                Service(item="MAIN/access_to_shared_objects"),
                Service(item="MAIN/template0"),
                Service(item="MAIN/template1"),
                Service(item="MAIN/nnnnnn"),
                Service(item="MAIN/postgres"),
            ],
            id="stats",
        ),
    ],
)
def test_discover_size(
    tmp_path: Path,
    fix_register: FixRegister,
    check_plugin_name: CheckPluginName,
    expected_discovery_result: list[Service],
) -> None:
    plugin = agent_based_register.get_check_plugin(check_plugin_name)
    assert plugin

    parsed = _get_parsed(tmp_path, fix_register)

    assert list(plugin.discovery_function(parsed)) == expected_discovery_result
