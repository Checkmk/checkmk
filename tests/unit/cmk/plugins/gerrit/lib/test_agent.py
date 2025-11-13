#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import argparse

import pytest

from cmk.plugins.gerrit.lib import agent


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


def test_write_version_section(capsys: pytest.CaptureFixture) -> None:
    section = {
        "current": "1.2.3",
        "latest": {"major": None, "minor": "1.3.4", "patch": "1.2.5"},
    }
    agent._write_section(section, name="gerrit_version")

    value = capsys.readouterr().out
    expected = """\
<<<gerrit_version:sep(0)>>>
{"current": "1.2.3", "latest": {"major": null, "minor": "1.3.4", "patch": "1.2.5"}}
"""

    assert value == expected
