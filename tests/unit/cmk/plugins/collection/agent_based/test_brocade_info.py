#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import OIDCached, Result, Service, SNMPTree, State
from cmk.plugins.collection.agent_based import brocade_info

_ENTITY_DESCR = "Brocade Communications Systems, Inc. SN6700B"


def test_entity_description_column_is_walked_and_cached() -> None:
    assert brocade_info.snmp_section_brocade_info.fetch[0] == SNMPTree(
        base=".1.3.6.1.2.1.47.1.1.1.1",
        oids=[OIDCached("2")],
    )


def test_check_reports_model_firmware_ssn_and_wwn() -> None:
    section = [[[_ENTITY_DESCR]], [["v9.2.2b", "BRC1234567"]], [["ABCDEFGH"]]]

    assert list(brocade_info.check_brocade_info(section)) == [
        Result(
            state=State.OK,
            summary=(
                f"Model: {_ENTITY_DESCR}, SSN: BRC1234567, Firmware Version: v9.2.2b, "
                "WWN: 41:42:43:44:45:46:47:48"
            ),
        )
    ]


def test_service_survives_a_switch_without_entity_mib() -> None:
    section = [[], [["v9.2.2b", "BRC1234567"]], []]

    assert list(brocade_info.inventory_brocade_info(section)) == [Service()]
    assert list(brocade_info.check_brocade_info(section)) == [
        Result(
            state=State.OK,
            summary="Model: -, SSN: BRC1234567, Firmware Version: v9.2.2b, WWN: -",
        )
    ]


def test_empty_device_yields_no_service() -> None:
    section: list[list[list[str]]] = [[], [], []]

    assert not list(brocade_info.inventory_brocade_info(section))
    assert list(brocade_info.check_brocade_info(section)) == [
        Result(state=State.UNKNOWN, summary="no information found")
    ]
