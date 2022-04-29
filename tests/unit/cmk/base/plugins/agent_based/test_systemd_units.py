#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import timedelta
from typing import Sequence

import pytest

from cmk.base.api.agent_based.checking_classes import Result, Service, State
from cmk.base.plugins.agent_based.systemd_units import (
    _services_split,
    check_systemd_units_services,
    check_systemd_units_services_summary,
    discovery_systemd_units_services,
    discovery_systemd_units_services_summary,
    parse,
    Section,
    UnitEntry,
)


@pytest.mark.parametrize(
    "services, blacklist, expected",
    [
        (
            [
                UnitEntry(
                    name="gpu-manager",
                    loaded_status="loaded",
                    active_status="inactive",
                    current_state="dead",
                    description="Detect the available GPUs and deal with any system changes",
                    enabled_status="unknown",
                ),
                UnitEntry(
                    name="rsyslog",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="running",
                    description="System Logging Service",
                    enabled_status="enabled",
                ),
                UnitEntry(
                    name="alsa-state",
                    loaded_status="loaded",
                    active_status="inactive",
                    current_state="dead",
                    description="Manage Sound Card State (restore and store)",
                    enabled_status="disabled",
                ),
            ],
            [],
            {
                "included": [
                    UnitEntry(
                        name="gpu-manager",
                        loaded_status="loaded",
                        active_status="inactive",
                        current_state="dead",
                        description="Detect the available GPUs and deal with any system changes",
                        enabled_status="unknown",
                    ),
                    UnitEntry(
                        name="rsyslog",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="running",
                        description="System Logging Service",
                        enabled_status="enabled",
                    ),
                ],
                "excluded": [],
                "disabled": [
                    UnitEntry(
                        name="alsa-state",
                        loaded_status="loaded",
                        active_status="inactive",
                        current_state="dead",
                        description="Manage Sound Card State (restore and store)",
                        enabled_status="disabled",
                    )
                ],
                "static": [],
                "activating": [],
                "deactivating": [],
                "reloading": [],
            },
        ),
        (
            [
                UnitEntry(
                    name="gpu-manager",
                    loaded_status="loaded",
                    active_status="inactive",
                    current_state="dead",
                    description="Detect the available GPUs and deal with any system changes",
                    enabled_status="unknown",
                ),
                UnitEntry(
                    name="rsyslog",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="running",
                    description="System Logging Service",
                    enabled_status="enabled",
                ),
                UnitEntry(
                    name="alsa-state",
                    loaded_status="loaded",
                    active_status="inactive",
                    current_state="dead",
                    description="Manage Sound Card State (restore and store)",
                    enabled_status="indirect",
                ),
            ],
            ["gpu"],
            {
                "included": [
                    UnitEntry(
                        name="rsyslog",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="running",
                        description="System Logging Service",
                        enabled_status="enabled",
                    ),
                ],
                "excluded": [
                    UnitEntry(
                        name="gpu-manager",
                        loaded_status="loaded",
                        active_status="inactive",
                        current_state="dead",
                        description="Detect the available GPUs and deal with any system changes",
                        enabled_status="unknown",
                    ),
                ],
                "disabled": [
                    UnitEntry(
                        name="alsa-state",
                        loaded_status="loaded",
                        active_status="inactive",
                        current_state="dead",
                        description="Manage Sound Card State (restore and store)",
                        enabled_status="indirect",
                    )
                ],
                "static": [],
                "activating": [],
                "deactivating": [],
                "reloading": [],
            },
        ),
    ],
)
def test_services_split(services, blacklist, expected):
    actual = _services_split(services, blacklist)
    assert actual == expected


