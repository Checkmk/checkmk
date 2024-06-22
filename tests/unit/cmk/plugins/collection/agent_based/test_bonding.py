#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v1 import Result, State
from cmk.agent_based.v1.type_defs import CheckResult
from cmk.plugins.collection.agent_based.bonding import _check_ieee_302_3ad_specific
from cmk.plugins.lib.bonding import Bond


@pytest.mark.parametrize(
    "params, status, result",
    [
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "aggregator_id": "1",
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "1",
                    },
                },
            },
            [],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "aggregator_id": "1",
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "2",
                    },
                },
            },
            [
                Result(state=State.WARN, summary="Mismatching aggregator ID of ens1f1: 2"),
            ],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "1",
                    },
                },
            },
            [],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 2},
            {
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "2",
                    },
                },
            },
            [
                Result(state=State.CRIT, summary="Mismatching aggregator ID of ens1f1: 2"),
            ],
        ),
    ],
)
def test_check_ieee_302_3ad_specific(
    params: Mapping[str, object], status: Bond, result: CheckResult
) -> None:
    assert list(_check_ieee_302_3ad_specific(params, status)) == result
