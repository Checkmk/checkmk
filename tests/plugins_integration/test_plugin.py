#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import textwrap
from contextlib import nullcontext

import pytest

from tests.testlib.site import Site

from tests.plugins_integration.checks import (
    get_host_names,
    process_check_output,
    read_cmk_dump,
    read_disk_dump,
    setup_host,
)

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "host_name",
    [
        host_name
        for host_name in get_host_names()
        if host_name
        not in (
            "snmp-citrix-netscaler-11.1",
            "snmp-cisco-router",
            "snmp-switch-dell-n3048p",
            "snmp-switch-cisco-redundancy",
            "snmp-idrac",
            "snmp-switch-dell-powerconnect-m8024",
            "snmp-brocade-router-5.7.0",
            "snmp-sky-cisco-asa-9.9",
            "snmp-checkpoint-firewall",
            "snmp-switch-cisco-powersupplies",
            "snmp-sw-arista.demo.checkmk.com_2_2_p12",
            "snmp-switch-dell-s4820t",
            "snmp-switch-cisco-nexus-n7700",
            "snmp-switch-cisco-c6509",
            "snmp-switch-hp-procurve-j9851a",
            "snmp-switch-hp-procurve-j4819a",
            "snmp-dell-openmanage",
            "snmp-opnsense-22.1",
            "snmp-juniper",
            "snmp-f5-bigip-failover-cluster",
            "snmp-meraki-switch",
            "snmp-fcswitch-brocade",
        )
    ],
)
def test_plugin(
    test_site: Site,
    host_name: str,
    tmp_path_factory: pytest.TempPathFactory,
    pytestconfig: pytest.Config,
) -> None:
    with (
        setup_host(test_site, host_name)
        if not pytestconfig.getoption(name="--bulk-mode")
        else nullcontext()
    ):
        disk_dump = read_disk_dump(host_name)
        dump_type = "snmp" if disk_dump[0] == "." else "agent"
        if dump_type == "agent":
            cmk_dump = read_cmk_dump(host_name, test_site, "agent")
            assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        # perform assertion over check data
        tmp_path = tmp_path_factory.mktemp("responses")
        logger.info(tmp_path)

        diffing_checks = process_check_output(test_site, host_name, tmp_path)
        err_msg = f"Check output mismatch for host {host_name}:\n" + "".join(
            [textwrap.dedent(f"{check}:\n" + diffing_checks[check]) for check in diffing_checks]
        )
        assert not diffing_checks, err_msg
