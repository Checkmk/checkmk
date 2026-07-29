#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable
from pathlib import PurePosixPath

from cmk.ccc.hostaddress import HostName
from cmk.diagnostics.internal import (
    CollectContext,
    CollectError,
    CollectWarning,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
    Topic,
)
from cmk.inventory.structured_data import InventoryStore, SDNodeName, serialize_tree

# Shared with the diagnostics plugin family; topics compare by value.
_TOPIC_GENERAL = Topic("General site information")


def _collect_checkmk_overview(context: CollectContext) -> Iterable[DumpItem]:
    checkmk_server_host = HostName(context.resolve_checkmk_server_host())
    try:
        tree = InventoryStore(context.omd_root).load_inventory_tree(host_name=checkmk_server_host)
    except FileNotFoundError as e:
        raise CollectError("No HW/SW Inventory tree of '%s' found" % checkmk_server_host) from e

    if not (
        node := tree.get_tree(
            (
                SDNodeName("software"),
                SDNodeName("applications"),
                SDNodeName("check_mk"),
            )
        )
    ):
        raise CollectWarning("No HW/SW Inventory node 'Software > Applications > Checkmk'")

    yield DumpItem(
        PurePosixPath("checkmk_overview"),
        GeneratedContent(json.dumps(serialize_tree(node), sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_checkmk_overview = DiagnosticsPlugin(
    name="checkmk_overview",
    description=Help(
        "HW/SW Inventory node 'Software > Applications > Checkmk' of the Checkmk server"
    ),
    sensitivity=Sensitivity.LOW,
    topic=_TOPIC_GENERAL,
    handler=_collect_checkmk_overview,
)
