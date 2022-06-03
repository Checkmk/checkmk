#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import telnetlib  # nosec
import time

import pytest
import yaml

from .local import DEFAULT_CONFIG, host, main_exe, port, run_agent, user_yaml_config


@pytest.fixture
def make_yaml_config():
    yml = yaml.safe_load(DEFAULT_CONFIG.format(port))
    return yml


@pytest.fixture(name="write_config")
def write_config_engine(testconfig):
    with open(user_yaml_config, "wt") as yaml_file:
        ret = yaml.dump(testconfig)
        yaml_file.write(ret)
    yield


# Override this in test file(s) to insert a wait before contacting the agent.
@pytest.fixture(name="wait_agent")
def wait_agent_engine():
    def inner():
        return False

    return inner


@pytest.fixture(name="actual_output")
def actual_output_engine(write_config, wait_agent):
    # Run agent and yield telnet output.
    telnet, p = None, None
    try:
        p = run_agent(main_exe)

        # Override wait_agent in tests to wait for async processes to start.
        wait_agent()

        for _ in range(0, 5):
            try:
                telnet = telnetlib.Telnet(host, port)  # nosec
                break
            except Exception as _:
                # print('No connect, waiting for agent')
                time.sleep(1)

        if telnet is None:
            raise ConnectionRefusedError("can't connect")

        result = telnet.read_all().decode(encoding="cp1252")

        yield result.splitlines()
    finally:
        if telnet:
            telnet.close()

        if p:
            p.terminate()

        # hammer kill of the process, terminate may be too long
        subprocess.call(f'taskkill /F /FI "pid eq {p.pid}" /FI "IMAGENAME eq check_mk_agent.exe"')

        # Possibly wait for async processes to stop.
        wait_agent()
