#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import IO

import pytest

from tests.composition.message_broker.utils import (
    assert_message_exchange_working,
    broker_pong,
    broker_stopped,
    check_broker_ping,
    p2p_connection,
    Timeout,
    timeout,
)

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


def pong_received_message(stdout: IO[str], wait_for: int) -> bool:
    """Wait for the cmk-broker-test pong to receive a message"""
    try:
        with timeout(
            wait_for, Timeout(f"`cmk-broker-test` did not receive anything within {wait_for}s")
        ):
            for line in stdout:
                if "Received message" in line:
                    return True
    except Timeout:
        pass
    return False


@skip_if_saas_edition
class TestCMKBrokerTest:
    """Make sure our cmk-broker-test tool works"""

    def test_ping_ok(self, central_site: Site) -> None:
        """Test if we can ping ourselves"""
        check_broker_ping(central_site, central_site.id)

    def test_ping_fail(self, central_site: Site) -> None:
        """Test if we can't ping a non-existing site"""
        with pytest.raises(Timeout):
            check_broker_ping(central_site, "this-goes-nowhere")

    def test_pong(self, central_site: Site) -> None:
        """Test if we can pong"""
        with broker_pong(central_site) as pong:
            assert pong.returncode is None  # it's running

    def test_pong_received_message(self, central_site: Site, remote_site: Site) -> None:
        """Test if the `pong_received_message` works as intended"""
        with broker_pong(central_site) as pong:
            assert pong.stdout  # for mypy
            # nothing received so far
            assert not pong_received_message(pong.stdout, wait_for=1)
            # we can't ping locally, that will bypass the pong
            check_broker_ping(remote_site, central_site.id)
            # if the _check_broker_ping worked, the pong *must* have received a message
            assert pong_received_message(pong.stdout, wait_for=1)


def _next_free_port(site: Site, key: str, port: str) -> int:
    return int(site.run(["lib/omd/next_free_port", key, port]).stdout.strip())


@skip_if_saas_edition
class TestMessageBroker:
    def test_message_broker_central_remote(self, central_site: Site, remote_site: Site) -> None:
        """Test if the connection between central and remote site works"""
        assert_message_exchange_working(central_site, remote_site)

    def test_message_broker_remote_remote_via_central(
        self,
        central_site: Site,
        remote_site: Site,
        remote_site_2: Site,
    ) -> None:
        with broker_pong(remote_site):
            # test complement: should not work without the central site running:
            with broker_stopped(central_site):
                with pytest.raises(Timeout):
                    check_broker_ping(remote_site_2, remote_site.id)

            check_broker_ping(remote_site_2, remote_site.id)

    def test_message_broker_remote_remote_p2p(
        self, central_site: Site, remote_site: Site, remote_site_2: Site
    ) -> None:
        with (
            p2p_connection(central_site, remote_site, remote_site_2),
            broker_pong(remote_site),
            broker_stopped(central_site),
        ):
            check_broker_ping(remote_site_2, remote_site.id)
