#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.diagnostics.internal import CollectContext, GeneratedContent
from cmk.plugins.diagnostics.diagnostics.general import (
    diagnostics_plugin_parameters,
)


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        all_parameters={"plugins": ["general_info"], "checkmk_server_host": ""},
        core_performance_settings={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
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
