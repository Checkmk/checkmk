#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path, PurePosixPath

import pytest

from cmk.diagnostics.internal import CollectContext, CollectInfo, VerbatimCopy
from cmk.plugins.diagnostics.diagnostics.performance import (
    diagnostics_plugin_gui_profiles,
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


def test_gui_profiles_packs_stored_profiles(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "var/check_mk/profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "20260101_120000_abcdefabcdef.profile").write_bytes(b"prof")
    (profiles_dir / "20260101_120000_abcdefabcdef.json").write_text("{}")
    # not a valid profile id -> skipped
    (profiles_dir / "readme.txt").write_text("nope")

    items = {
        i.path: i.content for i in diagnostics_plugin_gui_profiles.handler(_make_context(tmp_path))
    }

    assert set(items) == {
        PurePosixPath("var/check_mk/profiles/20260101_120000_abcdefabcdef.profile"),
        PurePosixPath("var/check_mk/profiles/20260101_120000_abcdefabcdef.json"),
    }
    assert all(isinstance(item, VerbatimCopy) for item in items.values())


def test_gui_profiles_reports_when_empty(tmp_path: Path) -> None:
    with pytest.raises(CollectInfo, match="No profiles found"):
        list(diagnostics_plugin_gui_profiles.handler(_make_context(tmp_path)))
