#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests of the Veeam special agent, which monitors Veeam Backup & Replication via its REST API.

The tests run against a mocked Veeam server that replays responses recorded from a real
one (see mock_vbr.py). During regular manual testing sessions, or on demand, they are
also run against the real server, to catch changes in its API or its login that the
recording would hide. README.md explains how to run against the real server and how to
record new responses.

The special agent connects as the Veeam Administrator user, so the expected values are
what an administrator sees. They describe the real server at the time of recording: if
the real server changes, update them here and re-record the responses.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.testlib.common.utils2 import ServiceInfo
from tests.testlib.system.site import Site

from .helpers import BACKUP_SERVER_HOST_NAME, PROTECTED_MACHINE_HOST_NAME, VeeamAccount

# Temporary skip the tests on Cloud as it is not supported yet
pytestmark = pytest.mark.skip_if_edition("cloud")

# The Veeam backup server: what it reports about itself.
BACKUP_SERVER_NAME = "EC2AMAZ-C4O89E0"
BACKUP_SERVER_PLATFORM = "Windows"
BACKUP_SERVER_EDITION = "EnterprisePlus"
BACKUP_SERVER_BUILD_VERSION = "13.0.3.63"


@dataclass(frozen=True)
class ExpectedServiceResult:
    """The state (0 OK, 1 WARN, 2 CRIT, 3 UNKNOWN) and regular expressions that the summary
    or the details have to contain.

    The values show that the data from Veeam reaches the services. Values the lab is
    configured with are enough for that; measured ones change with every recording. Each
    value comes with its label where it has one.
    """

    state: int
    values: Sequence[str] = ()


EXPECTED_BACKUP_SERVER_SERVICES: Mapping[str, ExpectedServiceResult | None] = {
    "Check_MK": ExpectedServiceResult(0, [r"\[special_veeam\] Success"]),
    "Check_MK Discovery": None,  # the service has to exist, but what it reports is not checked.
    "Check_MK HW/SW Inventory": ExpectedServiceResult(0, [r"Found \d+ inventory entries"]),
    "Veeam License": ExpectedServiceResult(
        0,
        [
            r"\bValid\b",
            rf"Edition: {BACKUP_SERVER_EDITION}\b",
            r"Licensed to: Checkmk\b",
            r"Type: NFR\b",
            r"Auto update: enabled\b",
        ],
    ),
    "Veeam Backup job Disabled_Windows_AP": ExpectedServiceResult(
        0,
        [
            r"Status: Disabled\b",
            r"Result: Success\b",
            r"Target repository: Default Backup Repository\b",
            r"Objects: 1\b",
            r"Type: WindowsAgentBackupServerPolicy\b",
        ],
    ),
    "Veeam Backup job Failing_job": ExpectedServiceResult(
        2,  # CRIT
        [
            r"Result: Failed\b",
            r"Status: Enabled\b",
            r"Objects: 1\b",
            r"Type: LinuxAgentBackupServerPolicy\b",
        ],
    ),
    "Veeam Backup job File_Backup_Job": ExpectedServiceResult(
        0, [r"Result: Success\b", r"Objects: 4\b", r"Type: FileBackup\b"]
    ),
    "Veeam Backup job Never_run_job": ExpectedServiceResult(
        0,
        [
            r"No run has happened yet\b",
            r"Status: Inactive\b",
            r"Objects: 1\b",
            r"Type: FileBackup\b",
        ],
    ),
    "Veeam Backup job Successful_job": ExpectedServiceResult(
        0,
        [
            r"Result: Success\b",
            r"Target repository: Default Backup Repository\b",
            r"Objects: 1\b",
            r"Type: LinuxAgentBackup\b",
        ],
    ),
    "Veeam Configuration backup": ExpectedServiceResult(
        0, [r"Restore points kept: 10\b", r"Encryption: disabled\b"]
    ),
    "Veeam Backup proxy Backup Proxy": ExpectedServiceResult(
        0, [r"\bGeneral purpose\b", r"\bOnline\b", r"Host: This server\b"]
    ),
    "Veeam Backup proxy VMware Backup Proxy": ExpectedServiceResult(
        0, [r"\bVMware vSphere\b", r"\bOnline\b", r"Host: This server\b"]
    ),
    "Veeam Backup repository Performance Extent - Backup Repository on Linux (22d8ed25)": (
        ExpectedServiceResult(0, [r"Host: 172\.31\.26\.65\b", r"Path: /backups\b"])
    ),
    "Veeam Backup repository WinLocal - Default Backup Repository (88788f9e)": ExpectedServiceResult(
        0,
        # Nagios doubles the backslash.
        [rf"Host: {re.escape(BACKUP_SERVER_NAME)}\b", r"Path: c:\\+backup\b"],
    ),
    "Veeam Scale-out repository Scale-out Backup Repository": ExpectedServiceResult(
        0,
        [
            r"Extent Backup Repository on Linux: Normal\b",
            r"Capacity tier: disabled\b",
            r"Archive tier: disabled\b",
            r"Placement policy: DataLocality\b",
        ],
    ),
    "Veeam Protection group Manually Added": ExpectedServiceResult(
        0,  # A disabled protection group is OK by default.
        [r"\bManually added\b", r"\b1 configured computer\b", r"\bDisabled\b"],
    ),
    "Veeam Protection group PG-Linux-Test": ExpectedServiceResult(
        0, [r"\bIndividual computers\b", r"\b1 configured computer\b"]
    ),
    "Veeam Protection group PG-Windows-Test": ExpectedServiceResult(
        0, [r"\bIndividual computers\b", r"\b1 configured computer\b"]
    ),
    "Veeam Managed server 172.31.26.65": ExpectedServiceResult(0, [r"\bLinux\b", r"\bAvailable\b"]),
    f"Veeam Managed server {BACKUP_SERVER_NAME}": ExpectedServiceResult(
        0,
        [
            r"\bMicrosoft Windows\b",
            r"\bAvailable\b",
            r"Roles: Backup server, Default mount server\b",
        ],
    ),
}

