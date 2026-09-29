#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="import"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import subprocess

import pytest
import yaml
from testlib.agent_output import read_agent_output

from .local import DEFAULT_CONFIG, host, main_exe, port, run_agent, user_yaml_config


@pytest.fixture
def make_yaml_config():
    yml = yaml.safe_load(DEFAULT_CONFIG.format(port))
    return yml


@pytest.fixture(name="write_config")
def write_config_engine(testconfig):
    with open(user_yaml_config, "w") as yaml_file:
        ret = yaml.dump(testconfig)
        yaml_file.write(ret)
    yield


# Override this in test file(s) to insert a wait before contacting the agent.
@pytest.fixture(name="wait_agent")
def wait_agent_engine():
    def inner():
        return False

    return inner


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "agent_output_may_be_empty: the agent may legitimately send nothing for this test,"
        " so empty output reaches the test instead of failing it",
    )


@pytest.fixture(name="actual_output")
def actual_output_engine(request, write_config, wait_agent):
    empty_ok = request.node.get_closest_marker("agent_output_may_be_empty") is not None
    p = None
    try:
        p = run_agent(main_exe)
        # Override wait_agent in tests to wait for async processes to start.
        wait_agent()

        yield read_agent_output(host, port, empty_ok=empty_ok).splitlines()
    finally:
        if p is not None:
            p.terminate()

            # hammer kill of the process, terminate may be too long
            subprocess.call(
                f'taskkill /F /FI "pid eq {p.pid}" /FI "IMAGENAME eq check_mk_agent.exe"'
            )

        # Possibly wait for async processes to stop.
        wait_agent()
