#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from datetime import timedelta
from typing import Any

import pytest

from cmk.utils.check_utils import ParametersTypeAlias

from cmk.agent_based.v2 import HostLabel, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.systemd_units import (
    _services_split,
    CHECK_DEFAULT_PARAMETERS_SUMMARY,
    check_systemd_services,
    check_systemd_sockets,
    check_systemd_units_services_summary,
    CpuTimeSeconds,
    discover_host_labels,
    discovery_systemd_units_services,
    discovery_systemd_units_services_summary,
    discovery_systemd_units_sockets,
    Memory,
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
                    enabled_status=None,
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
                        enabled_status=None,
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
                    enabled_status=None,
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
                        enabled_status=None,
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
def test_services_split(
    services: Sequence[UnitEntry],
    blacklist: Sequence[str],
    expected: dict[str, Sequence[UnitEntry]],
) -> None:
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
            Section(services={}, sockets={}),
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
            Section(services={}, sockets={}),
            id='Missing "[all]" header in agent section leads to empty parsed section',
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                    )
                },
            ),
            id="Simple agent section parsed correctly",
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB DESCRIPTION",
                "* virtualbox.service loaded active exited LSB: VirtualBox Linux kernel module",
                "1 unit files listed.",
            ],
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                    )
                },
            ),
            id='Leading "*" in systemd status line is ignored',
        ),
        pytest.param(
            [
                "[all]",
                "unit load active sub description",
                "active plugged ",
                "1 unit files listed.",
            ],
            Section(services={}, sockets={}),
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
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status="enabled",
                    )
                },
            ),
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
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                    )
                },
            ),
            id="Systemd unit status not available in list-unit-files mapping, use unknown instead",
        ),
        pytest.param(
            [
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "● kbd.service not-found inactive dead kbd.service",
            ],
            Section(
                sockets={},
                services={
                    "kbd": UnitEntry(
                        name="kbd",
                        loaded_status="not-found",
                        active_status="inactive",
                        current_state="dead",
                        description="kbd.service",
                        enabled_status=None,
                    ),
                },
            ),
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
                "cmktest.service loaded activating start NOT FROM SYSTEMD",
            ],
            Section(
                sockets={},
                services={
                    "cmktest": UnitEntry(
                        name="cmktest",
                        loaded_status="loaded",
                        active_status="activating",
                        current_state="start",
                        description="NOT FROM SYSTEMD",
                        enabled_status="disabled",
                        time_since_change=timedelta(minutes=33),
                        cpu_seconds=CpuTimeSeconds(value=0.000815),
                        number_of_tasks=1,
                        memory=Memory(180224),
                    ),
                },
            ),
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
                "sssd.service loaded inactive dead SSSD NOT FROM SYSTEMD ONLY FOR TEST",
            ],
            Section(
                sockets={},
                services={
                    "sssd": UnitEntry(
                        name="sssd",
                        loaded_status="loaded",
                        active_status="inactive",
                        current_state="dead",
                        description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
                        enabled_status="enabled",
                        time_since_change=None,
                    ),
                },
            ),
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
            Section(services={}, sockets={}),
            id="parse status works if '[' appears in output",
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
                "x Memory: 16.0K",
                "CPU: 1ms",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
            ],
            Section(services={}, sockets={}),
            id="parse status with misleading status symbol (x)",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "acpid.service",
                "Loaded: not-found (Reason: No such file or directory)",
                "Active: inactive (dead)",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
            ],
            Section(services={}, sockets={}),
            id="parse status works with incomplete data (SUP-10799)",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "cockpit.socket",
                "disabled",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "cockpit.socket loaded active listening Cockpit Web Service Socket",
            ],
            Section(
                sockets={
                    "cockpit": UnitEntry(
                        name="cockpit",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="listening",
                        description="Cockpit Web Service Socket",
                        enabled_status=None,
                        time_since_change=None,
                    )
                },
                services={},
            ),
            id="parse a socket instead of a service",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "cockpit.socket",
                "disabled",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "cockpit.socket loaded active listening",
            ],
            Section(
                sockets={
                    "cockpit": UnitEntry(
                        name="cockpit",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="listening",
                        description="",
                        enabled_status=None,
                        time_since_change=None,
                    )
                },
                services={},
            ),
            id="missing description",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "wasServer@.service indirect disabled",
                "[status]",
                "× wasServer@blablu.service - The WAS Server blablu",
                "Loaded: loaded (/etc/systemd/system/wasServer@.service; enabled; preset: disabled)",
                "Active: failed (Result: exit-code) since Wed 2024-10-09 12:06:40 CEST; 1 week 6 days ago",
                "Duration: 7h 28min 10.894s",
                "Main PID: 2505 (code=exited, status=0/SUCCESS)",
                "CPU: 3min 17.030s",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "wasServer@blablu.service loaded failed failed The WAS Server blablu",
            ],
            Section(
                services={
                    "wasServer@blablu": UnitEntry(
                        name="wasServer@blablu",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="The WAS Server blablu",
                        enabled_status="enabled",
                        time_since_change=timedelta(days=13),
                        cpu_seconds=CpuTimeSeconds(value=180.0 + 17.03),
                    )
                },
                sockets={},
            ),
            id="the enabled state is indirect, bc it comes from the unit-files. however status tells us 'enabled'",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "check-mk-agent.socket enabled enabled",
                "check-mk-agent@.service static -",
                "[status]",
                "● check-mk-agent@3149-1849349-997.service - Checkmk agent (PID 1849349/UID 997)",
                "Loaded: loaded (/lib/systemd/system/check-mk-agent@.service; static)",
                "Active: active (running) since Thu 2024-11-14 06:58:57 CET; 1s ago",
                "TriggeredBy: ● check-mk-agent.socket",
                "Docs: https://docs.checkmk.com/latest/en/agent_linux.html",
                "Main PID: 4075582 (check_mk_agent)",
                "Tasks: 6 (limit: 37925)",
                "Memory: 3.9M",
                "CPU: 134ms",
                "CGroup: /system.slice/system-check\x2dmk\x2dagent.slice/check-mk-agent@3149-1849349-997.service",
                "├─4075582 /bin/bash /usr/bin/check_mk_agent",
                "├─4075631 /bin/bash /usr/bin/check_mk_agent",
                "├─4075632 /bin/bash /usr/bin/check_mk_agent",
                "├─4075634 cat",
                "├─4075658 systemctl status --all --type service --type socket --no-pager --lines 0",
                "└─4075659 tr -s ",
                "● check-mk-agent.socket - Local Checkmk agent socket",
                "Loaded: loaded (/lib/systemd/system/check-mk-agent.socket; enabled; vendor preset: enabled)",
                "Active: active (listening) since Tue 2024-11-12 15:58:09 CET; 1 day 15h ago",
                "Triggers: ● check-mk-agent@3148-1849349-997.service",
                "● check-mk-agent@3149-1849349-997.service",
                "Docs: https://docs.checkmk.com/latest/en/agent_linux.html",
                "Listen: /run/check-mk-agent.socket (Stream)",
                "Accepted: 3150; Connected: 2;",
                "Tasks: 0 (limit: 37925)",
                "Memory: 0B",
                "CPU: 835us",
                "CGroup: /system.slice/check-mk-agent.socket",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "check-mk-agent@3149-1849349-997.service loaded active running Checkmk agent (PID 1849349/UID 997)",
                "check-mk-agent.socket loaded active listening Local Checkmk agent socket",
            ],
            Section(
                services={
                    "check-mk-agent@3149-1849349-997": UnitEntry(
                        name="check-mk-agent@3149-1849349-997",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="running",
                        description="Checkmk agent (PID 1849349/UID 997)",
                        enabled_status="static",
                        time_since_change=timedelta(seconds=1),
                        cpu_seconds=CpuTimeSeconds(value=0.134),
                        memory=Memory(bytes=4089446),
                        number_of_tasks=6,
                    )
                },
                sockets={
                    "check-mk-agent": UnitEntry(
                        name="check-mk-agent",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="listening",
                        description="Local Checkmk agent socket",
                        enabled_status="enabled",
                        time_since_change=None,
                        cpu_seconds=None,
                        memory=None,
                        number_of_tasks=None,
                    )
                },
            ),
            id="a unit which triggers multiple units: the new line after 'Triggers' is not a "
            "new entry, but referes to another unit which gets triggered by the current entry",
        ),
        pytest.param(
            [
                "[list-unit-files]",
                "[status]",
                "● apache2.service - LSB: Apache2 web server",
                "Loaded: loaded (/etc/init.d/apache2)",
                "Drop-In: /lib/systemd/system/apache2.service.d",
                "└─forking.conf",
                "Active: active (running) since Sat 2024-11-16 02:00:04 CET; 2 days ago",
                "CGroup: /system.slice/apache2.service",
                "├─ 1174 /usr/sbin/apache2 -k start",
                "[all]",
                "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
                "apache2.service loaded active running LSB: Apache2 web server",
            ],
            Section(
                services={
                    "apache2": UnitEntry(
                        name="apache2",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="running",
                        description="LSB: Apache2 web server",
                        enabled_status=None,
                        time_since_change=timedelta(days=2),
                        cpu_seconds=None,
                        memory=None,
                        number_of_tasks=None,
                    )
                },
                sockets={},
            ),
            id="unit in status section but not in list-unit-files",
        ),
    ],
)
def test_parse_systemd_units(pre_string_table: Sequence[str], section: Section) -> None:
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            [{"names": ["~apache"]}],
            [],
            id="no-host-labels",
        ),
        pytest.param(
            [{"names": ["~apache"], "host_labels_auto": True}],
            [HostLabel("cmk/systemd/unit", "apache")],
            id="host-labels-auto",
        ),
        pytest.param(
            [{"names": ["~apache"], "host_labels_explicit": {"webserver": "value"}}],
            [HostLabel("webserver", "value")],
            id="host-labels-explicit",
        ),
    ],
)
def test_discover_host_labels_of_systemd_units(
    params: Sequence[Mapping[str, Any]], expected: Sequence[HostLabel]
) -> None:
    assert (
        list(
            discover_host_labels(
                params,
                Section(
                    services={
                        "apache": UnitEntry(
                            name="apache",
                            loaded_status="loaded",
                            active_status="active",
                            current_state="running",
                            description="LSB: Apache2 web server",
                            enabled_status=None,
                            time_since_change=timedelta(days=2),
                            cpu_seconds=None,
                            memory=None,
                            number_of_tasks=None,
                        )
                    },
                    sockets={},
                ),
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    "raw_string, expected_seconds",
    [
        pytest.param(
            "3min",
            180.0,
            id="CPU time parsing: Single unit",
        ),
        pytest.param(
            "3min 12s",
            192.0,
            id="CPU time parsing: Two units",
        ),
        pytest.param(
            "3d 3min 3s",
            3 * 24 * 3600 + 180 + 3.0,
            id="CPU time parsing: Three units",
        ),
    ],
)
def test_parse_cpu_time(raw_string: str, expected_seconds: float) -> None:
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        "● apache2.service - LSB: Apache2 web server",
        "Loaded: loaded (/etc/init.d/apache2)",
        "Active: active (running) since Sat 2024-11-16 02:00:04 CET; 2 days ago",
        f"CPU: {raw_string}",
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        "apache2.service loaded active running LSB: Apache2 web server",
    ]
    string_table = [el.split() for el in pre_string_table]

    section = Section(
        services={
            "apache2": UnitEntry(
                name="apache2",
                loaded_status="loaded",
                active_status="active",
                current_state="running",
                description="LSB: Apache2 web server",
                enabled_status=None,
                time_since_change=timedelta(days=2),
                cpu_seconds=CpuTimeSeconds(value=expected_seconds),
                memory=None,
                number_of_tasks=None,
            )
        },
        sockets={},
    )
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
def test_parse_time_since_state_change(time: str, expected: timedelta) -> None:
    condition = f"Active: active (running) since Tue 2022-04-12 12:53:54 CEST; {time}"
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
    section = Section(
        sockets={},
        services={
            "sssd": UnitEntry(
                name="sssd",
                loaded_status="loaded",
                active_status="active",
                current_state="running",
                description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
                enabled_status="enabled",
                time_since_change=expected,
            ),
        },
    )
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "icon",
    ["●", "○", "↻", "×", "x", "*"],
)
def test_all_possible_service_states_in_status_section(icon: str) -> None:
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        f"{icon} sssd.service - System Security Services Daemon",
        "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
        "Active: active (running) since Mon Tue 2022-04-12 12:53:54 CEST; 3s ago",
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        "sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
    ]
    section = Section(
        sockets={},
        services={
            "sssd": UnitEntry(
                name="sssd",
                loaded_status="loaded",
                active_status="active",
                current_state="running",
                description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
                enabled_status="enabled",
                time_since_change=timedelta(seconds=3),
            ),
        },
    )
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


