#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path, PurePosixPath

from cmk.diagnostics.internal import CollectContext, GeneratedContent, REDACT_STRING
from cmk.plugins.diagnostics.diagnostics.files import (
    diagnostics_plugin_config_files_high,
    diagnostics_plugin_config_files_low,
    diagnostics_plugin_config_files_medium,
    diagnostics_plugin_log_files_medium,
)


class _NullLogger:
    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        site_id="mySite",
        all_parameters={},
        base_config={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=_NullLogger(),
    )


def test_config_files_are_bucketed_by_sensitivity(tmp_path: Path) -> None:
    config_dir = tmp_path / "etc/check_mk"
    (config_dir / "conf.d/wato").mkdir(parents=True)
    # classified 'sensitive' by name -> medium bucket
    (config_dir / "conf.d/wato/global.mk").write_text("x = 1")
    # unclassified -> conservative high bucket
    (config_dir / "unclassified.conf").write_text("y = 2")

    context = _make_context(tmp_path)

    assert list(diagnostics_plugin_config_files_low.handler(context)) == []

    medium = {i.path: i.content for i in diagnostics_plugin_config_files_medium.handler(context)}
    assert set(medium) == {PurePosixPath("etc/check_mk/conf.d/wato/global.mk")}

    high = {i.path: i.content for i in diagnostics_plugin_config_files_high.handler(context)}
    assert set(high) == {PurePosixPath("etc/check_mk/unclassified.conf")}
    content = high[PurePosixPath("etc/check_mk/unclassified.conf")]
    assert isinstance(content, GeneratedContent)
    assert content.data == b"y = 2"


def test_config_files_are_redacted(tmp_path: Path) -> None:
    config_dir = tmp_path / "etc/check_mk/conf.d/wato"
    config_dir.mkdir(parents=True)
    (config_dir / "rules.mk").write_text(
        "{'id': '123', 'value': ('password', 'very_secret'), 'condition': {}},"
    )

    context = _make_context(tmp_path)
    items = {i.path: i.content for i in diagnostics_plugin_config_files_medium.handler(context)}

    content = items[PurePosixPath("etc/check_mk/conf.d/wato/rules.mk")]
    assert isinstance(content, GeneratedContent)
    assert b"very_secret" not in content.data
    assert REDACT_STRING.encode() in content.data


def test_log_files_content(tmp_path: Path) -> None:
    log_dir = tmp_path / "var/log"
    log_dir.mkdir(parents=True)
    (log_dir / "web.log").write_text("a log line")

    context = _make_context(tmp_path)
    items = {i.path: i.content for i in diagnostics_plugin_log_files_medium.handler(context)}

    content = items[PurePosixPath("var/log/web.log")]
    assert isinstance(content, GeneratedContent)
    assert content.data == b"a log line"
