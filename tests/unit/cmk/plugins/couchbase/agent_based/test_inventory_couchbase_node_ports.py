#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes
from cmk.plugins.couchbase.agent_based.inventory_couchbase_node_ports import (
    inventorize_couchbase_nodes_ports,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines


def test_node_name_is_sanitized_into_inventory_path() -> None:
    section = parse_couchbase_lines(
        [['{"name": "10.0.0.1:8091", "ports": {"direct": 11210, "httpsMgmt": 18091}}']]
    )

    assert list(inventorize_couchbase_nodes_ports(section)) == [
        Attributes(
            path=["software", "applications", "couchbase", "nodes", "10-0-0-1-8091", "ports"],
            inventory_attributes={"direct": 11210, "httpsMgmt": 18091},
        )
    ]