@pytest.mark.parametrize(
    "icon",
    ["●", "○", "↻", "×", "x", "*"],
)
def test_all_possible_service_states_in_all_section(icon: str) -> None:
    pre_string_table = [
        "[list-unit-files]",
        "[status]",
        "● sssd.service - System Security Services Daemon",
        "Loaded: loaded (/lib/systemd/system/sssd.service; enabled; vendor preset: enabled)",
        "Active: active (running) since Mon Tue 2022-04-12 12:53:54 CEST; 3s ago",
        "[all]",
        "UNIT LOAD ACTIVE SUB JOB DESCRIPTION",
        f"{icon} sssd.service loaded active running SSSD NOT FROM SYSTEMD ONLY FOR TEST",
    ]
    section = Section(
        sockets={},
        services={
            "sssd": UnitEntry(
                name="sssd",
                loaded_status="loaded",
                active_status="active",
                current_state="running",
                description="SSSD NOT FROM SYSTEMD ONLY FOR TEST",
                enabled_status="enabled",
                time_since_change=timedelta(seconds=3),
            ),
        },
    )
    string_table = [el.split() for el in pre_string_table]
    assert parse(string_table) == section


SECTION = Section(
    sockets={},
    services={
        "virtualbox": UnitEntry(
            name="virtualbox",
            loaded_status="loaded",
            active_status="active",
            current_state="exited",
            description="LSB: VirtualBox Linux kernel module",
            enabled_status=None,
            time_since_change=timedelta(seconds=2),
        ),
        "cmktest": UnitEntry(
            name="cmktest",
            loaded_status="loaded",
            active_status="active",
            current_state="running",
            description="NOT FROM SYSTEMD",
            enabled_status=None,
            time_since_change=timedelta(minutes=33),
            cpu_seconds=CpuTimeSeconds(value=0.000815),
            number_of_tasks=1,
            memory=Memory(180224),
        ),
        "bar": UnitEntry(
            name="bar",
            loaded_status="loaded",
            active_status="failed",
            current_state="failed",
            description="a bar service",
            enabled_status=None,
        ),
        "foo": UnitEntry(
            name="foo",
            loaded_status="loaded",
            active_status="failed",
            current_state="failed",
            description="Arbitrary Executable File Formats File System Automount Point",
            enabled_status=None,
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
    },
)


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
            Section(services={}, sockets={}),
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
                Service(item="cmktest"),
                Service(item="bar"),
                Service(item="foo"),
                Service(item="check-mk-enterprise-2021.09.07"),
            ],
        ),
    ],
)
def test_discover_systemd_units_services(
    section: Section,
    discovery_params: Sequence[Mapping[str, Sequence[str]]],
    discovered_services: Sequence[Service],
) -> None:
    assert (
        list(
            discovery_systemd_units_services(
                params=discovery_params,
                section=section,
            )
        )
        == discovered_services
    )


