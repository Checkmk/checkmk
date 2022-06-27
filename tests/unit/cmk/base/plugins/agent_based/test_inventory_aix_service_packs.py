#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_aix_service_packs import (
    inventory_aix_service_packs,
    parse_aix_service_packs,
)

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        (
            [],
            [
                Attributes(
                    path=["software", "os"],
                    inventory_attributes={"service_pack": None},
                ),
            ],
        ),
        (
            [
                ["----", "foo"],
                ["latest"],
                ["Known", "bar"],
                ["pack"],
            ],
            [
                Attributes(
                    path=["software", "os"],
                    inventory_attributes={"service_pack": "latest"},
                ),
                TableRow(
                    path=["software", "os", "service_packs"],
                    key_columns={"name": "pack"},
                ),
            ],
        ),
    ],
)
def test_inv_aix_baselevel(raw_section, expected_result) -> None:
    assert sort_inventory_result(
        inventory_aix_service_packs(parse_aix_service_packs(raw_section))
    ) == sort_inventory_result(expected_result)
