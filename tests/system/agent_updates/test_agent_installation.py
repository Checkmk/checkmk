#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Installing the agent package of the site on the host under test."""

from pathlib import Path

import pytest

from tests.testlib.system.agent import install_agent_package
from tests.testlib.system.host_under_test import HostUnderTest

pytestmark = pytest.mark.skip_if_faked_artifacts


def test_installed_agent_reports_data(host: HostUnderTest, agent_package: Path) -> None:
    install_agent_package(agent_package, host)

    output = host.run(["check_mk_agent"], sudo=True).stdout

    assert output.startswith("<<<check_mk>>>"), (
        f"The installed agent does not start its output with the check_mk section.\n{output}"
    )