@pytest.mark.parametrize(
    "section, discovery_params, discovered_services",
    [
        (
            Section(
                sockets={
                    "cockpit": UnitEntry(
                        name="cockpit",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="listening",
                        description="Cockpit Web Service Socket",
                        enabled_status=None,
                        time_since_change=None,
                    )
                },
                services={},
            ),
            [
                {"names": ["~cockpit"]},
            ],
            [
                Service(item="cockpit"),
            ],
        ),
    ],
)
def test_discover_systemd_units_sockets(
    section: Section,
    discovery_params: Sequence[Mapping[str, Sequence[str]]],
    discovered_services: Sequence[Service],
) -> None:
    assert (
        list(discovery_systemd_units_sockets(params=discovery_params, section=section))
        == discovered_services
    )


@pytest.mark.parametrize(
    "section, discovered_services",
    [
        (
            SECTION,
            [Service()],
        ),
    ],
)
def test_discover_systemd_units_services_summary(
    section: Section, discovered_services: Sequence[Service]
) -> None:
    assert list(discovery_systemd_units_services_summary(section)) == discovered_services


@pytest.mark.parametrize(
    "item, params, section, check_results",
    [
        (
            "cmktest",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            SECTION,
            [
                Result(state=State.OK, summary="Status: active"),
                Result(state=State.OK, summary="NOT FROM SYSTEMD"),
                Result(state=State.OK, summary="CPU Time: 815 microseconds"),
                Metric("cpu_time", 0.000815),
                Result(state=State.OK, summary="Active since: 33 minutes 0 seconds"),
                Metric("active_since", 1980.0),
                Result(state=State.OK, summary="Memory: 176 KiB"),
                Metric("mem_used", 180224.0),
                Result(state=State.OK, summary="Number of tasks: 1"),
                Metric("number_of_tasks", 1.0),
            ],
        ),
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
                Result(state=State.OK, summary="Active since: 2 seconds"),
                Metric("active_since", 2.0),
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
            [
                Result(
                    state=State.CRIT,
                    summary="Unit not found",
                    details="Only units currently in memory are found. These can be shown with `systemctl --all --type service --type socket`.",
                )
            ],
        ),
        (
            "something",
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
            },
            Section(services={}, sockets={}),
            [
                Result(
                    state=State.CRIT,
                    summary="Unit not found",
                    details="Only units currently in memory are found. These can be shown with `systemctl --all --type service --type socket`.",
                )
            ],
        ),
    ],
)
def test_check_systemd_units_services(
    item: str, params: ParametersTypeAlias, section: Section, check_results: Sequence[Result]
) -> None:
    assert list(check_systemd_services(item, params, section)) == check_results


