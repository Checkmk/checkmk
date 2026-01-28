#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import ssl
from pathlib import Path
from typing import IO

import pytest

from tests.composition.message_broker.utils import (
    assert_message_exchange_not_working,
    assert_message_exchange_working,
    await_broker_ready,
    broker_pong,
    broker_stopped,
    check_broker_ping,
    p2p_connection,
    rabbitmq_info_on_failure,
    Timeout,
    timeout,
)
from tests.testlib.site import Site
from tests.testlib.tls import CMKTLSError, tls_connect

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.skip("CMK-29677: suspicious message broker tests")


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


@pytest.mark.skip_if_edition("cloud")
class TestCMKBrokerTest:
    """Make sure our cmk-broker-test tool works"""

    def test_ping_ok(self, central_site: Site) -> None:
        """Test if we can ping ourselves"""
        with rabbitmq_info_on_failure([central_site]):
            check_broker_ping(central_site, central_site.id)

    def test_ping_fail(self, central_site: Site) -> None:
        """Test if we can't ping a non-existing site"""
        with rabbitmq_info_on_failure([central_site]):
            with pytest.raises(Timeout):
                check_broker_ping(central_site, "this-goes-nowhere")

    def test_pong(self, central_site: Site) -> None:
        """Test if we can pong"""
        with rabbitmq_info_on_failure([central_site]):
            with broker_pong(central_site) as pong:
                assert pong.returncode is None  # it's running

    def test_pong_received_message(self, central_site: Site, remote_site: Site) -> None:
        """Test if the `pong_received_message` works as intended"""
        with rabbitmq_info_on_failure([central_site, remote_site]):
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


@pytest.mark.skip_if_edition("cloud")
class TestMessageBroker:
    def test_message_broker_central_remote(self, central_site: Site, remote_site: Site) -> None:
        """Test if the connection between central and remote site works"""
        with rabbitmq_info_on_failure([central_site, remote_site]):
            assert_message_exchange_working(central_site, remote_site)

    def test_message_broker_remote_remote_via_central(
        self,
        central_site: Site,
        remote_site: Site,
        remote_site_2: Site,
    ) -> None:
        with rabbitmq_info_on_failure([central_site, remote_site, remote_site_2]):
            await_broker_ready(central_site, remote_site, remote_site_2)
            with broker_pong(remote_site):
                # test complement: should not work without the central site running:
                with broker_stopped(central_site):
                    with pytest.raises(Timeout):
                        check_broker_ping(remote_site_2, remote_site.id)

                check_broker_ping(remote_site_2, remote_site.id)

    def test_message_broker_remote_remote_p2p(
        self, central_site: Site, remote_site: Site, remote_site_2: Site
    ) -> None:
        with rabbitmq_info_on_failure([central_site, remote_site, remote_site_2]):
            with p2p_connection(central_site, remote_site, remote_site_2):
                await_broker_ready(central_site, remote_site, remote_site_2)
                with (
                    broker_pong(remote_site),
                    broker_stopped(central_site),
                ):
                    check_broker_ping(remote_site_2, remote_site.id)

    def test_rabbitmq_port_change(self, central_site: Site, remote_site: Site) -> None:
        """Ensure that sites can still communicate after the message broker port is changed"""
        with rabbitmq_info_on_failure([central_site, remote_site, remote_site]):
            site_connection = central_site.openapi.sites.show(remote_site.id)
            site_connection_port = int(
                site_connection["configuration_connection"]["message_broker_port"]
            )
            assert site_connection_port == remote_site.message_broker_port
            next_port = _next_free_port(remote_site, "RABBITMQ_PORT", str(site_connection_port + 1))

            remote_site.set_config("RABBITMQ_PORT", str(next_port), with_restart=True)
            await_broker_ready(central_site, remote_site)

            site_connection["configuration_connection"]["message_broker_port"] = str(next_port)
            central_site.openapi.sites.update(remote_site.id, site_connection)

            # ensure changes are not in effect before activated
            assert_message_exchange_not_working(central_site, remote_site)

            central_site.openapi.changes.activate_and_wait_for_completion()
            assert_message_exchange_working(central_site, remote_site)


@pytest.fixture(scope="session", name="broker_ca")
def site_ca_fixture(central_site: Site, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("ca") / "broker.pem"
    path.write_bytes(central_site.read_file("etc/rabbitmq/ssl/ca_cert.pem", encoding=None))
    return path


UNSUPPORTED_VERSIONS = (
    ssl.TLSVersion.SSLv3,
    ssl.TLSVersion.TLSv1,
    ssl.TLSVersion.TLSv1_1,
)
SUPPORTED_VERSIONS = (
    ssl.TLSVersion.TLSv1_2,
    ssl.TLSVersion.TLSv1_3,
)


@pytest.mark.parametrize("tls_version", UNSUPPORTED_VERSIONS, ids=lambda v: v.name)
def test_unsupported_tls_versions(
    central_site: Site, broker_ca: Path, tls_version: ssl.TLSVersion
) -> None:
    with pytest.raises(CMKTLSError):
        tls_connect(
            central_site.http_address,
            central_site.message_broker_port,
            broker_ca,
            tls_version,
        )


@pytest.mark.parametrize("tls_version", SUPPORTED_VERSIONS, ids=lambda v: v.name)
def test_supported_tls_versions(
    central_site: Site, broker_ca: Path, tls_version: ssl.TLSVersion
) -> None:
    tls_connect(
        central_site.http_address,
        central_site.message_broker_port,
        broker_ca,
        tls_version,
    )
