#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path, PurePosixPath

from cmk.diagnostics.internal import CollectContext
from cmk.plugins.flags.diagnostics.experimental_flags import (
    diagnostics_plugin_experimental_flags,
)


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        site_id="mySite",
        all_parameters={},
        base_config={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=None,  # type: ignore[arg-type]  # not used
    )


def test_collects_existing_flag_files(tmp_path: Path) -> None:
    config_dir = tmp_path / "etc/check_mk"
    config_dir.mkdir(parents=True)
    (config_dir / "release_flag.json").write_text("{}")

    items = list(diagnostics_plugin_experimental_flags.handler(_make_context(tmp_path)))

    assert [i.path for i in items] == [PurePosixPath("etc/check_mk/release_flag.json")]
