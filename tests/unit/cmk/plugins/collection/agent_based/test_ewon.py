#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based import ewon

STRING_TABLE = [
    ["1", "0", "System"],
    ["2", "0", "System"],
    ["3", "0", "System"],
    ["4", "8192", "System"],
    ["5", "1", "N2-Versorgung"],
    ["6", "0", "Betriebsraum"],
    ["7", "0", "Betriebsraum"],
    ["8", "0", "Flur_Nebenraum"],
    ["9", "0", "Flur_Nebenraum"],
    ["10", "1527", "Schutzbereich01"],
    ["11", "1550", "Schutzbereich01"],
    ["12", "1550", "Schutzbereich01"],
    ["13", "1520", "Schutzbereich01"],
    ["14", "0", "Schutzbereich01"],
    ["15", "1029", "Schutzbereich01"],
    ["16", "512", "Schutzbereich01"],
    ["17", "513", "Schutzbereich01"],
    ["18", "1539", "Schutzbereich02"],
    ["19", "1550", "Schutzbereich02"],
    ["20", "1550", "Schutzbereich02"],
    ["21", "1520", "Schutzbereich02"],
    ["22", "0", "Schutzbereich02"],
    ["23", "1029", "Schutzbereich02"],
    ["24", "512", "Schutzbereich02"],
    ["25", "513", "Schutzbereich02"],
    ["26", "1533", "Schutzbereich03"],
    ["27", "1550", "Schutzbereich03"],
    ["28", "1550", "Schutzbereich03"],
    ["29", "1520", "Schutzbereich03"],
    ["30", "0", "Schutzbereich03"],
    ["31", "1029", "Schutzbereich03"],
    ["32", "512", "Schutzbereich03"],
    ["33", "513", "Schutzbereich03"],
    ["34", "0", "Schutzbereich04"],
    ["35", "0", "Schutzbereich04"],
    ["36", "0", "Schutzbereich04"],
    ["37", "0", "Schutzbereich04"],
    ["38", "0", "Schutzbereich04"],
    ["39", "0", "Schutzbereich04"],
    ["40", "0", "Schutzbereich04"],
    ["41", "0", "Schutzbereich04"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> ewon.Section:
    return ewon.parse_ewon(STRING_TABLE)


def test_discover_empty() -> None:
    assert list(ewon.discovery_ewon({"device": None}, {})) == [
        Service(item="eWON Status", parameters={"device": None}),
    ]


def test_check_empty() -> None:
    assert list(ewon.check_ewon("eWON Status", {"device": None}, {})) == [
        Result(
            state=State.WARN,
            summary="This device requires configuration. Please pick the device type.",
        ),
    ]


def test_discover_ewon(section: ewon.Section) -> None:
    assert list(ewon.discovery_ewon({"device": "oxyreduct"}, section)) == [
        Service(item="eWON Status", parameters={"device": "oxyreduct"}),
        Service(item="System", parameters={"device": "oxyreduct"}),
        Service(item="N2-Versorgung", parameters={"device": "oxyreduct"}),
        Service(item="Betriebsraum", parameters={"device": "oxyreduct"}),
        Service(item="Flur_Nebenraum", parameters={"device": "oxyreduct"}),
        Service(item="Schutzbereich01", parameters={"device": "oxyreduct"}),
        Service(item="Schutzbereich02", parameters={"device": "oxyreduct"}),
        Service(item="Schutzbereich03", parameters={"device": "oxyreduct"}),
    ]


def test_check_ewon_status(section: ewon.Section) -> None:
    assert list(ewon.check_ewon("eWON Status", {"device": "oxyreduct"}, section)) == [
        Result(state=State.OK, summary="Configured for oxyreduct"),
    ]


def test_check_ewon_inactive(section: ewon.Section) -> None:
    assert list(ewon.check_ewon("Flur_Nebenraum", {"device": "oxyreduct"}, section)) == [
        Result(state=State.OK, summary="O2 Sensor inactive"),
    ]


def test_check_ewon_system(section: ewon.Section) -> None:
    assert list(ewon.check_ewon("System", {"device": "oxyreduct"}, section)) == [
        Result(state=State.OK, summary="alarms: 0.00"),
        Result(state=State.OK, summary="incidents: 0.00"),
        Result(state=State.OK, summary="shutdown messages: 0.00"),
        Result(state=State.CRIT, summary="luminous field active"),
    ]
