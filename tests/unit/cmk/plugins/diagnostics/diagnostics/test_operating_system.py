#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path, PurePosixPath

import pytest

from cmk.diagnostics.internal import CollectContext, GeneratedContent
from cmk.plugins.diagnostics.diagnostics.operating_system import (
    diagnostics_plugin_environment_variables,
)


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        all_parameters={},
        core_performance_settings={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=None,  # type: ignore[arg-type]  # not used
    )


def test_environment_variables_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment_vars = {"France": "Paris", "Italy": "Rome", "Germany": "Berlin"}
    with monkeypatch.context() as m:
        for key, value in environment_vars.items():
            m.setenv(key, value)

        items = list(diagnostics_plugin_environment_variables.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("environment.json")
    assert isinstance(content, GeneratedContent)
    parsed = json.loads(content.data)
    for key, value in environment_vars.items():
        assert parsed[key] == value
