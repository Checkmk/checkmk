#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import textwrap

import pytest

from tests.testlib.agent_dumps import get_dump_and_walk_names, read_cmk_dump, read_disk_dump
from tests.testlib.site import Site

from tests.plugins_integration.checks import (
    config,
    process_check_output,
    setup_host,
)

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("host_name", get_dump_and_walk_names(config.dump_dir_integration))
def test_plugin(
    test_site: Site,
    host_name: str,
    tmp_path_factory: pytest.TempPathFactory,
    pytestconfig: pytest.Config,
) -> None:
    with setup_host(test_site, host_name):
        disk_dump = read_disk_dump(host_name, config.dump_dir_integration)
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
