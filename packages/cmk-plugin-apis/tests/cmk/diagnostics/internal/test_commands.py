#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path, PurePosixPath

import pytest

from cmk.diagnostics.internal import (
    collect_command_output,
    CollectContext,
    CollectError,
    CollectInfo,
    GeneratedContent,
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


def test_collect_command_output(tmp_path: Path) -> None:
    items = list(collect_command_output(_make_context(tmp_path), "echo", ".out", ["echo", "hi"]))
    assert items[0].path == PurePosixPath("command_echo.out")
    assert items[0].content == GeneratedContent(b"hi\n")


def test_collect_command_output_unavailable(tmp_path: Path) -> None:
    with pytest.raises(CollectInfo, match="not available"):
        list(collect_command_output(_make_context(tmp_path), "x", ".out", ["/no/such/binary"]))


def test_collect_command_output_failure(tmp_path: Path) -> None:
    with pytest.raises(CollectError, match="unexpected error"):
        list(collect_command_output(_make_context(tmp_path), "false", ".out", ["false"]))