EXPECTED_PROTECTED_MACHINE_SERVICES: Mapping[str, ExpectedServiceResult | None] = {
    "Check_MK": ExpectedServiceResult(
        0, [r"\[piggyback\] Successfully processed from source 'veeam-server'"]
    ),
    "Check_MK Discovery": None,
    "Veeam Backup Successful_job": ExpectedServiceResult(0, [r"Status: Success\b"]),
    "Veeam Restore points": ExpectedServiceResult(
        0,
        [
            r"\bMalware status: Clean\b",
            r"Platform: LinuxPhysical\b",
            r"Object type: Directory\b",
        ],
    ),
}


@pytest.fixture(name="veeam_account", scope="module")
def _veeam_account() -> VeeamAccount:
    return VeeamAccount(
        user="Administrator",
        password_variable="VEEAM_SERVER_PASSWORD",
        recording_file=Path(__file__).parent / "recorded_admin_responses.json",
    )


def _assert_service_reports_expected_result(
    host_name: str,
    service_name: str,
    actual_services: Mapping[str, ServiceInfo],
    expected_result: ExpectedServiceResult,
) -> None:
    if (actual_result := actual_services.get(service_name)) is None:
        pytest.fail(f"{service_name!r} not found on {host_name}")
    assert actual_result.state == expected_result.state, (
        f"State of {service_name!r} on {host_name}: expected {expected_result.state}, "
        f"actual {actual_result.state}. Actual summary: {actual_result.summary}"
    )
    actual_output = "\n".join(
        [
            actual_result.summary,
            *re.split(r"\n|\\n", actual_result.extra_columns["long_plugin_output"]),
        ]
    )
    missing_values = [
        value for value in expected_result.values if not re.search(value, actual_output)
    ]
    assert not missing_values, (
        f"Output of {service_name!r} on {host_name}: expected to contain each of "
        f"{missing_values}, actual: {actual_output}"
    )


def _assert_host_has_exactly_the_expected_services(
    *,
    host_name: str,
    actual_services: Mapping[str, ServiceInfo],
    expected_services: Mapping[str, ExpectedServiceResult | None],
) -> None:
    actual_service_names, expected_service_names = set(actual_services), set(expected_services)
    assert actual_service_names == expected_service_names, (
        f"Services on {host_name}: missing {sorted(expected_service_names - actual_service_names)}, "
        f"unexpected {sorted(actual_service_names - expected_service_names)}"
    )


def test_backup_server_has_exactly_the_expected_services(
    backup_server_services: Mapping[str, ServiceInfo],
) -> None:
    _assert_host_has_exactly_the_expected_services(
        host_name=BACKUP_SERVER_HOST_NAME,
        actual_services=backup_server_services,
        expected_services=EXPECTED_BACKUP_SERVER_SERVICES,
    )


def test_protected_machine_has_exactly_the_expected_services(
    protected_machine_services: Mapping[str, ServiceInfo],
) -> None:
    _assert_host_has_exactly_the_expected_services(
        host_name=PROTECTED_MACHINE_HOST_NAME,
        actual_services=protected_machine_services,
        expected_services=EXPECTED_PROTECTED_MACHINE_SERVICES,
    )


