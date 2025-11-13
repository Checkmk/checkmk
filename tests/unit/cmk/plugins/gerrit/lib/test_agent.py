#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

import pytest

from cmk.plugins.gerrit.lib import agent
from cmk.plugins.gerrit.lib.schema import VersionInfo


@pytest.fixture(autouse=True)
def patch_storage_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


@pytest.mark.usefixtures("patch_storage_env")
def test_run_agent(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    ctx = agent.GerritRunContext(
        hostname="heute",
        ttl=agent.TTLCache(version=60),
        collectors=agent.Collectors(version=_FakeVersionCollector()),
    )
    agent.run(ctx)
    captured = capsys.readouterr()

    # agent ran without error
    assert captured.err == ""

    # sections headings were successfully written out.
    assert "<<<gerrit_version:sep(0)>>>" in captured.out

    # cache was succesfully written out.
    assert any((tmp_path / "heute/gerrit_version").iterdir())


def test_parse_arguments() -> None:
    argv = ["--user", "abc", "--password-id", "foo:bar", "review.gerrit.com"]

    value = agent.parse_arguments(argv)
    expected = argparse.Namespace(
        debug=False,
        verbose=0,
        vcrtrace=False,
        user="abc",
        password_id="foo:bar",
        password=None,
        version_cache=28800.0,
        proto="https",
        port=443,
        hostname="review.gerrit.com",
    )

    assert value == expected


class _FakeVersionCollector:
    def collect(self) -> VersionInfo:
        return {
            "current": "1.2.3",
            "latest": {"major": "2.0.0", "minor": "1.3.0", "patch": "1.2.4"},
        }
