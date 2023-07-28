#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Generator

import pytest

from tests.testlib.site import Site

from tests.plugins_integration import constants
from tests.plugins_integration.checks import get_host_names, process_check_output
from tests.plugins_integration.conftest import LOGGER


@pytest.mark.parametrize("host_name", get_host_names())
def test_plugin(
    test_site: Site,
    setup: Generator,
    tmp_path_factory: pytest.TempPathFactory,
    host_name: str,
    request: pytest.FixtureRequest,
) -> None:
    # perform assertion over raw data
    with open(f"{constants.DUMP_DIR_PATH}/{host_name}", "r") as injected_file:
        raw_data = injected_file.read()

    discovery_out, _ = test_site.execute(
        ["cmk", "-d", host_name],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ).communicate()

    assert raw_data == discovery_out != ""

    # perform assertion over check data
    tmp_path = tmp_path_factory.mktemp(constants.RESPONSE_DIR)
    LOGGER.info(tmp_path)
    assert process_check_output(
        test_site,
        host_name,
        tmp_path,
        update_mode=request.config.getoption("--update-checks"),
    ), "Check output mismatch!"
