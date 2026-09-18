#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Importing every agent-based check plugin into the Nagios core."""

import logging
from pathlib import Path

from tests.performance.perftest import PerformanceTest
from tests.performance.sysmon import track_resources
from tests.testlib.common.utils2 import check_output
from tests.testlib.site import PythonHelper

logger = logging.getLogger(__name__)


def setup_nagios_core_plugin_import(perftest: PerformanceTest) -> None:
    """Setup: Nagios core plugin import

    Executes "nagios_core_plugin_import.py" to generate "check_localhost.py",
    which loads all agent based checks.
    """
    helper_path = Path(__file__).parent / "nagios_core_plugin_import.py"
    helper = PythonHelper(perftest.central_site, helper_path)
    helper_stem = helper.helper_path.stem
    perftest.central_site.write_file(f"var/log/{helper_stem}.log", helper.check_output())


def scenario_nagios_core_plugin_import(perftest: PerformanceTest, iterations: int) -> None:
    """Scenario: Nagios core plugin import

    Sequentially runs "check_localhost.py" 10 times per iteration in the site context.

    Uses a small sampling interval to get more meaningful data.
    """
    check_path = perftest.central_site.path(
        "var/check_mk/core/helper_config/latest/host_checks/check_localhost.py"
    )
    assert perftest.central_site.file_exists(check_path), "Check file not found! Aborting."

    cmd = ["python3", check_path.as_posix()]
    logger.info("$ %s", " ".join(cmd))
    with track_resources("test_nagios_core_plugin_import", sampling_interval=0.1):
        for _ in range(iterations * 10):
            check_output(cmd, sudo=True, substitute_user=perftest.central_site.id)