@pytest.mark.parametrize(
    "pre_string_table, section",
    [
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "0 unit files listed.",
            ],
            None,
            id="No systemd units returns empty parsed section",
        ),
        pytest.param(
            [],
            None,
            id="Empty agent section returns empty parsed section",
        ),
        pytest.param(
            [
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            None,
            id='Missing "[all]" header in agent section leads to empty parsed section',
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                )
            },
            id="Simple agent section parsed correctly",
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "* virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                )
            },
            id='Leading "*" in systemd status line is ignored',
        ),
        pytest.param(
            [
                "[all]",
                "unit load active sub description",
                "active plugged ",
                "1 unit files listed.",
            ],
            None,
            id="Invalid systemd status lines are skipped",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "UNIT FILE STATE",
                "virtualbox.service enabled",
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="enabled",
                )
            },
            id="Systemd unit status found in list-unit-files mapping",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "UNIT FILE STATE",
                "someother.service enabled",
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                )
            },
            id='Systemd unit status not available in list-unit-files mapping, use "unknown" instead',
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "● kbd.service not-found inactive dead kbd.service",
            ],
            {
                "kbd": UnitEntry(
                    name="kbd",
                    loaded_status="not-found",
                    active_status="inactive",
                    current_state="dead",
                    description="kbd.service",
                    enabled_status="unknown",
                ),
            },
            id="C.UTF-8 locale (● instead of * for broken units)",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "● cmktest.service - Checkmk Monitoring",
                "Loaded: loaded (/etc/systemd/system/cmktest.service; disabled; vendor preset: enabled)",
                "Active: activating (start) since Tue 2022-04-19 15:02:38 CEST; 33min ago",
                "Docs: https://docs.checkmk.com/latest/en",
                "Main PID: 173988 (sleep)",
                "Tasks: 1 (limit: 38101",
                "Memory: 176.0K",
                "CPU: 815u",
                "CGroup: /system.slice/cmktest.service",
                "└─173988 /usr/bin/sleep 88888",
                "Apr 19 15:02:38 klappmax systemd[1]: Starting Checkmk Monitoring..",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "cmktest.service loaded active running NOT FROM SYSTEMD",
            ],
            {
                "cmktest": UnitEntry(
                    name="cmktest",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="running",
                    description="NOT FROM SYSTEMD",
                    enabled_status="unknown",
                    time_since_change=timedelta(minutes=33),
                ),
            },
            id="parse status change",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "● sssd.service - System Security Services Daemon",
                "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
                " Active: inactive (dead)",
                " Condition: start condition failed at Tue 2022-04-12 12:53:54 CEST; 2h 0min ago",
                " ├─ ConditionPathExists=|/etc/sssd/sssd.conf was not met",
                " └─ ConditionDirectoryNotEmpty=|/etc/sssd/conf.d was not met",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
            ],
            {
                "sssd": UnitEntry(
                    name="sssd",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="running",
                    description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
                    enabled_status="unknown",
                    time_since_change=None,
                ),
            },
            id="parse status change works with status inactive (no time information included)",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "● rpcbind.socket - RPCbind Server Activation Socket",
                "Loaded: loaded (/lib/systemd/system/rpcbind.socket; enabled; vendor preset: enabled)",
                "Active: active (running) since Mon 2022-04-18 22:03:32 CEST; 15h ago",
                "Triggers: ● rpcbind.service",
                "Listen: /run/rpcbind.sock (Stream)",
                "0.0.0.0:111 (Stream)",
                "0.0.0.0:111 (Datagram)",
                "[::]:111 (Stream)",
                "[::]:111 (Datagram)",
                "Tasks: 0 (limit: 38101)",
                "Memory: 16.0K",
                "CPU: 1ms",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
            ],
            None,
            id="parse status works if '[' appears in output",
        ),
    ],
)
def test_parse_systemd_units(pre_string_table: Sequence[str], section: Section) -> None:
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


# This test is exhaustive given the options in the systemd source code at the time of writing
# https://github.com/systemd/systemd/blob/c87c30780624df257ed96909a2286b2b933f8c44/src/basic/time-util.c#L417
SEC_PER_MONTH = 2629800
SEC_PER_YEAR = 31557600


