#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import subprocess
import time

import pytest
import telnetlib3  # type: ignore[import-untyped]
import yaml

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


_result = ""


async def _telnet_shell(reader: telnetlib3.TelnetReader, _: telnetlib3.TelnetWriter) -> None:
    global _result
    while True:
        data = await reader.read(1024)
        if not data:
            break
        _result += data


def _read_client_data(addr_host: str, addr_port: int) -> None:
    loop = asyncio.get_event_loop()
    coro = telnetlib3.open_connection(addr_host, addr_port, shell=_telnet_shell)
    _, writer = loop.run_until_complete(coro)
    loop.run_until_complete(writer.protocol.waiter_closed)


def _get_data_using_telnet(addr_host: str, addr_port: int) -> str:
    # overloaded CI Node may delay start/init of the agent process
    # we must retry connection few times to avoid complaints
    global _result
    _result = ""
    for _ in range(5):
        try:
            _read_client_data(addr_host, addr_port)
            if _result:
                return _result
            time.sleep(2)
        except Exception:
            # print('No connect, waiting for agent')
            time.sleep(2)

    return ""


@pytest.fixture(name="actual_output")
def actual_output_engine(write_config, wait_agent):
    # Run agent and yield telnet output.
    p = None
    try:
        p = run_agent(main_exe)
        # Override wait_agent in tests to wait for async processes to start.
        wait_agent()

        yield _get_data_using_telnet(host, port).splitlines()
    finally:
        if p is not None:
            p.terminate()

            # hammer kill of the process, terminate may be too long
            subprocess.call(
                f'taskkill /F /FI "pid eq {p.pid}" /FI "IMAGENAME eq check_mk_agent.exe"'
            )

        # Possibly wait for async processes to stop.
        wait_agent()
