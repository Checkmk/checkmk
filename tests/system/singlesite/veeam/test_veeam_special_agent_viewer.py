#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests of the Veeam special agent connecting as a user with the Veeam Backup Viewer role.

The special agent leaves out the sections the Viewer is denied and warns about them.
Only this difference to the Administrator is checked; what the other sections report
is checked by test_veeam_special_agent.py. That includes the protected machine, whose
sections the Viewer may read.
"""

import re
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.testlib.common.utils2 import ServiceInfo

from .helpers import BACKUP_SERVER_HOST_NAME, VeeamAccount

# The sections a Viewer may not read, with the endpoint each is denied on.
DENIED_SECTIONS: Mapping[str, str] = {
    "veeam_server_info": "/api/v1/serverInfo",
    "veeam_license": "/api/v1/license",
    "veeam_replicas": "/api/v1/replicas",
    "veeam_protection_groups": "/api/v1/agents/protectionGroups",
    "veeam_wan_accelerators": "/api/v1/backupInfrastructure/wanAccelerators",
    "veeam_config_backup": "/api/v1/configBackup",
}

# Without the services of the denied sections: Veeam License, Configuration backup and
# Protection group.
EXPECTED_BACKUP_SERVER_SERVICES = {
    "Check_MK",
    "Check_MK Discovery",
    "Check_MK HW/SW Inventory",
    "Backup job Disabled_Windows_AP",
    "Backup job Failing_job",
    "Backup job File_Backup_Job",
    "Backup job Never_run_job",
    "Backup job Successful_job",
    "Backup proxy Backup Proxy",
    "Backup proxy VMware Backup Proxy",
    "Backup repository Performance Extent - Backup Repository on Linux (22d8ed25)",
    "Backup repository WinLocal - Default Backup Repository (88788f9e)",
    "Scale-out repository Scale-out Backup Repository",
    "Managed server 172.31.26.65",
    "Managed server EC2AMAZ-C4O89E0",
}

_DENIED_SECTION_WARNING = re.compile(
    r"Could not create section '(\w+)': denied permission to endpoint (/[\w/]+)"
)


@pytest.fixture(name="veeam_account", scope="module")
def _veeam_account() -> VeeamAccount:
    return VeeamAccount(
        user="veeam-viewer",
        password_variable="VEEAM_VIEWER_PASSWORD",
        recording_file=Path(__file__).parent / "recorded_viewer_responses.json",
        can_read_all_sections=False,
    )


def test_backup_server_has_only_the_services_a_viewer_may_read(
    backup_server_services: Mapping[str, ServiceInfo],
) -> None:
    actual_service_names = set(backup_server_services)
    assert actual_service_names == EXPECTED_BACKUP_SERVER_SERVICES, (
        f"Services on {BACKUP_SERVER_HOST_NAME}: "
        f"missing {sorted(EXPECTED_BACKUP_SERVER_SERVICES - actual_service_names)}, "
        f"unexpected {sorted(actual_service_names - EXPECTED_BACKUP_SERVER_SERVICES)}"
    )


def test_check_mk_service_warns_about_exactly_the_denied_sections(
    backup_server_services: Mapping[str, ServiceInfo],
) -> None:
    check_mk = backup_server_services["Check_MK"]

    actual_denied_sections = dict(_DENIED_SECTION_WARNING.findall(check_mk.summary))

    assert check_mk.state == 1, (
        f"State of 'Check_MK' on {BACKUP_SERVER_HOST_NAME}: expected 1 (WARN, the default "
        f"state of a special agent warning), actual {check_mk.state}. "
        f"Summary: {check_mk.summary}"
    )
    assert actual_denied_sections == DENIED_SECTIONS, (
        f"'Check_MK' on {BACKUP_SERVER_HOST_NAME} warns about the wrong denied sections: "
        f"expected {DENIED_SECTIONS}, actual {actual_denied_sections}. "
        f"Summary: {check_mk.summary}"
    )


def test_inventory_finds_no_data(
    backup_server_services: Mapping[str, ServiceInfo],
) -> None:
    # The backup server's inventory data all comes from sections only an Administrator may
    # read. An inventory that finds nothing saves no tree, so check what the service says.
    # It repeats the special agent's warnings about the denied sections, hence WARN.
    inventory = backup_server_services["Check_MK HW/SW Inventory"]

    assert inventory.state == 1, (
        f"State of 'Check_MK HW/SW Inventory' on {BACKUP_SERVER_HOST_NAME}: expected 1 "
        f"(WARN), actual {inventory.state}. Summary: {inventory.summary}"
    )
    assert inventory.summary.startswith("Found no data"), (
        f"'Check_MK HW/SW Inventory' on {BACKUP_SERVER_HOST_NAME} found data: {inventory.summary}"
    )
