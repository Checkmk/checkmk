#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.special_agents.bi import MultisiteBiDatasource


@pytest.fixture(scope="function")
def _bi_datasource_parameters():
    # parameter format introduced with 2.0.0p9
    return {
        "site": "local",
        "credentials": "automation",
        "filter": {"aggr_name": ["Host admin-pc"], "aggr_group_prefix": ["Hosts"]},
    }


@pytest.mark.parametrize(
    "value",
    [
        (
            # filter keys till 2.0.0p8
            {
                "site": "local",
                "credentials": "automation",
                "filter": {"aggr_name_regex": ["Host admin-pc"], "aggr_groups": ["Hosts"]},
            }
        ),
        (
            {
                # filter keys from 2.0.0p9
                "site": "local",
                "credentials": "automation",
                "filter": {"aggr_name": ["Host admin-pc"], "aggr_group_prefix": ["Hosts"]},
            }
        ),
    ],
)
def test_bi_datasource_parameters(value, _bi_datasource_parameters):
    assert (
        MultisiteBiDatasource().get_valuespec().transform_value(value) == _bi_datasource_parameters
    )
