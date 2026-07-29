#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
import tarfile
import uuid
from pathlib import Path, PurePosixPath

from cmk.crash import make_crash_report_base_path
from cmk.diagnostics.internal import CollectContext, GeneratedContent
from cmk.plugins.crash.diagnostics.crash_reports import (
    diagnostics_plugin_latest_crash_reports,
)


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        all_parameters={},
        base_config={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=None,  # type: ignore[arg-type]  # not used
    )


def test_latest_crash_reports_content(tmp_path: Path) -> None:
    test_uuid = str(uuid.uuid4())
    category = "checks"
    test_crash_dir = make_crash_report_base_path(tmp_path) / category / test_uuid
    test_crash_dir.mkdir(parents=True, exist_ok=True)
    (test_crash_dir / "info.json").write_text('{ "testvar": "testvalue"}')

    items = list(diagnostics_plugin_latest_crash_reports.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath(f"var/check_mk/crashes/{category}/{test_uuid}.tar.gz")
    assert isinstance(content, GeneratedContent)

    with tarfile.open(fileobj=io.BytesIO(content.data), mode="r:gz") as tar:
        tar.extractall(path=tmp_path / "extracted", filter="data")
    extracted = (tmp_path / "extracted/info.json").read_text()
    assert json.loads(extracted)["testvar"] == "testvalue"


def test_latest_crash_reports_empty(tmp_path: Path) -> None:
    assert list(diagnostics_plugin_latest_crash_reports.handler(_make_context(tmp_path))) == []