@pytest.mark.parametrize(
    "time, expected",
    [
        ("10us ago", timedelta(microseconds=10)),
        ("10ms ago", timedelta(milliseconds=10)),
        ("10s ago", timedelta(seconds=10)),
        ("2min 10s ago", timedelta(minutes=2, seconds=10)),
        ("2min 0s ago", timedelta(minutes=2)),
        ("23min ago", timedelta(minutes=23)),
        ("10h 42min ago", timedelta(hours=10, minutes=42)),
        ("1h 0min ago", timedelta(hours=1)),
        ("13h ago", timedelta(hours=13)),
        ("1 day 13h ago", timedelta(days=1, hours=13)),
        ("1 day 0h ago", timedelta(days=1)),
        ("21 days ago", timedelta(days=21)),
        ("1 week 1 day ago", timedelta(weeks=1, days=1)),
        ("1 week 0 day ago", timedelta(weeks=1)),
        ("2 weeks 2 days ago", timedelta(weeks=2, days=2)),
        ("1 month 1 day ago", timedelta(days=1, seconds=SEC_PER_MONTH)),
        ("1 month 0 day ago", timedelta(seconds=SEC_PER_MONTH)),
        ("2 months 2 days ago", timedelta(days=2, seconds=SEC_PER_MONTH * 2)),
        ("1 year 1 month ago", timedelta(seconds=SEC_PER_MONTH + SEC_PER_YEAR)),
        ("1 year 0 month ago", timedelta(seconds=SEC_PER_YEAR)),
        ("2 years 2 months ago", timedelta(seconds=SEC_PER_MONTH * 2 + SEC_PER_YEAR * 2)),
        ("0 years 12 months ago", timedelta(seconds=SEC_PER_MONTH * 12)),
    ],
)
def test_parse_time_since_state_change(time, expected):
    condition = f" Condition: start condition failed at Tue 2022-04-12 12:53:54 CEST; {time}"
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        "● sssd.service - System Security Services Daemon",
        "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
        condition,
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        "sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
    ]
    section = {
        "sssd": UnitEntry(
            name="sssd",
            loaded_status="loaded",
            active_status="active",
            current_state="running",
            description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
            enabled_status="unknown",
            time_since_change=expected,
        ),
    }
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "icon",
    ["●", "○", "↻", "×", "x", "*"],
)
def test_all_possible_service_states_in_status_section(icon):
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        f"{icon} sssd.service - System Security Services Daemon",
        "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
        " Condition: start condition failed at Tue 2022-04-12 12:53:54 CEST; 3s ago",
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        "sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
    ]
    section = {
        "sssd": UnitEntry(
            name="sssd",
            loaded_status="loaded",
            active_status="active",
            current_state="running",
            description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
            enabled_status="unknown",
            time_since_change=timedelta(seconds=3),
        ),
    }
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "icon",
    ["●", "○", "↻", "×", "x", "*"],
)
def test_all_possible_service_states_in_all_section(icon):
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        "● sssd.service - System Security Services Daemon",
        "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
        " Condition: start condition failed at Tue 2022-04-12 12:53:54 CEST; 3s ago",
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        f"{icon} sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
    ]
    section = {
        "sssd": UnitEntry(
            name="sssd",
            loaded_status="loaded",
            active_status="active",
            current_state="running",
            description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
            enabled_status="unknown",
            time_since_change=timedelta(seconds=3),
        ),
    }
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


SECTION = {
    "virtualbox": UnitEntry(
        name="virtualbox",
        loaded_status="loaded",
        active_status="active",
        current_state="exited",
        description="LSB: VirtualBox Linux kernel module",
        enabled_status="unknown",
        time_since_change=timedelta(seconds=2),
    ),
    "bar": UnitEntry(
        name="bar",
        loaded_status="loaded",
        active_status="failed",
        current_state="failed",
        description="a bar service",
        enabled_status="unknown",
    ),
    "foo": UnitEntry(
        name="foo",
        loaded_status="loaded",
        active_status="failed",
        current_state="failed",
        description="Arbitrary Executable File Formats File System Automount Point",
        enabled_status="unknown",
    ),
    "check-mk-agent@738-127.0.0.1:6556-127.0.0.1:51542": UnitEntry(
        name="check-mk-agent@738-127.0.0.1:6556-127.0.0.1:51542",
        loaded_status="loaded",
        active_status="active",
        current_state="running",
        description="Checkmk agent (127.0.0.1:51542)",
        enabled_status="static",
    ),
    "check-mk-enterprise-2021.09.07": UnitEntry(
        name="check-mk-enterprise-2021.09.07",
        loaded_status="loaded",
        active_status="active",
        current_state="exited",
        description="LSB: OMD sites",
        enabled_status="generated",
    ),
}


