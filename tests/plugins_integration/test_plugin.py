#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site

from tests.plugins_integration import constants
from tests.plugins_integration.checks import (
    get_host_names,
    process_check_output,
    read_cmk_dump,
    read_disk_dump,
    setup_host,
)
from tests.plugins_integration.conftest import LOGGER


@pytest.mark.parametrize("host_name", get_host_names())
def test_single(
    test_site: Site,
    host_name: str,
    tmp_path_factory: pytest.TempPathFactory,
    request: pytest.FixtureRequest,
) -> None:
    """Atomic execution (done if --bulk-mode is not set)"""
    with setup_host(test_site, host_name):
        disk_dump = read_disk_dump(host_name)
        dump_type = "snmp" if disk_dump[0] == "." else "agent"
        if dump_type == "agent":
            cmk_dump = read_cmk_dump(host_name, test_site, "agent")
            assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        # perform assertion over check data
        tmp_path = tmp_path_factory.mktemp(constants.RESPONSE_DIR)
        LOGGER.info(tmp_path)
        assert process_check_output(
            test_site,
            host_name,
            tmp_path,
            update_mode=request.config.getoption("--update-checks"),
            apply_regexps=not request.config.getoption("--skip-masking"),
        ), "Check output mismatch!"


@pytest.mark.usefixtures("bulk_setup")
@pytest.mark.parametrize("host_name", get_host_names())
def test_bulk(
    test_site: Site,
    host_name: str,
    tmp_path_factory: pytest.TempPathFactory,
    request: pytest.FixtureRequest,
) -> None:
    """Bulk mode execution (done if --bulk-mode is set)"""
    disk_dump = read_disk_dump(host_name)
    dump_type = "snmp" if disk_dump[0] == "." else "agent"
    if dump_type == "agent":
        cmk_dump = read_cmk_dump(host_name, test_site, "agent")
        assert disk_dump == cmk_dump != "", "Raw data mismatch!"

    # perform assertion over check data
    tmp_path = tmp_path_factory.mktemp(constants.RESPONSE_DIR)
    LOGGER.info(tmp_path)
    assert process_check_output(
        test_site,
        host_name,
        tmp_path,
        update_mode=request.config.getoption("--update-checks"),
        apply_regexps=not request.config.getoption("--skip-masking"),
    ), "Check output mismatch!"
