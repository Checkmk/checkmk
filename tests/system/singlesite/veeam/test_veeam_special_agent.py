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

import logging
import os
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

import pytest

from tests.testlib.common.utils2 import ServiceInfo
from tests.testlib.system.site import Site

from .mock_vbr import Credentials, RECORDING_FILE, replaying

logger = logging.getLogger(__name__)

# The password the mock accepts. A real server's password comes from the environment.
ADMIN_PASS = "mock-veeam-password"

# The Veeam backup server: how to reach it, and what it reports about itself.
BACKUP_SERVER_PORT = 9419  # Of a real server; the mock listens on a free port.
BACKUP_SERVER_USER = "Administrator"
BACKUP_SERVER_NAME = "EC2AMAZ-C4O89E0"
BACKUP_SERVER_PLATFORM = "Windows"
BACKUP_SERVER_EDITION = "EnterprisePlus"
BACKUP_SERVER_BUILD_VERSION = "13.0.3.63"

BACKUP_SERVER_HOST_NAME = "veeam-server"
PROTECTED_MACHINE_HOST_NAME = "ip-172-31-26-65"
PASSWORD_ID = "veeam_admin"


@dataclass(frozen=True)
class ExpectedServiceResult:
    """The state (0 OK, 1 WARN, 2 CRIT, 3 UNKNOWN) and regular expressions that the start
    of the summary and of one details line each have to match."""

    state: int
    summary: str
    details: Sequence[str] = ()


EXPECTED_BACKUP_SERVER_SERVICES: Mapping[str, ExpectedServiceResult | None] = {
    "Check_MK": ExpectedServiceResult(0, r"\[special_veeam\] Success"),
    "Check_MK Discovery": None,  # the service has to exist, but what it reports is not checked.
    "Check_MK HW/SW Inventory": ExpectedServiceResult(0, r"Found \d+ inventory entries"),
    "Veeam License": ExpectedServiceResult(
        0,
        r"Valid, License expiry: .+, Instances used: \d+\.\d+%$",
        details=[
            rf"Edition: {BACKUP_SERVER_EDITION}$",
            r"Licensed to: Checkmk$",
            r"Type: NFR$",
            r"Auto update: enabled$",
        ],
    ),
    "Backup job Disabled_Windows_AP": ExpectedServiceResult(
        0,
        r"Status: Disabled, Result: Success, Time since last run: .+",
        details=[
            r"Last run time: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            r"Duration: .+",
            r"Target repository: Default Backup Repository$",
            r"Objects: 1$",
            r"Type: WindowsAgentBackupServerPolicy$",
        ],
    ),
    "Backup job Failing_job": ExpectedServiceResult(
        2,  # CRIT
        r"Result: Failed\(!!\), Time since last run: .+",
        details=[
            r"Status: Enabled$",
            r"Duration: .+",
            r"Objects: 1$",
            r"Type: LinuxAgentBackupServerPolicy$",
        ],
    ),
    "Backup job File_Backup_Job": ExpectedServiceResult(
        0,
        r"Result: Success, Time since last run: .+",
        details=[
            r"Status: \w+$",
            r"Duration: .+",
            r"Next run: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            r"Objects: 4$",
            r"Type: FileBackup$",
        ],
    ),
    "Backup job Never_run_job": ExpectedServiceResult(
        0,
        r"No run has happened yet$",
        details=[r"Status: Inactive$", r"Objects: 1$", r"Type: FileBackup$"],
    ),
    "Backup job Successful_job": ExpectedServiceResult(
        0,
        r"Result: Success, Time since last run: .+",
        details=[
            r"Status: \w+$",
            r"Duration: .+",
            r"Target repository: Default Backup Repository$",
            r"Objects: 1$",
            r"Type: LinuxAgentBackup$",
        ],
    ),
    "Configuration backup": ExpectedServiceResult(
        0,
        r"Last successful backup age: .+",
        details=[
            r"Restore points kept: 10$",
            r"Encryption: disabled$",
            r"Target repository ID: 88788f9e-d8f5-4eb4-bc4f-9b3f5403bcec$",
        ],
    ),
    "Backup proxy Backup Proxy": ExpectedServiceResult(
        0,
        r"General purpose, Online$",
        details=[r"Host: This server$", r"Description: Created by Veeam Backup & Replication$"],
    ),
    "Backup proxy VMware Backup Proxy": ExpectedServiceResult(
        0,
        r"VMware vSphere, Online$",
        details=[r"Host: This server$"],
    ),
    "Backup repository Performance Extent - Backup Repository on Linux (22d8ed25)": (
        ExpectedServiceResult(
            0,
            r"Used: \d+\.\d+% - .+ of 18\.3 GiB",
            details=[r"Host: 172\.31\.26\.65$", r"Path: /backups$"],
        )
    ),
    "Backup repository WinLocal - Default Backup Repository (88788f9e)": ExpectedServiceResult(
        0,
        r"Used: \d+\.\d+% - .+ of 200 GiB",
        details=[rf"Host: {re.escape(BACKUP_SERVER_NAME)}$", r"Path: c:\\backup$"],
    ),
    "Scale-out repository Scale-out Backup Repository": ExpectedServiceResult(
        0,
        r"1 extent$",
        details=[
            r"Extent Backup Repository on Linux: Normal$",
            r"Capacity tier: disabled$",
            r"Archive tier: disabled$",
            r"Placement policy: DataLocality$",
        ],
    ),
    "Protection group Manually Added": ExpectedServiceResult(
        0,  # A disabled protection group is OK by default.
        r"Manually added, 1 configured computer, Disabled$",
        details=[r"Description: Contains manually added computers$"],
    ),
    "Protection group PG-Linux-Test": ExpectedServiceResult(
        0,
        r"Individual computers, 1 configured computer$",
        details=[r"Description: .+"],
    ),
    "Protection group PG-Windows-Test": ExpectedServiceResult(
        0,
        r"Individual computers, 1 configured computer$",
        details=[r"Description: .+"],
    ),
    "Managed server 172.31.26.65": ExpectedServiceResult(
        0,
        r"Linux, Available$",
        details=[r"Server ID: 8da3c8d4-0ca3-4a30-99a3-0cf3fd3c8c5c$"],
    ),
    f"Managed server {BACKUP_SERVER_NAME}": ExpectedServiceResult(
        0,
        r"Microsoft Windows, Available$",
        details=[
            r"Description: Backup server$",
            r"Roles: Backup server, Default mount server$",
            r"Server ID: 6745a759-2205-4cd2-b172-8ec8f7e60ef8$",
        ],
    ),
}

