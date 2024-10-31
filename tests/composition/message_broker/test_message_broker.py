#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from signal import SIGINT

import pytest

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


def _check_broker_ping(site: Site, destination: str) -> None:
    """Send a message to the site and wait for a response"""
    # timeout of 5 seconds should be plenty, we're observing oom ~10ms
    result = site.run(["cmk-broker-test", destination], timeout=5)
    logger.info(result.stdout)


@contextmanager
def _broker_pong(site: Site) -> Iterator[subprocess.Popen]:
    """Make sure the site echoes messages"""
    pong = site.execute(["cmk-broker-test"])
    try:
        yield pong
    finally:
        pong.send_signal(SIGINT)
        try:
            pong.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pong.kill()  # No idea why we need this :-(


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
