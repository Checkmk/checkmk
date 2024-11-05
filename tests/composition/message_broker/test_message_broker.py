#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import re
import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO

import pytest

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@contextmanager
def _timeout(seconds: int, exc: Exception) -> Iterator[None]:
    """Context manager to raise an exception after a timeout"""

    def _raise_timeout(signum, frame):
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
    with _timeout(3, RuntimeError("cmk-broker-test did not start in time")):
        for line in stdout:
            if "Waiting for messages" in line:
                return


@contextmanager
def _broker_pong(site: Site) -> Iterator[subprocess.Popen]:
    """Make sure the site echoes messages"""
    pong = site.execute(["cmk-broker-test"], stdout=subprocess.PIPE, text=True)
    assert pong.stdout is not None

    pid = _get_broker_test_pid(pong.stdout.readline())

    _wait_for_pong_ready(pong.stdout)

    try:
        yield pong
    finally:
        site.run(["kill", "-s", "SIGINT", str(pid)])
        pong.wait(timeout=3)


def _check_broker_ping(site: Site, destination: str) -> None:
    """Send a message to the site and wait for a response"""
    # timeout of 5 seconds should be plenty, we're observing oom ~10ms
    result = site.run(["cmk-broker-test", destination], timeout=5)
    logger.info(result.stdout)


@skip_if_saas_edition
class TestCMKBrokerTest:
    """Make sure our cmk-broker-test tool works"""

    def test_ping_ok(self, central_site: Site) -> None:
        """Test if we can ping ourselves"""
        _check_broker_ping(central_site, central_site.id)

    def test_ping_fail(self, central_site: Site) -> None:
        """Test if we can't ping a non-existing site"""
        with pytest.raises(subprocess.TimeoutExpired):
            _check_broker_ping(central_site, "this-goes-nowhere")

    def test_pong(self, central_site: Site) -> None:
        """Test if we can pong"""
        with _broker_pong(central_site) as pong:
            assert pong.returncode is None  # it's running


@skip_if_saas_edition
class TestMessageBroker:
    def test_message_broker_central_remote(self, central_site: Site, remote_site: Site) -> None:
        """Test if the connection between central and remote site works"""
        with _broker_pong(central_site):
            _check_broker_ping(remote_site, central_site.id)