EXPECTED_PROTECTED_MACHINE_SERVICES: Mapping[str, ExpectedServiceResult | None] = {
    "Check_MK": ExpectedServiceResult(
        0, r"\[piggyback\] Successfully processed from source 'veeam-server'"
    ),
    "Check_MK Discovery": None,
    "Backup Successful_job": ExpectedServiceResult(
        0,
        r"Status: Success \(Success\), Last backup age: .+, "
        r"Size: .+ \(read: .+, transferred: .+\)$",
        details=[r"Duration: .+"],
    ),
    "Restore points": ExpectedServiceResult(
        0,
        r"Last restore point age: .+, [1-9]\d* restore points$",
        details=[
            r"Malware status: Clean$",
            r"Platform: LinuxPhysical$",
            r"Object type: Directory$",
            r"Last restore point type: \w+$",
            r"Last restore point malware status: Clean$",
        ],
    ),
}


@dataclass(frozen=True)
class VeeamServer:
    address: str
    port: int
    credentials: Credentials


@pytest.fixture(name="veeam_server", scope="module")
def _provide_veeam_server() -> Iterator[VeeamServer]:
    """Return the Veeam backup server to monitor.

    That is the real server named by VEEAM_SERVER_ADDRESS and VEEAM_SERVER_PASSWORD in the
    environment, if set. Otherwise start a mocked server, which replays the responses
    recorded from the lab server, and stop it afterwards. The mock listens on a free port,
    so that it does not clash with anything else on the test host, and accepts only
    BACKUP_SERVER_USER with ADMIN_PASS.
    """
    if real_server_address := os.environ.get("VEEAM_SERVER_ADDRESS"):
        if not (real_server_password := os.environ.get("VEEAM_SERVER_PASSWORD")):
            raise RuntimeError("VEEAM_SERVER_ADDRESS is set, but VEEAM_SERVER_PASSWORD is not")
        logger.info("Monitor the real Veeam server at %s", real_server_address)
        yield VeeamServer(
            real_server_address,
            BACKUP_SERVER_PORT,
            Credentials(BACKUP_SERVER_USER, real_server_password),
        )
        return

    address = "127.0.0.1"
    credentials = Credentials(BACKUP_SERVER_USER, ADMIN_PASS)
    with replaying(RECORDING_FILE, credentials=credentials, address=address) as port:
        logger.info("Monitor the mocked Veeam server at %s:%d", address, port)
        yield VeeamServer(address, port, credentials)


