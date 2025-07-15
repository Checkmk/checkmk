#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.testlib.site import Site

from tests.plugins_integration.checks import setup_host


def test_management_board_services_receive_data(test_site: Site) -> None:
    """Test that management board services receive data.

    Steps:
    1. Inject the desired SNMP file in the test-site
    2. Create a new host that uses such file as datasource
    3. Enable the "Management board" in such a host, using the SNMP protocol
    4. Assert the management board services are correctly discovered,
       they all receive data and they are in state 0
    """
    host_name = "snmp-cisco-router"

    assert test_site.file_exists(f"var/check_mk/snmpwalks/{host_name}"), (
        f"SNMP file for {host_name} not injected"
    )

    with setup_host(test_site, host_name, management_board=True):
        management_board_services = {
            service_name: service_info
            for service_name, service_info in test_site.get_host_services(
                host_name, extra_columns=["has_been_checked"]
            ).items()
            if service_name.lower().startswith("management interface:")
        }
        assert len(management_board_services) > 0, "Management board services not found"

        for service_name, service_info in management_board_services.items():
            assert service_info.extra_columns["has_been_checked"] == 1, (
                f"Service '{service_name}' is stale"
            )
            assert service_info.state == 0, (
                f"Service '{service_name}' is not OK; actual state: {service_info.state}"
            )