@pytest.mark.parametrize(
    "item, params, section, check_results",
    [
        (
            "cockpit",
            {
                "else": 2,
                "states": {"active": 2, "failed": 1, "inactive": 0},
                "states_default": 2,
            },
            Section(
                sockets={
                    "cockpit": UnitEntry(
                        name="cockpit",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="listening",
                        description="Cockpit Web Service Socket",
                        enabled_status=None,
                        time_since_change=None,
                    )
                },
                services={},
            ),
            [
                Result(state=State.CRIT, summary="Status: active"),
                Result(state=State.OK, summary="Cockpit Web Service Socket"),
            ],
        ),
    ],
)
def test_check_systemd_units_sockets(
    item: str, params: ParametersTypeAlias, section: Section, check_results: Sequence[Result]
) -> None:
    assert list(check_systemd_sockets(item, params, section)) == check_results


@pytest.mark.parametrize(
    "params, section, check_results",
    [
        pytest.param(
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
                Result(state=State.OK, summary="Total: 6"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.CRIT, summary="Failed: 2"),
                Result(state=State.CRIT, summary="2 services failed (bar, foo)"),
            ],
            id="'Normal' test case",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 1, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            SECTION,
            [
                Result(state=State.OK, summary="Total: 6"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.WARN, summary="Failed: 2"),
                Result(state=State.WARN, summary="2 services failed (bar, foo)"),
            ],
            id="Custom state for failed",
        ),
        pytest.param(
            {
                "ignored": ["virtual"],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Ignored: 1"),
            ],
            id="Ignored (see 'blacklist')",
        ),
        pytest.param(
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="activating",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                        time_since_change=timedelta(seconds=2),
                    ),
                    "actualbox": UnitEntry(
                        name="actualbox",
                        loaded_status="loaded",
                        active_status="deactivating",
                        current_state="finished",
                        description="A made up service for this test",
                        enabled_status=None,
                        time_since_change=timedelta(seconds=4),
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 2"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' activating for: 2 seconds"),
                Result(state=State.OK, notice="Service 'actualbox' deactivating for: 4 seconds"),
            ],
            id="(de)activating",
        ),
        pytest.param(
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="activating",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status="enabled",
                        time_since_change=timedelta(seconds=2),
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' activating for: 2 seconds"),
            ],
            id="Activating + reloading",
        ),
        pytest.param(
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="reloading",
                        current_state="reload",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status="enabled",
                        time_since_change=timedelta(seconds=2),
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.OK, notice="Service 'virtualbox' reloading for: 2 seconds"),
            ],
            id="Reloading",
        ),
        pytest.param(
            {
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="active",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status="indirect",
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 1"),
                Result(state=State.OK, summary="Failed: 0"),
            ],
            id="Indirect",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "virtualbox": UnitEntry(
                        name="virtualbox",
                        loaded_status="loaded",
                        active_status="somesystemdstate",
                        current_state="exited",
                        description="LSB: VirtualBox Linux kernel module",
                        enabled_status=None,
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 0"),
                Result(state=State.CRIT, summary="1 service somesystemdstate (virtualbox)"),
            ],
            id="Custom systemd state",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [
                    "systemd-timesyncd.service",
                    "systemd-ask-password-console",
                    "zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                ],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100": UnitEntry(
                        name="zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="enabled",
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 1"),
                Result(state=State.OK, notice="Ignored: 1"),
            ],
            id="Failed, but ignored service",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [
                    "systemd.",
                ],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100": UnitEntry(
                        name="zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="enabled",
                    ),
                    "systemd-timesyncd.service": UnitEntry(
                        name="systemd-timesyncd.service",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="enabled",
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 2"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.CRIT, summary="Failed: 2"),
                Result(
                    state=State.CRIT,
                    summary="1 service failed (zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100)",
                ),
                Result(state=State.OK, notice="Ignored: 1"),
            ],
            id="Two failed. One failed but ignored with regex",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 2, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "systemd-timesyncd.service": UnitEntry(
                        name="systemd-timesyncd.service",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="disabled",
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 1"),
                Result(state=State.OK, summary="Disabled: 1"),
                Result(state=State.OK, summary="Failed: 1"),
            ],
            id="One failed, but disabled",
        ),
        pytest.param(
            {
                "else": 2,
                "states": {"active": 0, "failed": 0, "inactive": 0},
                "states_default": 2,
                "ignored": [],
                "activating_levels": (30, 60),
                "deactivating_levels": (30, 60),
                "reloading_levels": (30, 60),
            },
            Section(
                sockets={},
                services={
                    "zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100": UnitEntry(
                        name="zfs-import@fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="enabled",
                    ),
                    "systemd-timesyncd.service": UnitEntry(
                        name="systemd-timesyncd.service",
                        loaded_status="loaded",
                        active_status="failed",
                        current_state="failed",
                        description="Import ZFS pool fgprs\\x2dpbs02\\x2dpool1\\x2d100",
                        enabled_status="enabled",
                    ),
                },
            ),
            [
                Result(state=State.OK, summary="Total: 2"),
                Result(state=State.OK, summary="Disabled: 0"),
                Result(state=State.OK, summary="Failed: 2"),
            ],
            id="Two failed, but OK state configured in params",
        ),
    ],
)
def test_check_systemd_units_services_summary(
    params: ParametersTypeAlias, section: Section, check_results: Sequence[Result]
) -> None:
    assert (
        list(check_systemd_units_services_summary(params=params, section=section)) == check_results
    )


