#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any as HopeForTheBestForNow

import pytest

from tests.testlib import on_time

from tests.unit.checks.checktestlib import mock_item_state

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.plugin_contexts
from cmk.base.config import CEEConfigCache as Cache
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

Section = HopeForTheBestForNow


STRING_TABLE = [
    ["WWID", "  0x5000cca00b045e9c"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk4"],
    ["Bytes read                                       ", " 16375049"],
    ["Bytes written                                    ", " 571040768"],
    ["Total I/Os processed                             ", " 870553"],
    ["I/O failures                                     ", " 0"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x5000c50013801e7f"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk5"],
    ["Bytes read                                       ", " 229698466718"],
    ["Bytes written                                    ", " 458434521088"],
    ["Total I/Os processed                             ", " 67841911"],
    ["I/O failures                                     ", " 0"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d447456346450776b4c67"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk20"],
    ["Bytes read                                       ", " 66875865358"],
    ["Bytes written                                    ", " 27759884288"],
    ["Total I/Os processed                             ", " 6483391"],
    ["I/O failures                                     ", " 18"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d44745634645077717449"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk21"],
    ["Bytes read                                       ", " 2760640735497"],
    ["Bytes written                                    ", " 549730951168"],
    ["Total I/Os processed                             ", " 68172495"],
    ["I/O failures                                     ", " 33"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d447456346450774a6948"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk22"],
    ["Bytes read                                       ", " 2859709547785"],
    ["Bytes written                                    ", " 514804342784"],
    ["Total I/Os processed                             ", " 84900754"],
    ["I/O failures                                     ", " 37"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d44745634645077625679"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk23"],
    ["Bytes read                                       ", " 251929835785"],
    ["Bytes written                                    ", " 171925457920"],
    ["Total I/Os processed                             ", " 23209476"],
    ["I/O failures                                     ", " 24"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
]


check_name = "hpux_lunstats"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse(fix_register):
    return fix_register.agent_sections[SectionName(check_name)].parse_function


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


@pytest.fixture(scope="module", name="section")
def _get_section(parse_hpux_lunstats) -> Section:
    return parse_hpux_lunstats(STRING_TABLE)


def test_discover_default(monkeypatch, discover_hpux_lunstats, section: Section) -> None:
    monkeypatch.setattr(Cache, "host_extra_conf", lambda *a: [])
    monkeypatch.setattr(cmk.base.plugin_contexts, "_hostname", "moo")

    assert list(discover_hpux_lunstats(section)) == [
        Service(item="SUMMARY"),
    ]


def test_discover_physical(monkeypatch, discover_hpux_lunstats, section: Section) -> None:
    monkeypatch.setattr(Cache, "host_extra_conf", lambda *a: [["physical"]])
    monkeypatch.setattr(cmk.base.plugin_contexts, "_hostname", "moo")

    assert list(discover_hpux_lunstats(section)) == [
        Service(item="/dev/rdisk/disk4"),
        Service(item="/dev/rdisk/disk5"),
        Service(item="/dev/rdisk/disk20"),
        Service(item="/dev/rdisk/disk21"),
        Service(item="/dev/rdisk/disk22"),
        Service(item="/dev/rdisk/disk23"),
    ]


def test_check_hpux_lunstats_not_found(check_hpux_lunstats, section: Section) -> None:
    assert list(check_hpux_lunstats("möööööööp", {}, section)) == [
        Result(
            state=State.UNKNOWN,
            summary="No matching disk found",
        )
    ]


def test_check_hpux_lunstats_summary(check_hpux_lunstats, section: Section) -> None:
    with mock_item_state(
        {
            "diskstat.SUMMARY.write": (1659105408, 3360676168),
            "diskstat.SUMMARY.read": (1659105408, 12040575829),
        }
    ), on_time(1659105468, "UTC"):
        assert list(check_hpux_lunstats("SUMMARY", {}, section)) == [
            Result(
                state=State.OK,
                summary="read: 68.3 MB/s, write: 42.7 MB/s",
            ),
            Metric("read", 68266666.66666667),
            Metric("write", 42666666.666666664),
        ]


def test_check_hpux_lunstats(check_hpux_lunstats, section: Section) -> None:
    read_test_data = 2760640735497
    write_test_data = 549730951168
    item = "/dev/rdisk/disk21"

    # just to make sure this is what we're talking about:
    assert {i: (r, w) for _none, i, r, w in section}[item] == (
        read_test_data // 512,
        write_test_data // 512,
    )

    now = 1659105468
    with mock_item_state(
        {
            # surely one of these will result in a nice reported value?
            f"diskstat.{item}.write": (now - 60, (write_test_data - 1000**2 * 60) / 512),
            f"diskstat.{item}.read": (now - 60, (read_test_data - 1024**2 * 60) / 512),
        }
    ), on_time(now, "UTC"):
        assert list(check_hpux_lunstats(item, {}, section)) == [
            Result(
                state=State.OK,
                summary="read: 1.05 MB/s, write: 1.00 MB/s",
            ),
            Metric("read", 1048571.5833333334),
            Metric("write", 1000000.0),
        ]