# The setup is split into fixtures that each create one object on the site (password,
# host, rule) and remove it again afterwards. pytest tears them down one by one, in the
# reverse order of their dependencies, and a failing teardown does not skip the others.
# The changes are activated once, after all objects are removed.


@pytest.fixture(name="activate_changes_on_teardown", scope="module")
def _activate_changes_on_teardown(site: Site) -> Iterator[None]:
    """Activate the changes once all fixtures depending on this one have removed theirs."""
    yield
    site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(name="veeam_password", scope="module")
def _veeam_password(
    site: Site,
    veeam_server: VeeamServer,
    activate_changes_on_teardown: None,  # noqa: ARG001  # Needed for the teardown
) -> Iterator[None]:
    """The password of the Veeam admin user, in the password store."""
    logger.info("Save the Veeam admin password in the password store")
    site.openapi.passwords.create(
        PASSWORD_ID, "Veeam admin password", "comment", veeam_server.credentials.password
    )
    yield
    site.openapi.passwords.delete(PASSWORD_ID)


@pytest.fixture(name="backup_server_host", scope="module")
def _backup_server_host(
    site: Site,
    veeam_server: VeeamServer,
    activate_changes_on_teardown: None,  # noqa: ARG001  # Needed for the teardown
) -> Iterator[None]:
    """The host of the Veeam backup server, monitored via the special agent."""
    logger.info("Create the host for the Veeam backup server")
    site.openapi.hosts.create(
        hostname=BACKUP_SERVER_HOST_NAME,
        folder="/",
        attributes={"ipaddress": veeam_server.address, "tag_agent": "special-agents"},
    )
    yield
    site.openapi.hosts.delete(BACKUP_SERVER_HOST_NAME)


@pytest.fixture(name="protected_machine_host", scope="module")
def _protected_machine_host(
    site: Site,
    activate_changes_on_teardown: None,  # noqa: ARG001  # Needed for the teardown
) -> Iterator[None]:
    """The host of a machine the backup server protects."""
    logger.info("Create the host for the protected machine")
    site.openapi.hosts.create(
        hostname=PROTECTED_MACHINE_HOST_NAME,
        folder="/",
        attributes={"tag_address_family": "no-ip", "tag_agent": "no-agent"},
    )
    yield
    site.openapi.hosts.delete(PROTECTED_MACHINE_HOST_NAME)


@pytest.fixture(name="special_agent_rule", scope="module")
def _special_agent_rule(
    site: Site,
    veeam_server: VeeamServer,
    veeam_password: None,  # noqa: ARG001  # The rule uses the stored password
) -> Iterator[None]:
    """The 'Veeam Backup & Replication' rule for the backup server."""
    logger.info("Create a 'Veeam Backup & Replication' rule")
    rule_id = site.openapi.rules.create(
        value={
            "connection": ("ip_address", None),
            "port": veeam_server.port,
            "user": veeam_server.credentials.user,
            "password": ("cmk_postprocessed", "stored_password", (PASSWORD_ID, "")),
            "disable_cert_verification": True,
            "sections": [
                "veeam_server_info",
                "veeam_license",
                "veeam_backup_jobs",
                "veeam_backups",
                "veeam_replicas",
                "veeam_protection_groups",
                "veeam_managed_servers",
                "veeam_wan_accelerators",
                "veeam_config_backup",
                "veeam_proxies",
                "veeam_repositories",
                "veeam_scaleout_repositories",
                "veeam_restore_points",
            ],
        },
        ruleset_name="special_agents:veeam",
        folder="/",
        conditions={"host_name": {"match_on": [BACKUP_SERVER_HOST_NAME], "operator": "one_of"}},
    )
    yield
    site.openapi.rules.delete(rule_id)