def test_reloading() -> None:
    # $ cat /etc/systemd/system/testing.service
    # [Service]
    #
    # ExecStartPre=/usr/bin/sleep 75
    # ExecStart=/usr/bin/sleep 90000
    # ExecStop=/usr/bin/sleep 90
    # ExecReload=/usr/bin/sleep 65
    #
    # [Install]
    # WantedBy=multi-user.target
    #
    # $ systemctl enable testing
    # $ check_mk_agent > /tmp/systemd/dead
    # $ systemctl start testing
    # $ check_mk_agent > /tmp/systemd/starting
    # # wait a bit, check with systemctl status testing
    # $ check_mk_agent > /tmp/systemd/started
    # # ... do same with reloaded and reloading, and other states you want to check
    # $ use-dump --site heute --path agent /tmp/systemd/*
    # # check services in your site, maybe use service search for better overview

    pre_pre_string_table = """[list-unit-files]
testing.service enabled enabled
[status]
↻ testing.service
Loaded: loaded (/etc/systemd/system/testing.service; enabled; vendor preset: enabled)
Active: reloading (reload) since Tue 2024-08-20 11:49:32 CEST; 53s ago
Process: 1727884 ExecStartPre=/usr/bin/sleep 75 (code=exited, status=0/SUCCESS)
Main PID: 1728726 (sleep); Control PID: 1729357 (sleep)
Tasks: 2 (limit: 38119)
Memory: 360.0K
CPU: 8ms
CGroup: /system.slice/testing.service
├─1728726 /usr/bin/sleep 90000
└─1729357 /usr/bin/sleep 65
[all]
testing.service loaded reloading reload reload testing.service
"""
    string_table = [l.split(" ") for l in pre_pre_string_table.split("\n")]
    parsed = parse(string_table)
    assert parsed is not None
    assert list(
        check_systemd_units_services_summary(
            params=CHECK_DEFAULT_PARAMETERS_SUMMARY, section=parsed
        )
    ) == [
        Result(state=State.OK, summary="Total: 1"),
        Result(state=State.OK, summary="Disabled: 0"),
        Result(state=State.OK, summary="Failed: 0"),
        Result(
            state=State.WARN,
            summary="Service 'testing' reloading for: 53 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
        ),
    ]


