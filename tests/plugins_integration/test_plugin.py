#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from typing import Generator

import pytest

from tests.testlib.site import Site

from .checks import compare_check_output, update_check_output
from .conftest import LOGGER


def test_plugin(
    test_site: Site, setup: Generator, tmp_path_factory: pytest.TempPathFactory
) -> None:
    host_name = "test_agent_plugin_injected"

    LOGGER.info("Running update-config...")
    assert test_site.execute(["cmk-update-config"]).wait() == 0

    LOGGER.info("Running service discovery...")
    assert test_site.execute(["cmk", "-vI"]).wait() == 0

    LOGGER.info("Reloading core...")
    assert test_site.execute(["cmk", "-O"]).wait() == 0

    # perform assertion over raw data
    cat_out, _ = test_site.execute(
        ["cat", f"{test_site.root}/var/check_mk/agent_output/{host_name}"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ).communicate()

    discovery_out, _ = test_site.execute(
        ["cmk", "-d", host_name],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ).communicate()

    assert cat_out == discovery_out != ""

    # perform assertion over check data
    assert compare_check_output(
        test_site, tmp_path_factory.mktemp("check_output")
    ), "Check output mismatch!"


@pytest.mark.update_checks
def test_store_update_checks(
    test_site: Site, setup: Generator, tmp_path_factory: pytest.TempPathFactory
) -> None:
    # dump_section_output() TODO: improve section-output  dump function
    assert update_check_output(
        test_site, tmp_path_factory.mktemp("check_output")
    ), "Failed to update check output!"
