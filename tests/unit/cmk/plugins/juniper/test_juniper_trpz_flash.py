#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.juniper.agent_based.juniper_trpz_flash import (
    check_juniper_trpz_flash,
    discover_juniper_trpz_flash,
    parse_juniper_trpz_flash,
    Section,
)


def test_parse_juniper_trpz_flash_returns_none_on_empty() -> None:
    assert parse_juniper_trpz_flash([]) is None


def test_parse_juniper_trpz_flash_returns_section() -> None:
    assert parse_juniper_trpz_flash([["51439616", "62900224"]]) == Section(
        used=51439616.0, total=62900224.0
    )


def test_discover_juniper_trpz_flash() -> None:
    assert list(discover_juniper_trpz_flash(Section(used=51439616.0, total=62900224.0))) == [
        Service()
    ]


def test_check_juniper_trpz_flash_ok() -> None:
    results = list(
        check_juniper_trpz_flash(
            {"levels": (90.0, 95.0)}, Section(used=51439616.0, total=62900224.0)
        )
    )
    assert results == [
        Result(state=State.OK, summary="Used: 49.1 MiB of 60.0 MiB "),
        Metric(
            "used",
            51439616.0,
            levels=(56610201.6, 59755212.8),
            boundaries=(0, 62900224.0),
        ),
    ]