def test_broken_parsing_without_unit_description() -> None:
    pre_pre_string_table = """
<<<systemd_units>>>
[list-unit-files]
testing.service enabled enabled
systemd-user-sessions.service static -
[status]
● klapp-0285
State: running
Jobs: 1 queued
Failed: 0 units
Since: Mon 2024-08-19 07:09:27 CEST; 1 day 4h ago
CGroup: /
├─sys-fs-fuse-connections.mount

● systemd-user-sessions.service - Permit User Sessions
Loaded: loaded (/lib/systemd/system/systemd-user-sessions.service; static)
Active: active (exited) since Mon 2024-08-19 07:09:30 CEST; 1 day 4h ago
Docs: man:systemd-user-sessions.service(8)
Main PID: 1397 (code=exited, status=0/SUCCESS)
CPU: 6ms

↻ testing.service
Loaded: loaded (/etc/systemd/system/testing.service; enabled; vendor preset: enabled)
Active: reloading (reload) since Tue 2024-08-20 11:49:32 CEST; 53s ago
Process: 1727884 ExecStartPre=/usr/bin/sleep 75 (code=exited, status=0/SUCCESS)
Main PID: 1728726 (sleep); Control PID: 1729357 (sleep)
Tasks: 2 (limit: 38119)
Memory: 360.0K
CPU: 8ms
CGroup: /system.slice/testing.service
├─1728726 /usr/bin/sleep 90000
└─1729357 /usr/bin/sleep 65

[all]
testing.service loaded reloading reload reload testing.service
systemd-user-sessions.service loaded active exited Permit User Sessions
"""

    string_table = [l.split(" ") for l in pre_pre_string_table.split("\n")]
    parsed = parse(string_table)
    assert parsed is not None
    assert parsed.services["testing"].time_since_change == timedelta(seconds=53)


