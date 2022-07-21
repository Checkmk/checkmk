#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.base.plugins.agent_based import brocade_fcport as bf
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

STRING_TABLE_INDEX_1_MISSING = [
    [
        [
            "45",
            "6",
            "1",
            "1",
            "2905743640",
            "886676077",
            "925307562",
            "12463206",
            "3618162349",
            "0",
            "0",
            "0",
            "0",
            "",
            "port44",
        ],
        [
            "46",
            "6",
            "1",
            "1",
            "3419046246",
            "972264932",
            "3137901401",
            "544788281",
            "569031932",
            "0",
            "0",
            "0",
            "82",
            "",
            "port45",
        ],
        [
            "47",
            "6",
            "1",
            "1",
            "1111764110",
            "2429196329",
            "4259150384",
            "1651642909",
            "569031932",
            "0",
            "0",
            "0",
            "6",
            "",
            "port46",
        ],
        [
            "48",
            "6",
            "1",
            "1",
            "1832010527",
            "3916222665",
            "596751007",
            "1430959330",
            "3618162349",
            "0",
            "0",
            "0",
            "0",
            "",
            "port47",
        ],
    ],
    [["45", "512"], ["46", "512"], ["47", "512"], ["48", "512"]],
    [
        ["805306369", "6", "100"],
        ["805306370", "24", "0"],
        ["805306371", "131", "0"],
        ["805306372", "1", "0"],
        ["805306373", "1", "0"],
        ["805306374", "1", "0"],
        ["805306375", "1", "0"],
        ["805306376", "1", "0"],
        ["805306377", "1", "0"],
        ["805306378", "1", "0"],
        ["1073741868", "56", "16000"],
        ["1073741869", "56", "16000"],
        ["1073741870", "56", "16000"],
        ["1073741871", "56", "16000"],
    ],
    [],
]


@pytest.fixture(name="section_idx", scope="module")
def _get_section_idx() -> bf.Section:
    section = bf.parse_brocade_fcport(STRING_TABLE_INDEX_1_MISSING)
    assert section is not None
    return section


def test_discovery_idx(section_idx: bf.Section) -> None:
    assert sorted(
        bf.discover_brocade_fcport(
            {
                "admstates": [1],
                "phystates": [6],
                "opstates": [1],
                "show_isl": True,
                "use_portname": True,
            },
            section_idx,
        )
    ) == sorted(
        [
            Service(
                item="44 ISL port44", parameters={"phystate": [6], "opstate": [1], "admstate": [1]}
            ),
            Service(
                item="45 ISL port45", parameters={"phystate": [6], "opstate": [1], "admstate": [1]}
            ),
            Service(
                item="46 ISL port46", parameters={"phystate": [6], "opstate": [1], "admstate": [1]}
            ),
            Service(
                item="47 ISL port47", parameters={"phystate": [6], "opstate": [1], "admstate": [1]}
            ),
        ]
    )


def test_check(section_idx: bf.Section) -> None:
    assert list(
        bf._check_brocade_fcport(
            "44 ISL port44",
            {
                "assumed_speed": 2.0,
                "phystate": [6],
                "notxcredits": (3.0, 20.0),
                "opstate": [1],
                "c3discards": (3.0, 20.0),
                "admstate": [1],
                "rxencinframes": (3.0, 20.0),
                "rxcrcs": (3.0, 20.0),
                "rxencoutframes": (3.0, 20.0),
            },
            section_idx,
            1658523186,
            {
                "rxwords.45": (1658523126, 0),
                "txwords.45": (1658523126, 0),
                "rxframes.45": (1658523126, 0),
                "txframes.45": (1658523126, 0),
                "rxcrcs.45": (1658523126, 0),
                "txcrcs.45": (1658523126, 0),
                "rxencoutframes.45": (1658523126, 0),
                "txencoutframes.45": (1658523126, 0),
                "rxencinframes.45": (1658523126, 0),
                "txencinframes.45": (1658523126, 0),
                "c3discards.45": (1658523126, 0),
                "notxcredits.45": (1658523126, 0),
            },
        )
    ) == [
        Result(
            state=State.CRIT,
            summary=(
                "ISL speed: 16 Gbit/s, In: 59.1 MB/s, Out: 194 MB/s, "
                "No TX buffer credits: 79.63%(!!), Physical: in sync, "
                "Operational: online, Administrative: online"
            ),
        ),
        Metric("in", 59111738.46666667, boundaries=(0.0, 1600000000.0)),
        Metric("out", 193716242.66666666, boundaries=(0.0, 1600000000.0)),
        Metric("rxframes", 207720.1),
        Metric("txframes", 15421792.7),
        Metric("rxcrcs", 0.0),
        Metric("rxencoutframes", 0.0),
        Metric("rxencinframes", 0.0),
        Metric("c3discards", 0.0),
        Metric("notxcredits", 60302705.81666667),
    ]
