#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generator

import pytest

from tests.testlib.site import Site

from .checks import compare_check_output, update_check_output
from .conftest import LOGGER, run_as_site_user


def test_plugin(
    test_site: Site, setup: Generator, tmp_path_factory: pytest.TempPathFactory
) -> None:
    host_name = "test_agent_plugin_injected"

    LOGGER.info("Running update-config...")
    assert run_as_site_user(test_site.id, ["cmk-update-config"]).returncode == 0

    LOGGER.info("Running service discovery...")
    assert run_as_site_user(test_site.id, ["cmk", "$DEBUG", "-vII"]).returncode == 0

    LOGGER.info("Reloading core...")
    assert run_as_site_user(test_site.id, ["cmk", "-O"]).returncode == 0

    # perform assertion over raw data
    cat_stdout = run_as_site_user(
        test_site.id, ["cat", f"$OMD_ROOT/var/check_mk/agent_output/{host_name}"]
    ).stdout
    discovery_stdout = run_as_site_user(test_site.id, ["cmk", "-d", host_name]).stdout

    assert discovery_stdout == cat_stdout

    output_dir = tmp_path_factory.mktemp("check_output")
    assert compare_check_output(test_site, output_dir), "Check output mismatch!"


@pytest.mark.update_checks
def test_store_update_checks(test_site: Site, setup: Generator) -> None:
    # dump_section_output() TODO: improve section-output  dump function
    assert update_check_output(test_site), "Failed to update check output!"
