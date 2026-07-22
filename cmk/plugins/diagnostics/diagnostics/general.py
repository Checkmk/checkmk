#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import platform
from collections.abc import Iterable
from datetime import datetime
from pathlib import PurePosixPath

import cmk.ccc.version as cmk_version
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
)
from cmk.inventory.structured_data import InventoryStore, SDNodeName, serialize_tree
from cmk.plugins.diagnostics.lib.files import walk_verbatim
from cmk.plugins.diagnostics.lib.topics import TOPIC_GENERAL


def _collect_parameters(context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("parameters_%s" % datetime.now().timestamp()),
        GeneratedContent(str(dict(context.all_parameters)).encode()),
    )


diagnostics_plugin_parameters = DiagnosticsPlugin(
    name="parameters",
    description=Help("The parameters this diagnostics dump was created with"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_GENERAL,
    always=True,
    handler=_collect_parameters,
)


def _collect_general_info(context: CollectContext) -> Iterable[DumpItem]:
    version_infos = cmk_version.get_general_version_infos(context.omd_root)
    time_obj = datetime.fromtimestamp(version_infos.get("time", 0.0))
    yield DumpItem(
        PurePosixPath("general.json"),
        GeneratedContent(
            json.dumps(
                {
                    "arch": platform.machine(),
                    "time_human_readable": time_obj.isoformat(sep=" "),
                    "time": version_infos["time"],
                    "os": version_infos["os"],
                    "version": version_infos["version"],
                    "edition": version_infos["edition"],
                    "core": version_infos["core"],
                    "python_version": version_infos["python_version"],
                    "python_paths": list(version_infos["python_paths"]),
                },
                sort_keys=True,
                indent=4,
            ).encode()
        ),
    )


diagnostics_plugin_general_info = DiagnosticsPlugin(
    name="general_info",
    description=Help(
        "OS, Checkmk version and edition, Time, Core, Python version and paths, Architecture"
    ),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_GENERAL,
    always=True,
    handler=_collect_general_info,
)


def _collect_omd_config(context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("omd_config.json"),
        GeneratedContent(json.dumps(dict(context.omd_config), sort_keys=True, indent=4).encode()),
    )
    yield from walk_verbatim(context.omd_root / "etc/omd", PurePosixPath("etc/omd"))


diagnostics_plugin_omd_config = DiagnosticsPlugin(
    name="omd_config",
    description=Help("The OMD site configuration ('omd config show') and the files below etc/omd"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_GENERAL,
    handler=_collect_omd_config,
)


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
    topic=TOPIC_GENERAL,
    handler=_collect_checkmk_overview,
)
