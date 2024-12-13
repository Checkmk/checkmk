#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from tests.testlib.site import Site

from .lib import get_service, get_services, Hosts


def test_datasource_ok(site: Site, redfish_hosts: Hosts) -> None:
    checkmk_service = get_service(site, redfish_hosts.hpe_ok, "Check_MK")
    assert checkmk_service.state == 0
    assert "[special_redfish] Success" in checkmk_service.plugin_output


def test_host_labels(site: Site, redfish_hosts: Hosts) -> None:
    raw = site.openapi.service_discovery.get_discovery_result(redfish_hosts.hpe_ok)["extensions"]
    assert isinstance(raw, Mapping)

    discovered_labels = raw["host_labels"]
    assert {k: v["value"] for k, v in discovered_labels.items()} == {
        "cmk/os_family": "redfish",
        "cmk/os_name": "iLO 6",
        "cmk/os_platform": "HPE",
        "cmk/os_type": "redfish",
        "cmk/os_version": "1.54",
    }


def test_no_agent_service(site: Site, redfish_hosts: Hosts) -> None:
    assert "check_mk-checkmk_agent" not in {
        s.check_command for s in get_services(site, redfish_hosts.hpe_ok)
    }


def test_plugins(site: Site, redfish_hosts: Hosts) -> None:
    """We try to not be too specific here.

    Make sure that all expected plugins are present and OK.
    """
    services = get_services(site, redfish_hosts.hpe_ok)

    assert not {s for s in services if s.state != 0}
    assert {s.check_command for s in services} >= {
        "check_mk-redfish_drives",
        "check_mk-redfish_ethernetinterfaces",
        "check_mk-redfish_fans",
        "check_mk-redfish_firmware",
        "check_mk-redfish_memory",
        "check_mk-redfish_memory_summary",
        "check_mk-redfish_networkadapters",
        "check_mk-redfish_processors",
        "check_mk-redfish_psu",
        "check_mk-redfish_storage",
        "check_mk-redfish_system",
        "check_mk-redfish_temperatures",
        "check_mk-redfish_volumes",
    }
