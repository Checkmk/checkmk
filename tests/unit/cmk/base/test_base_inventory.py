#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
from typing import List, Union

from cmk.base import inventory
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow


def test_aggregator_raises_collision():
    inventory_items: List[Union[Attributes, TableRow]] = [
        Attributes(path=["a", "b", "c"], status_attributes={"foo": "bar"}),
        TableRow(path=["a", "b", "c"], key_columns={"foo": "bar"}),
    ]

    result = inventory._TreeAggregator().aggregate_results(inventory_items)

    assert isinstance(result, TypeError)
    assert str(result) == (
        "Cannot create TableRow at path ['a', 'b', 'c']: this is a Attributes node.")
