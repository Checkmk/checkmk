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

HOST_NAMES = [
    name
    for name in get_host_names()
    if name
    not in (
        "agent-1.2.7i2-zfs-solaris",
        "agent-2.2.0p6-rhel-9.2",
        "agent-2.2.0p9-windows-citrix",
        "agent-2.2.0p8-ceph-17.2.6",
        "agent-2.1.0p33-postgreSQL-14.9",
        "agent-2.2.0-ontapi-9.10",
        "agent-2.1.0p34-cma-1.7",
        "agent-2.2.0p14-windows-mssql",
        "agent-2.1.0p11-ms-exchange",
        "agent-2.1.0p2-f5-bigip",
        "agent-2.0.0p21-aix-7.2-nim",
        "agent-2.1.0p9-postgreSQL-12.0",
        "agent-1.2.4p5-server-solaris",
        "agent-2.2.0p14-windows-dhcp",
        "agent-2.2.0p14-proxmox",
        "agent-2.2.0p14-isc-dhcpd",
        "agent-2.2.0p14-windows-veeam-backup",
        "agent-2.2.0p12-mk-oracle-centos",
        "agent-2.2.0-osx",
        "snmp-opnsense-22.1",
    )
]


@pytest.mark.parametrize("host_name", HOST_NAMES)
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
