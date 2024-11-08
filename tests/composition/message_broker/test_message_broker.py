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


class _Timeout(RuntimeError):
    pass


@contextmanager
def _timeout(seconds: int, exc: _Timeout) -> Iterator[None]:
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
    with _timeout(3, _Timeout("`cmk-broker-test` did not start in time")):
        for line in stdout:
            if "Waiting for messages" in line:
                return


def pong_received_message(stdout: IO[str], wait_for: int) -> bool:
    """Wait for the cmk-broker-test pong to receive a message"""
    try:
        with _timeout(
            wait_for, _Timeout(f"`cmk-broker-test` did not receive anything within {wait_for}s")
        ):
            for line in stdout:
                if "Received message" in line:
                    return True
    except _Timeout:
        pass
    return False


@contextmanager
def _broker_pong(site: Site) -> Iterator[subprocess.Popen]:
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


def _check_broker_ping(site: Site, destination: str) -> None:
    """Send a message to the site and wait for a response"""
    output = []

    def _collect_output_while_waiting(stream: IO[str]) -> None:
        while line := stream.readline():
            output.append(line)

    try:
        # timeout of 5 seconds should be plenty, we're observing oom ~10ms
        with _timeout(5, _Timeout(f"`cmk-broker-test {destination}` timed out after 5s")):
            ping = site.execute(["cmk-broker-test", destination], stdout=subprocess.PIPE, text=True)
            assert ping.stdout
            _collect_output_while_waiting(ping.stdout)
    finally:
        logger.info("".join(output))


@contextmanager
def _broker_stopped(site: Site) -> Iterator[None]:
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
def _p2p_connection(central_site: Site, remote_site: Site, remote_site_2: Site) -> Iterator[None]:
    """Establish a direct connection between two sites"""
    connection_id = f"comp_test_p2p_{remote_site.id}_{remote_site_2.id}"
    try:
        central_site.openapi.create_broker_connection(
            connection_id, connecter=remote_site.id, connectee=remote_site_2.id
        )
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)
        yield
    finally:
        central_site.openapi.delete_broker_connection(connection_id)
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


@skip_if_saas_edition
class TestCMKBrokerTest:
    """Make sure our cmk-broker-test tool works"""

    def test_ping_ok(self, central_site: Site) -> None:
        """Test if we can ping ourselves"""
        _check_broker_ping(central_site, central_site.id)

    def test_ping_fail(self, central_site: Site) -> None:
        """Test if we can't ping a non-existing site"""
        with pytest.raises(_Timeout):
            _check_broker_ping(central_site, "this-goes-nowhere")

    def test_pong(self, central_site: Site) -> None:
        """Test if we can pong"""
        with _broker_pong(central_site) as pong:
            assert pong.returncode is None  # it's running

    def test_pong_received_message(self, central_site: Site, remote_site: Site) -> None:
        """Test if the `pong_received_message` works as intended"""
        with _broker_pong(central_site) as pong:
            assert pong.stdout  # for mypy
            # nothing received so far
            assert not pong_received_message(pong.stdout, wait_for=1)
            # we can't ping locally, that will bypass the pong
            _check_broker_ping(remote_site, central_site.id)
            # if the _check_broker_ping worked, the pong *must* have received a message
            assert pong_received_message(pong.stdout, wait_for=1)


@skip_if_saas_edition
class TestMessageBroker:
    def test_message_broker_central_remote(self, central_site: Site, remote_site: Site) -> None:
        """Test if the connection between central and remote site works"""
        with _broker_pong(central_site):
            _check_broker_ping(remote_site, central_site.id)

    def test_message_broker_remote_remote_via_central(
        self,
        central_site: Site,
        remote_site: Site,
        remote_site_2: Site,
    ) -> None:
        with _broker_pong(remote_site):
            _check_broker_ping(remote_site_2, remote_site.id)

            # test complement: should not work without the central site running:
            with _broker_stopped(central_site):
                with pytest.raises(_Timeout):
                    _check_broker_ping(remote_site_2, remote_site.id)

    def test_message_broker_remote_remote_p2p(
        self, central_site: Site, remote_site: Site, remote_site_2: Site
    ) -> None:
        with (
            _p2p_connection(central_site, remote_site, remote_site_2),
            _broker_pong(remote_site),
            _broker_stopped(central_site),
        ):
            _check_broker_ping(remote_site_2, remote_site.id)
