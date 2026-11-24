#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.diagnostics.internal import (
    CollectContext,
    CollectWarning,
    DumpItem,
    GeneratedContent,
)
from cmk.inventory.serialization import deserialize_tree, make_meta
from cmk.inventory.store import InventoryStore
from cmk.plugins.inventory.diagnostics.checkmk_overview import (
    diagnostics_plugin_checkmk_overview,
)

from ._logger import null_logger


def _make_context(
    omd_root: Path,
    *,
    omd_config: Mapping[str, str] | None = None,
    checkmk_server_host: str = "checkmk_server",
) -> CollectContext:
    return CollectContext(
        omd_root=omd_root,
        omd_config=omd_config or {},
        site_id="mySite",
        all_parameters={"plugins": ["general_info"], "checkmk_server_host": ""},
        base_config={},
        resolve_checkmk_server_host=lambda: checkmk_server_host,
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=null_logger(),
    )


def test_checkmk_overview_no_inventory_tree(tmp_path: Path) -> None:
    with pytest.raises(
        CollectWarning, match="No HW/SW Inventory node 'Software > Applications > Checkmk'"
    ):
        list(
            diagnostics_plugin_checkmk_overview.handler(
                _make_context(tmp_path, checkmk_server_host="checkmk-server-name")
            )
        )


def test_checkmk_overview_no_checkmk_node(tmp_path: Path) -> None:
    InventoryStore(tmp_path).save_inventory_tree(
        host_name=HostName("checkmk-server-name"),
        tree=deserialize_tree(
            {
                "hardware": {},
                "networking": {},
                "software": {
                    "applications": {},
                },
            }
        ),
        meta=make_meta(do_archive=False),
    )

    with pytest.raises(
        CollectWarning, match="No HW/SW Inventory node 'Software > Applications > Checkmk'"
    ):
        list(
            diagnostics_plugin_checkmk_overview.handler(
                _make_context(tmp_path, checkmk_server_host="checkmk-server-name")
            )
        )


def _overview_items(tmp_path: Path) -> Sequence[DumpItem]:
    InventoryStore(tmp_path).save_inventory_tree(
        host_name=HostName("checkmk-server-name"),
        tree=deserialize_tree(
            {
                "hardware": {},
                "networking": {},
                "software": {
                    "applications": {
                        "check_mk": {
                            "versions": [
                                {
                                    "version": "2020.06.07.cee",
                                    "number": "2020.06.07",
                                    "edition": "cee",
                                    "demo": False,
                                    "num_sites": 0,
                                },
                                {
                                    "version": "2020.06.09.cee",
                                    "number": "2020.06.09",
                                    "edition": "cee",
                                    "demo": False,
                                    "num_sites": 1,
                                },
                            ],
                            "sites": [
                                {
                                    "site": "heute",
                                    "used_version": "2020.06.09.cee",
                                    "autostart": False,
                                }
                            ],
                            "cluster": {"is_cluster": False},
                            "agent_version": "1.7.0i1",
                            "num_versions": 2,
                            "num_sites": 1,
                        }
                    }
                },
            }
        ),
        meta=make_meta(do_archive=False),
    )

    return list(
        diagnostics_plugin_checkmk_overview.handler(
            _make_context(tmp_path, checkmk_server_host="checkmk-server-name")
        )
    )


def _overview_content(item: DumpItem) -> object:
    if not isinstance(item.content, GeneratedContent):
        raise TypeError(item.content)
    return json.loads(item.content.data)


def test_checkmk_overview_dumps_one_file(tmp_path: Path) -> None:
    assert [item.path for item in _overview_items(tmp_path)] == [PurePosixPath("checkmk_overview")]


def test_checkmk_overview_dumps_the_checkmk_node(tmp_path: Path) -> None:
    assert _overview_content(_overview_items(tmp_path)[0]) == {
        "Attributes": {
            "Pairs": {"agent_version": "1.7.0i1", "num_sites": 1, "num_versions": 2},
        },
        "Table": {},
        "Nodes": {
            "cluster": {
                "Attributes": {"Pairs": {"is_cluster": False}},
                "Table": {},
                "Nodes": {},
            },
            "sites": {
                "Attributes": {},
                "Table": {
                    "KeyColumns": ["autostart", "site", "used_version"],
                    "Rows": [
                        {"autostart": False, "site": "heute", "used_version": "2020.06.09.cee"}
                    ],
                },
                "Nodes": {},
            },
            "versions": {
                "Attributes": {},
                "Table": {
                    "KeyColumns": ["demo", "edition", "num_sites", "number", "version"],
                    "Rows": [
                        {
                            "demo": False,
                            "edition": "cee",
                            "num_sites": 0,
                            "number": "2020.06.07",
                            "version": "2020.06.07.cee",
                        },
                        {
                            "demo": False,
                            "edition": "cee",
                            "num_sites": 1,
                            "number": "2020.06.09",
                            "version": "2020.06.09.cee",
                        },
                    ],
                },
                "Nodes": {},
            },
        },
    }
