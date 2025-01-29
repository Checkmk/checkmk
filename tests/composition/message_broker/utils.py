#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import logging
import re
import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType
from typing import IO

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)


class Timeout(RuntimeError):
    pass


@contextmanager
def timeout(seconds: int, exc: Timeout) -> Iterator[None]:
    """Context manager to raise an exception after a timeout"""

    def _raise_timeout(_: int, __: FrameType | None) -> None:
        raise exc

    alarm_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, alarm_handler)


def _get_broker_test_pid(line: str) -> int:
    """Extract the PID from the cmk-broker-test output"""
    if match := re.match(r"cmk-broker-test \[(\d+)\]", line):
        return int(match.group(1))
    raise ValueError(f"Unexpected output from cmk-broker-test: {line}")


def _wait_for_pong_ready(stdout: IO[str]) -> None:
    """Wait for the cmk-broker-test to be ready"""
    with timeout(3, Timeout("`cmk-broker-test` did not start in time")):
        for line in stdout:
            if "Waiting for messages" in line:
                return


@contextmanager
def broker_pong(site: Site) -> Iterator[subprocess.Popen]:
    """Make sure the site echoes messages"""
    pong = site.execute(["cmk-broker-test"], stdout=subprocess.PIPE, text=True)
    assert pong.stdout is not None

    pid = _get_broker_test_pid(pong.stdout.readline())

    _wait_for_pong_ready(pong.stdout)
    logger.info("`cmk-broker-test` found to be ready on %s", site.id)

    # We had a race condition with not received messages. Maybe queue declaration returns too early?
    site.run(["rabbitmqctl", "status"])  # collapse wave function of declared queue

    try:
        yield pong
    finally:
        if pong.returncode is not None:
            err = f"`cmk-broker-test` stopped unexpectedly on {site.id}"
            logger.error(err)
            logger.error("stdout: %s", pong.stdout)
            logger.error("stderr: %s", pong.stderr)
            raise RuntimeError(err)
        site.run(["kill", "-s", "SIGINT", str(pid)])
        pong.wait(timeout=3)


def check_broker_ping(site: Site, destination: str, time_out_: int = 5) -> None:
    """Send a message to the site and wait for a response"""
    output = []

    def _collect_output_while_waiting(stream: IO[str]) -> None:
        while line := stream.readline():
            output.append(line)

    ping = site.execute(
        ["cmk-broker-test", destination],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert ping.stdout
    pid = _get_broker_test_pid(ping.stdout.readline())
    try:
        with timeout(
            time_out_, Timeout(f"`cmk-broker-test {destination}` timed out after {time_out_}s")
        ):
            _collect_output_while_waiting(ping.stdout)

        if "UUIDs match" not in output[-1]:
            raise RuntimeError(
                f"cmk-broker-test received another message from {destination} than sent"
            )
        if ping.stderr is not None and (error_output := ping.stderr.read()):
            logger.error("stderr: %s", error_output)
            raise RuntimeError(f"cmk-broker-test communication with {destination} failed")
    finally:
        # if no response was received, we need to ensure the process is terminated
        with contextlib.suppress(subprocess.CalledProcessError):
            site.run(["kill", "-s", "SIGINT", str(pid)])
        logger.info("".join(output))


def assert_message_exchange_working(site1: Site, site2: Site) -> None:
    # There seems to be a race condition when rabbitmq is reloaded and a new connection is
    # established where messages get lost.
    # Checking for the binding, the queues or the shovels as well as check_port_connectivity
    # did not help, but waiting for some time does
    retries = 10
    time_out_ = 2
    for _ in range(retries):
        with contextlib.suppress(Timeout):
            with broker_pong(site1):
                check_broker_ping(site2, site1.id, time_out_=time_out_)
            break
    else:
        assert False, f"Message exchange not working after {retries} retries"


def assert_message_exchange_not_working(site1: Site, site2: Site) -> None:
    with broker_pong(site1):
        with pytest.raises(Timeout):
            check_broker_ping(site2, site1.id)
    with broker_pong(site2):
        with pytest.raises(Timeout):
            check_broker_ping(site1, site2.id)


@contextmanager
def broker_stopped(site: Site) -> Iterator[None]:
    """Disable the broker on the site"""
    if site.omd("status", "rabbitmq") != 0:
        # broker is not running anyway
        yield
        return

    assert site.omd("stop", "rabbitmq") == 0
    try:
        yield
    finally:
        assert site.omd("start", "rabbitmq") == 0


@contextmanager
def p2p_connection(central_site: Site, remote_site: Site, remote_site_2: Site) -> Iterator[None]:
    """Establish a direct connection between two sites"""
    connection_id = f"comp_test_p2p_{remote_site.id}_{remote_site_2.id}"
    try:
        central_site.openapi.broker_connections.create(
            connection_id, connecter=remote_site.id, connectee=remote_site_2.id
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        central_site.openapi.broker_connections.delete(connection_id)
        central_site.openapi.changes.activate_and_wait_for_completion()
