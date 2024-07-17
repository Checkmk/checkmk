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
    setup_source_host,
)

logger = logging.getLogger(__name__)


HOSTNAMES = [
    name
    for name in get_host_names()
    if name not in ("agent-2.1.0p11-ms-exchange", "agent-1.2.6b12-win-ad-replication")
]


@pytest.mark.parametrize("source_host_name", HOSTNAMES)
def test_plugin(
    test_site: Site,
    source_host_name: str,
    dcd_connector: None,
    tmp_path_factory: pytest.TempPathFactory,
    pytestconfig: pytest.Config,
) -> None:
    with (
        setup_source_host(test_site, source_host_name)
        if not pytestconfig.getoption(name="--bulk-mode")
        else nullcontext()
    ):
        disk_dump = read_disk_dump(source_host_name)
        dump_type = "snmp" if disk_dump[0] == "." else "agent"
        if dump_type == "agent":
            cmk_dump = read_cmk_dump(source_host_name, test_site, "agent")
            assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        # perform assertion over check data
        tmp_path = tmp_path_factory.mktemp("responses")
        logger.info(tmp_path)
        hostnames = [
            _.get("id") for _ in test_site.openapi.get_hosts()
        ]  # including piggyback hosts
        for hostname in hostnames:
            diffing_checks = process_check_output(test_site, hostname, tmp_path)
            err_msg = f"Check output mismatch for host {hostname}:\n" + "".join(
                [textwrap.dedent(f"{check}:\n" + diffing_checks[check]) for check in diffing_checks]
            )
            assert not diffing_checks, err_msg