@pytest.fixture(name="inventory_rule", scope="module")
def _inventory_rule(
    site: Site,
    activate_changes_on_teardown: None,  # noqa: ARG001  # Needed for the teardown
) -> Iterator[None]:
    """The rule that runs the HW/SW inventory of the backup server."""
    logger.info("Set up the HW/SW inventory for the Veeam backup server")
    rule_id = site.openapi.rules.create(
        value={"status_data_inventory": True},
        ruleset_name="active_checks:cmk_inv",
        folder="/",
        conditions={"host_name": {"match_on": [BACKUP_SERVER_HOST_NAME], "operator": "one_of"}},
    )
    yield
    site.openapi.rules.delete(rule_id)


@pytest.fixture(name="veeam_monitoring_via_special_agent", scope="module")
def _set_up_veeam_monitoring_via_special_agent(
    site: Site,
    backup_server_host: None,  # noqa: ARG001  # Needed for the setup
    protected_machine_host: None,  # noqa: ARG001  # Needed for the setup
    special_agent_rule: None,  # noqa: ARG001  # Needed for the setup
    inventory_rule: None,  # noqa: ARG001  # Needed for the setup
) -> None:
    """Monitor a Veeam backup server and a machine it protects via the Veeam special agent.

    Discovers and checks the services of both hosts and runs the backup server's HW/SW
    inventory.
    """
    logger.info("Run service discovery on both hosts and activate the changes")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(BACKUP_SERVER_HOST_NAME)
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(
        PROTECTED_MACHINE_HOST_NAME
    )
    site.activate_changes_and_wait_for_core_reload()

    logger.info("Run the checks and the HW/SW inventory")
    site.schedule_check(BACKUP_SERVER_HOST_NAME, "Check_MK")
    site.schedule_check(PROTECTED_MACHINE_HOST_NAME, "Check_MK")
    site.schedule_check(BACKUP_SERVER_HOST_NAME, "Check_MK HW/SW Inventory")


@pytest.fixture(name="backup_server_services", scope="module")
def _backup_server_services(
    site: Site,
    veeam_monitoring_via_special_agent: None,  # noqa: ARG001  # Needed for the setup
) -> Mapping[str, ServiceInfo]:
    """The services of the Veeam backup server host, read once after the setup."""
    return site.get_host_services(BACKUP_SERVER_HOST_NAME, extra_columns=("long_plugin_output",))


@pytest.fixture(name="protected_machine_services", scope="module")
def _protected_machine_services(
    site: Site,
    veeam_monitoring_via_special_agent: None,  # noqa: ARG001  # Needed for the setup
) -> Mapping[str, ServiceInfo]:
    """The services of the protected machine host, read once after the setup."""
    return site.get_host_services(
        PROTECTED_MACHINE_HOST_NAME, extra_columns=("long_plugin_output",)
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
    assert re.match(expected_result.summary, actual_result.summary), (
        f"Summary of {service_name!r} on {host_name}: expected to match "
        f"{expected_result.summary!r}, actual: {actual_result.summary}"
    )
    actual_detail_lines = re.split(r"\n|\\n", actual_result.extra_columns["long_plugin_output"])
    unmatched_detail_patterns = [
        pattern
        for pattern in expected_result.details
        if not any(re.match(pattern, line) for line in actual_detail_lines)
    ]
    assert not unmatched_detail_patterns, (
        f"Details of {service_name!r} on {host_name}: expected a line matching each of "
        f"{unmatched_detail_patterns}, actual: {actual_detail_lines}"
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
