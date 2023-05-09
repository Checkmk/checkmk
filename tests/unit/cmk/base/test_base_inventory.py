#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
from typing import List, Union

import pytest

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.structured_data import StructuredDataTree

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


@pytest.mark.parametrize("failed_state, expected", [
    (None, 1),
    (0, 0),
    (1, 1),
    (2, 2),
    (3, 3),
])
def test_do_inv_check(monkeypatch, capsys, failed_state, expected):
    hostname = "my-host"
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    monkeypatch.setattr(
        inventory,
        "_do_active_inventory_for",
        lambda host_config, selected_sections, run_only_plugin_names: inventory.
        ActiveInventoryResult(
            trees=inventory.InventoryTrees(
                inventory=StructuredDataTree(),
                status_data=StructuredDataTree(),
            ),
            source_results=[],
            parsing_errors=[],
            safe_to_write=False,
        ),
    )

    monkeypatch.setattr(
        inventory,
        "_run_inventory_export_hooks",
        lambda h, i: None,
    )

    assert expected == inventory.do_inv_check(
        hostname, {} if failed_state is None else {"inv-fail-status": failed_state})

    cap_out_err = capsys.readouterr()
    assert "Cannot update tree" in cap_out_err.out
