#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.ibm_mq_queues import inventory_ibm_mq_queues

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "parsed, expected_result",
    [
        ({}, []),
        (
            {
                "a2:b2": {
                    "MAXDEPTH": "maxdepth",
                    "MAXMSGL": "maxmsgl",
                    "CRDATE": "crdate",
                    "CRTIME": "cr.time",
                    "ALTDATE": "altdate",
                    "ALTTIME": "alt.time",
                    "MONQ": "monq",
                },
                "a1:b1": {
                    "MAXDEPTH": "maxdepth",
                },
                "a": {
                    "MAXDEPTH": "maxdepth",
                },
            },
            [
                TableRow(
                    path=["software", "applications", "ibm_mq", "queues"],
                    key_columns={
                        "qmgr": "a1",
                        "name": "b1",
                    },
                    inventory_columns={
                        "maxdepth": "maxdepth",
                        "maxmsgl": "n/a",
                        "created": "n/a",
                        "altered": "n/a",
                        "monq": "n/a",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "ibm_mq", "queues"],
                    key_columns={
                        "qmgr": "a2",
                        "name": "b2",
                    },
                    inventory_columns={
                        "maxdepth": "maxdepth",
                        "maxmsgl": "maxmsgl",
                        "created": "crdate cr:time",
                        "altered": "altdate alt:time",
                        "monq": "monq",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_ibm_mq_queues(parsed, expected_result):
    assert sort_inventory_result(inventory_ibm_mq_queues(parsed)) == sort_inventory_result(
        expected_result
    )