@pytest.mark.parametrize(
    "section, discovery_params, discovered_services",
    [
        (
            SECTION,
            [
                {"names": ["~virtualbox.*"]},
            ],
            [Service(item="virtualbox")],
        ),
        (
            SECTION,
            [],
            [],
        ),
        (
            {},
            [
                {"names": ["~virtualbox.*"]},
            ],
            [],
        ),
        (
            SECTION,
            [
                {"names": ["~aardvark.*"]},
            ],
            [],
        ),
        (
            SECTION,
            [
                {"names": ["~.*"]},
            ],
            [
                Service(item="virtualbox"),
                Service(item="bar"),
                Service(item="foo"),
                Service(item="check-mk-enterprise-2021.09.07"),
            ],
        ),
    ],
)
def test_discover_systemd_units_services(section, discovery_params, discovered_services):
    assert (
        list(discovery_systemd_units_services(params=discovery_params, section=section))
        == discovered_services
    )


@pytest.mark.parametrize(
    "section, discovered_services",
    [
        (
            SECTION,
            [Service(item="Summary")],
        ),
    ],
)
def test_discover_systemd_units_services_summary(section, discovered_services):
    assert list(discovery_systemd_units_services_summary(section)) == discovered_services


@pytest.mark.parametrize(
    "item, params, section, check_results",
    [
        (
            "virtualbox",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            SECTION,
            [
                Result(state=State.OK, summary="Status: active"),
                Result(state=State.OK, summary="LSB: VirtualBox Linux kernel module"),
            ],
        ),
        (
            "foo",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            SECTION,
            [
                Result(state=State.CRIT, summary="Status: failed"),
                Result(
                    state=State.OK,
                    summary="Arbitrary Executable File Formats File System Automount Point",
                ),
            ],
        ),
        (
            "something",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            SECTION,
            [Result(state=State.CRIT, summary="Service not found")],
        ),
        (
            "something",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            {},
            [Result(state=State.CRIT, summary="Service not found")],
        ),
    ],
)
def test_check_systemd_units_services(item, params, section, check_results):
    assert list(check_systemd_units_services(item, params, section)) == check_results


@pytest.mark.parametrize(
    "params, section, check_results",
    [
        # "Normal" test case
        (
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            SECTION,
            [
                Result(state=State.OK, summary="Total: 5"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 2"),
                Result(state=State.CRIT, summary="2 services failed (bar, foo)"),
            ],
        ),
        # Ignored (see 'blacklist')
        (
            {
                "ignored": ["virtual"],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                ),
            },
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Ignored: 1"),
            ],
        ),
        # (de)activating
        (
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="activating",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                    time_since_change=timedelta(seconds=2),
                ),
                "actualbox": UnitEntry(
                    name="actualbox",
                    loaded_status="loaded",
                    active_status="deactivating",
                    current_state="finished",
                    description="A made up service for this test",
                    enabled_status="unknown",
                    time_since_change=timedelta(seconds=4),
                ),
            },
            [
                Result(state=State.OK, summary="Total: 2"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' activating for: 2 seconds"),
                Result(state=State.OK, notice="Service 'actualbox' deactivating for: 4 seconds"),
            ],
        ),
        # Activating + reloading
        (
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="activating",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="reloading",
                    time_since_change=timedelta(seconds=2),
                ),
            },
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' activating for: 2 seconds"),
            ],
        ),
        # Reloading
        (
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="reloading",
                    time_since_change=timedelta(seconds=2),
                ),
            },
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' reloading for: 2 seconds"),
            ],
        ),
        # Indirect
        (
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="active",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="indirect",
                ),
            },
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 1"),
                Result(state=State.OK, summary="Failed: 0"),
            ],
        ),
        # Custom systemd state
        (
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            {
                "virtualbox": UnitEntry(
                    name="virtualbox",
                    loaded_status="loaded",
                    active_status="somesystemdstate",
                    current_state="exited",
                    description="LSB: VirtualBox Linux kernel module",
                    enabled_status="unknown",
                ),
            },
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.CRIT, summary="1 service somesystemdstate (virtualbox)"),
            ],
        ),
    ],
)
def test_check_systemd_units_services_summary(params, section, check_results):
    assert (
        list(
            check_systemd_units_services_summary(
                item="nonsense-backward-compatibility", params=params, section=section
            )
        )
        == check_results
    )
