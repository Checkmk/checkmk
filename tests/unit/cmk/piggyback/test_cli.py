#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Set

import pytest
import time_machine

import cmk.utils.paths
from cmk.ccc.hostaddress import HostAddress
from cmk.piggyback.backend import store_piggyback_raw_data
from cmk.piggyback.cli import main

_REF_TIME = 1640000000


def _send(source: str, *piggybacked: str) -> None:
    store_piggyback_raw_data(
        HostAddress(source),
        {HostAddress(host): (b"<<<local>>>",) for host in piggybacked},
        message_timestamp=_REF_TIME,
        contact_timestamp=_REF_TIME,
        omd_root=cmk.utils.paths.omd_root,
    )


def _cannot_read_hosts() -> Set[str]:
    raise RuntimeError("cannot read hosts")


def test_list_sources_prints_sources_sorted(capsys: pytest.CaptureFixture[str]) -> None:
    _send("srcB", "vm1")
    _send("srcA", "vm1")

    exit_code = main(["list", "sources"])

    assert (exit_code, capsys.readouterr().out) == (0, "srcA srcB\n")


def test_list_piggybacked_prints_hosts_sorted(capsys: pytest.CaptureFixture[str]) -> None:
    _send("src", "vm2", "vm1")

    exit_code = main(["list", "piggybacked"])

    assert (exit_code, capsys.readouterr().out) == (0, "vm1 vm2\n")


def test_list_without_piggyback_data_prints_empty_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["list", "sources"])

    assert (exit_code, capsys.readouterr().out) == (0, "\n")


def test_list_orphans_prints_unmonitored_piggybacked_hosts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _send("src", "vm1", "vm2")

    exit_code = main(["list", "orphans"], get_monitored_hosts=lambda: {"vm1"})

    assert (exit_code, capsys.readouterr().out) == (0, "vm2\n")


def test_error_is_printed_and_exits_with_1(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["list", "orphans"], get_monitored_hosts=_cannot_read_hosts)

    assert (exit_code, capsys.readouterr().err) == (1, "cannot read hosts\n")


def test_debug_mode_raises_error_instead_of_printing_it() -> None:
    with pytest.raises(RuntimeError, match="cannot read hosts"):
        main(["--debug", "list", "orphans"], get_monitored_hosts=_cannot_read_hosts)


def test_create_sections_prints_one_section_per_host(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with time_machine.travel(_REF_TIME, tick=False):
        exit_code = main(["create-sections", "My service", "vm1", "vm2"])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        (
            "<<<<vm1>>>>\n"
            "<<<local>>>\n"
            '0 "My service" - Agent data created at 1640000000\n'
            "<<<<vm2>>>>\n"
            "<<<local>>>\n"
            '0 "My service" - Agent data created at 1640000000\n'
        ),
    )


def test_missing_command_prints_usage_and_exits_with_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == 2
    assert capsys.readouterr().err.startswith("usage: cmk-piggyback")