@pytest.mark.parametrize(
    "raw_string, expected",
    [
        pytest.param("0", 0.0, id="0"),
        pytest.param("8ms", 8e-3, id="8ms"),
        pytest.param("1min 13s", 73.0, id="1min 13s"),
        pytest.param("3d 1s", 259_201.0, id="3d 1s"),
        pytest.param("3w 3d 1s", 2_073_601.0, id="3w 3d 1s"),
        pytest.param(
            "1month 4w 2d 3h 38min 41.898s", 5_234_921.898, id="1month 4w 2d 3h 38min 41.898s"
        ),
        pytest.param(
            "5y 1month 4w 2d 3h 38min 41.898s",
            163_022_921.898,
            id="5y 1month 4w 2d 3h 38min 41.898s",
        ),
        pytest.param(
            "5y",
            157_788_000,
            id="5y",
        ),
    ],
)
def test_cputimeseconds_parse(raw_string: str, expected: float) -> None:
    assert CpuTimeSeconds.parse_raw(raw=raw_string).value == expected


@pytest.mark.parametrize(
    "raw_string",
    [
        pytest.param("", id="0"),
        pytest.param("0xyz", id="0"),
        pytest.param("8arfs", id="8arfs"),
        pytest.param("1z", id="1z"),
    ],
)
def test_cputimeseconds_parse_nonsense(raw_string: str) -> None:
    with pytest.raises(ValueError):
        CpuTimeSeconds.parse_raw(raw=raw_string)
