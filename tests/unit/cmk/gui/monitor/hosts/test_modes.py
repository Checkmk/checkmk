#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.hosts._api._modes import build_host_modes

from .testlib import HostFactory


def test_build_host_modes_none() -> None:
    host = HostFactory.build(in_downtime=False, acknowledged=False)
    assert build_host_modes(host) == []


def test_build_host_modes_downtime() -> None:
    host = HostFactory.build(in_downtime=True, acknowledged=False)
    modes = build_host_modes(host)

    assert [mode.icon_name for mode in modes] == ["downtime"]
    assert modes[0].link.startswith("view.py?")
    assert "downtimes_of_host" in modes[0].link


def test_build_host_modes_acknowledged() -> None:
    host = HostFactory.build(in_downtime=False, acknowledged=True)

    assert [mode.icon_name for mode in build_host_modes(host)] == ["ack"]


def test_build_host_modes_downtime_and_acknowledged() -> None:
    host = HostFactory.build(in_downtime=True, acknowledged=True)

    assert [mode.icon_name for mode in build_host_modes(host)] == ["downtime", "ack"]
