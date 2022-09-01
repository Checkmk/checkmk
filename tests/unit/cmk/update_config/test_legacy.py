#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import io
import sys
from pathlib import Path

import pytest

import cmk.utils.log
import cmk.utils.paths

import cmk.gui.config
from cmk.gui.watolib.audit_log import AuditLogStore

import cmk.update_config.legacy as update_config


@pytest.fixture(name="uc")
def fixture_uc() -> update_config.UpdateConfig:
    return update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_parse_arguments_defaults() -> None:
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose() -> None:
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug() -> None:
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init() -> None:
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def mock_run() -> int:
    sys.stdout.write("XYZ\n")
    return 0


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: mock_run())
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()


def test_cleanup_version_specific_caches_missing_directory(uc: update_config.UpdateConfig) -> None:
    uc._cleanup_version_specific_caches()


def test_cleanup_version_specific_caches(uc: update_config.UpdateConfig) -> None:
    paths = [
        Path(cmk.utils.paths.include_cache_dir, "builtin"),
        Path(cmk.utils.paths.include_cache_dir, "local"),
        Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
        Path(cmk.utils.paths.precompiled_checks_dir, "local"),
    ]
    for base_dir in paths:
        base_dir.mkdir(parents=True, exist_ok=True)
        cached_file = base_dir / "if"
        with cached_file.open("w", encoding="utf-8") as f:
            f.write("\n")
        uc._cleanup_version_specific_caches()
        assert not cached_file.exists()
        assert base_dir.exists()


@pytest.fixture(name="old_path")
def fixture_old_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "audit.log")


@pytest.fixture(name="new_path")
def fixture_new_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "wato_audit.log")


@pytest.fixture(name="old_audit_log")
def fixture_old_audit_log(old_path: Path) -> Path:
    old_path.parent.mkdir(exist_ok=True, parents=True)
    with old_path.open("w") as f:
        f.write(
            """
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604992040 :heute2 cmkadmin create-host Created new host heute2.
1604992159 :heute2 cmkadmin delete-host Deleted host heute2
1604992163 :heute1 cmkadmin create-host Created new host heute1.
1604992166 :heute12 cmkadmin create-host Created new host heute12.
"""
        )
    return old_path


def mock_audit_log_entry(action: str, diff_text: str) -> AuditLogStore.Entry:
    return AuditLogStore.Entry(
        time=0, object_ref=None, user_id="", action=action, text="", diff_text=diff_text
    )
