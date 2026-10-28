#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The setup of the Veeam monitoring the tests check.

Each test module sets it up for one Veeam user, which it names in a `veeam_account`
fixture.
"""

import logging
import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

import pytest

from tests.testlib.common.utils2 import ServiceInfo
from tests.testlib.system.site import Site

from .helpers import BACKUP_SERVER_HOST_NAME, PROTECTED_MACHINE_HOST_NAME, VeeamAccount
from .mock_vbr import Credentials, replaying

logger = logging.getLogger(__name__)

# The password the mock accepts. A real server's password comes from the environment.
MOCK_PASSWORD = "mock-veeam-password"

BACKUP_SERVER_PORT = 9419  # Of a real server; the mock listens on a free port.
PASSWORD_ID = "veeam"


@dataclass(frozen=True)
class VeeamServer:
    address: str
    port: int
    credentials: Credentials


@pytest.fixture(name="veeam_server", scope="module")
def _provide_veeam_server(veeam_account: VeeamAccount) -> Iterator[VeeamServer]:
    """Return the Veeam backup server to monitor.

    That is the real server named by VEEAM_SERVER_ADDRESS in the environment, if set,
    with the password of the Veeam user from the environment variable the account names.
    Otherwise start a mocked server, which replays the responses recorded from the lab
    server as the Veeam user, and stop it afterwards. The mock listens on a free port, so that it does not
    clash with anything else on the test host, and accepts only the Veeam user with
    MOCK_PASSWORD.
    """
    if real_server_address := os.environ.get("VEEAM_SERVER_ADDRESS"):
        if not (real_server_password := os.environ.get(veeam_account.password_variable)):
            raise RuntimeError(
                f"VEEAM_SERVER_ADDRESS is set, but {veeam_account.password_variable} is not"
            )
        logger.info(
            "Monitor the real Veeam server at %s as %s", real_server_address, veeam_account.user
        )
        yield VeeamServer(
            real_server_address,
            BACKUP_SERVER_PORT,
            Credentials(veeam_account.user, real_server_password),
        )
        return

    address = "127.0.0.1"
    credentials = Credentials(veeam_account.user, MOCK_PASSWORD)
    with replaying(veeam_account.recording_file, credentials=credentials, address=address) as port:
        logger.info(
            "Monitor the mocked Veeam server at %s:%d as %s", address, port, veeam_account.user
        )
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
    """The password of the Veeam user, in the password store."""
    logger.info("Save the password of the Veeam user in the password store")
    site.openapi.passwords.create(
        PASSWORD_ID,
        f"Veeam {veeam_server.credentials.user} password",
        "comment",
        veeam_server.credentials.password,
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
    veeam_account: VeeamAccount,
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
    if not veeam_account.can_read_all_sections:
        # A tabula rasa skips a host whose data source reports a warning, as the automatic
        # discovery does, so accept the services found despite the warnings.
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            BACKUP_SERVER_HOST_NAME, mode="refresh"
        )
        site.openapi.service_discovery.run_discovery(BACKUP_SERVER_HOST_NAME, mode="fix_all")
    else:
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            BACKUP_SERVER_HOST_NAME
        )
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
