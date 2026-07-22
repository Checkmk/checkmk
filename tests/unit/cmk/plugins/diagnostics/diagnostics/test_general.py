#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.diagnostics.internal import (
    CollectContext,
    CollectWarning,
    GeneratedContent,
    VerbatimCopy,
)
from cmk.inventory.structured_data import deserialize_tree, InventoryStore, make_meta
from cmk.plugins.diagnostics.diagnostics.general import (
    diagnostics_plugin_checkmk_overview,
    diagnostics_plugin_general_info,
    diagnostics_plugin_omd_config,
    diagnostics_plugin_parameters,
)


def _make_context(
    omd_root: Path,
    *,
    omd_config: Mapping[str, str] | None = None,
    checkmk_server_host: str = "checkmk_server",
) -> CollectContext:
    return CollectContext(
        omd_root=omd_root,
        omd_config=omd_config or {},
        all_parameters={"plugins": ["general_info"], "checkmk_server_host": ""},
        core_performance_settings={},
        resolve_checkmk_server_host=lambda: checkmk_server_host,
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=None,  # type: ignore[arg-type]  # not used
    )


def test_parameters_dumps_the_selection(tmp_path: Path) -> None:
    items = list(diagnostics_plugin_parameters.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname.name.startswith("parameters_")
    assert isinstance(content, GeneratedContent)
    assert b"general_info" in content.data


def test_general_info_content(tmp_path: Path) -> None:
    (tmp_path / "etc/omd").mkdir(parents=True)
    (tmp_path / "etc/omd/site.conf").write_text("CONFIG_CORE='cmc'\n")

    items = list(diagnostics_plugin_general_info.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("general.json")
    assert isinstance(content, GeneratedContent)

    info_keys = [
        "time",
        "time_human_readable",
        "os",
        "version",
        "edition",
        "core",
        "python_version",
        "python_paths",
        "arch",
    ]
    assert sorted(json.loads(content.data)) == sorted(info_keys)


def test_omd_config_content(tmp_path: Path) -> None:
    omd_config = {
        "CONFIG_ADMIN_MAIL": "",
        "CONFIG_APACHE_MODE": "own",
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
        "CONFIG_AUTOSTART": "off",
        "CONFIG_CORE": "cmc",
        "CONFIG_LIVEPROXYD": "on",
        "CONFIG_LIVESTATUS_TCP": "off",
        "CONFIG_MKEVENTD": "on",
        "CONFIG_MULTISITE_AUTHORISATION": "on",
        "CONFIG_MULTISITE_COOKIE_AUTH": "on",
        "CONFIG_NSCA": "off",
        "CONFIG_TMPFS": "on",
    }
    (tmp_path / "etc/omd").mkdir(parents=True)
    (tmp_path / "etc/omd/site.conf").write_text("CONFIG_CORE='cmc'\n")

    items = {
        i.path: i.content
        for i in diagnostics_plugin_omd_config.handler(
            _make_context(tmp_path, omd_config=omd_config)
        )
    }

    content = items[PurePosixPath("omd_config.json")]
    assert isinstance(content, GeneratedContent)
    assert json.loads(content.data) == omd_config

    copied = items[PurePosixPath("etc/omd/site.conf")]
    assert isinstance(copied, VerbatimCopy)
    assert copied.source == tmp_path / "etc/omd/site.conf"


def test_checkmk_overview_no_inventory_tree(tmp_path: Path) -> None:
    # A missing tree loads as an empty tree, so the node lookup reports the warning
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


def test_checkmk_overview_content(tmp_path: Path) -> None:
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

    items = list(
        diagnostics_plugin_checkmk_overview.handler(
            _make_context(tmp_path, checkmk_server_host="checkmk-server-name")
        )
    )

    assert len(items) == 1
    arcname, generated = items[0].path, items[0].content
    assert arcname == PurePosixPath("checkmk_overview")
    assert isinstance(generated, GeneratedContent)
    content = json.loads(generated.data)

    assert content["Nodes"]["cluster"]["Attributes"]["Pairs"] == {
        "is_cluster": False,
    }

    assert content["Nodes"]["sites"]["Table"]["Rows"] == [
        {
            "autostart": False,
            "site": "heute",
            "used_version": "2020.06.09.cee",
        },
    ]

    rows = content["Nodes"]["versions"]["Table"]["Rows"]
    assert len(rows) == 2
    for row in [
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
    ]:
        assert row in rows
