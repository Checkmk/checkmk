#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    GeneratedContent,
    VerbatimCopy,
)
from cmk.plugins.diagnostics.diagnostics.general import (
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
        site_id="mySite",
        all_parameters={"plugins": ["general_info"], "checkmk_server_host": ""},
        base_config={},
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