@pytest.mark.parametrize(
    "service_name, expected_result",
    [
        # Services without an expected result are only checked for existence.
        pytest.param(service_name, expected_result, id=service_name)
        for service_name, expected_result in EXPECTED_BACKUP_SERVER_SERVICES.items()
        if expected_result is not None
    ],
)
def test_backup_server_service_reports_the_expected_result(
    backup_server_services: Mapping[str, ServiceInfo],
    service_name: str,
    expected_result: ExpectedServiceResult,
) -> None:
    _assert_service_reports_expected_result(
        host_name=BACKUP_SERVER_HOST_NAME,
        service_name=service_name,
        actual_services=backup_server_services,
        expected_result=expected_result,
    )


@pytest.mark.parametrize(
    "service_name, expected_result",
    [
        # Services without an expected result are only checked for existence.
        pytest.param(service_name, expected_result, id=service_name)
        for service_name, expected_result in EXPECTED_PROTECTED_MACHINE_SERVICES.items()
        if expected_result is not None
    ],
)
def test_protected_machine_service_reports_the_expected_result(
    protected_machine_services: Mapping[str, ServiceInfo],
    service_name: str,
    expected_result: ExpectedServiceResult,
) -> None:
    _assert_service_reports_expected_result(
        host_name=PROTECTED_MACHINE_HOST_NAME,
        service_name=service_name,
        actual_services=protected_machine_services,
        expected_result=expected_result,
    )


@pytest.mark.usefixtures("veeam_monitoring_via_special_agent")
def test_backup_server_has_the_veeam_host_labels(site: Site) -> None:
    discovery_result = site.openapi.service_discovery.get_discovery_result(BACKUP_SERVER_HOST_NAME)[
        "extensions"
    ]
    assert isinstance(discovery_result, Mapping) and isinstance(
        discovery_result.get("host_labels"), Mapping
    ), f"The discovery result of {BACKUP_SERVER_HOST_NAME} has no host labels: {discovery_result}"

    actual_veeam_labels = {
        name: label["value"]
        for name, label in discovery_result["host_labels"].items()
        if name.startswith("cmk/veeam_vbr/")
    }

    expected_veeam_labels = {
        "cmk/veeam_vbr/edition": BACKUP_SERVER_EDITION,
        "cmk/veeam_vbr/platform": BACKUP_SERVER_PLATFORM,
    }
    assert actual_veeam_labels == expected_veeam_labels, (
        f"Veeam host labels of {BACKUP_SERVER_HOST_NAME}: expected {expected_veeam_labels}, actual {actual_veeam_labels}. "
        f"All discovered labels: {sorted(discovery_result['host_labels'])}"
    )


@pytest.mark.usefixtures("veeam_monitoring_via_special_agent")
def test_inventory_holds_the_backup_server_version(site: Site) -> None:
    inventory_tree = site.get_inventory_tree(BACKUP_SERVER_HOST_NAME)

    backup_server_attributes = site.get_inventory_attributes(
        inventory_tree, ["software", "applications", "veeam", "backup_server"]
    )

    assert backup_server_attributes.get("build_version") == BACKUP_SERVER_BUILD_VERSION, (
        f"The inventory of {BACKUP_SERVER_HOST_NAME} has the wrong Veeam build version "
        f"(version, update, patch, build), expected {BACKUP_SERVER_BUILD_VERSION}: "
        f"{backup_server_attributes}"
    )
    assert backup_server_attributes.get("name") == BACKUP_SERVER_NAME, (
        f"The inventory of {BACKUP_SERVER_HOST_NAME} names the wrong Veeam backup server: {backup_server_attributes}"
    )
    assert backup_server_attributes.get("platform") == BACKUP_SERVER_PLATFORM, (
        f"The inventory of {BACKUP_SERVER_HOST_NAME} has the wrong Veeam backup server platform: {backup_server_attributes}"
    )


@pytest.mark.usefixtures("veeam_monitoring_via_special_agent")
def test_inventory_holds_the_wan_accelerators(site: Site) -> None:
    inventory_tree = site.get_inventory_tree(BACKUP_SERVER_HOST_NAME)

    wan_accelerators = site.get_inventory_rows(
        inventory_tree, ["software", "applications", "veeam", "wan_accelerators"]
    )

    assert [row.get("name") for row in wan_accelerators] == [BACKUP_SERVER_NAME], (
        f"The inventory of {BACKUP_SERVER_HOST_NAME} has the wrong WAN accelerators: {wan_accelerators}"
    )
