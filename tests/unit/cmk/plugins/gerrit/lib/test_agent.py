#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.plugins.gerrit.lib import agent
from cmk.plugins.gerrit.lib.schema import VersionInfo


@pytest.fixture
def patch_storage_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


@pytest.mark.usefixtures("patch_storage_env")
def test_run_agent(capsys: pytest.CaptureFixture[str]) -> None:
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

    # cache is being used on second run.
    agent.run(ctx)
    assert captured.out == capsys.readouterr().out


@pytest.mark.usefixtures("patch_storage_env")
def test_run_agent_with_no_cache(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = agent.GerritRunContext(
        hostname="heute",
        ttl=agent.TTLCache(version=0),
        collectors=agent.Collectors(version=_FakeVersionCollector()),
    )

    agent.run(ctx)
    first_run_output = capsys.readouterr().out
    agent.run(ctx)
    second_run_output = capsys.readouterr().out

    assert first_run_output != second_run_output


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


class _VersionInfoFactory(TypedDictFactory[VersionInfo]):
    __check_model__ = False


class _FakeVersionCollector:
    def collect(self) -> VersionInfo:
        return _VersionInfoFactory.build()
