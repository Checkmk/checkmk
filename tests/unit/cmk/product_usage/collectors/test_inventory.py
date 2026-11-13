#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest_mock import MockType

import cmk.product_usage.collectors.inventory as inventory_collector


def test_collect_counts_hosts_returned_by_livestatus(local_connection: MockType) -> None:
    local_connection.query.return_value = [["host1"], ["host2"]]

    assert inventory_collector.collect().hosts_with_inventory == 2


def test_collect_queries_hosts_with_inventory_data(local_connection: MockType) -> None:
    local_connection.query.return_value = []

    inventory_collector.collect()

    query = local_connection.query.call_args.args[0]
    assert "Filter: mk_inventory_last > 0" in str(query)
    assert query.supports_json_format()
