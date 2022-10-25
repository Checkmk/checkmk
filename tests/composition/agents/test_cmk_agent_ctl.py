#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from pathlib import Path

import pytest

from tests.testlib.utils import is_containerized

from tests.composition.utils import execute, install_package

# Skip all agent controller tests if we are not in a container to avoid messing up your machine
pytestmark = pytest.mark.skipif(
    not is_containerized(),
    reason=(
        "tests will install an actual agent on the machine where they are running and we want to avoid"
        " messing up your local environment"
    ),
)


@pytest.fixture(scope="module")
def agent_ctl(bake_test_agent: tuple[str, Path]) -> Path:
    _agent_hash, agent_path = bake_test_agent
    install_result = install_package(agent_path)
    if install_result.returncode != 0:
        raise ValueError(
            f"Error while installing cmk agent:\nstderr:\n{install_result.stderr}"
            f"\nstdout:\n{install_result.stdout}"
        )
    return Path("/usr/bin/cmk-agent-ctl")


def test_agent_controller_installed(agent_ctl: Path) -> None:
    res = execute([agent_ctl.as_posix(), "--help"])
    assert "Checkmk agent controller.\n\nUsage:" in res.stdout
