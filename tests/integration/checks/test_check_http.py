#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.https import HTTPSDummy
from tests.testlib.openapi_session import UnexpectedResponse
from tests.testlib.site import Site
from tests.testlib.utils import ServiceInfo

from cmk.utils.hostaddress import HostName

logger = logging.getLogger(__name__)


@pytest.fixture(name="check_http", scope="function")
def _check_http(site: Site) -> Iterator[tuple[str, dict[str, ServiceInfo]]]:
    hostname = HostName("http-0")
    site.openapi.create_host(hostname, attributes={"ipaddress": site.http_address, "site": site.id})
    site.activate_changes_and_wait_for_core_reload()
    try:
        rule_id = site.openapi.create_rule(
            ruleset_name="active_checks:http",
            value={
                "name": "check_http",
                "host": {"address": ("direct", "localhost")},
                "mode": ("url", {}),
            },
            folder="/",
        )
        site.activate_changes_and_wait_for_core_reload()
        yield rule_id, site.get_host_services(hostname)
    except UnexpectedResponse:
        logger.error("Failed to create check_http rule.")
        raise
    finally:
        site.openapi.delete_rule(rule_id)
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.skipif(
    os.environ.get("DISTRO") in {"centos-8", "almalinux-9", "sles-15sp5"},
    reason="Currently fails on this platform. Investigating...",
)
def test_check_http(site: Site, check_http: tuple[str, dict[str, ServiceInfo]]) -> None:
    rule_id, host_services = check_http
    service_name = "HTTP check_http"
    assert site.openapi.get_rule(rule_id)
    assert service_name in host_services.keys()
    assert host_services[service_name].state == 0
    logger.info(host_services[service_name].summary)


@pytest.fixture(name="check_https", scope="function")
def _check_https(site: Site, tmp_path: Path) -> Iterator[tuple[str, dict[str, ServiceInfo]]]:
    # start https dummy server
    httpss = HTTPSDummy(
        address=site.http_address,
        cert_dir=tmp_path.as_posix(),
    )
    port: int = httpss.run()

    hostname = HostName("https-0")
    site.openapi.create_host(hostname, attributes={"ipaddress": site.http_address, "site": site.id})
    site.activate_changes_and_wait_for_core_reload()
    try:
        rule_id = site.openapi.create_rule(
            ruleset_name="active_checks:http",
            value={
                "name": "check_https",
                "host": {"address": ("direct", site.http_address), "port": port},
                "mode": ("url", {"ssl": "auto"}),
            },
            folder="/",
        )
        site.activate_changes_and_wait_for_core_reload()
        yield rule_id, site.get_host_services(hostname)
    except UnexpectedResponse:
        logger.error("Failed to create check_https rule.")
        raise
    finally:
        site.openapi.delete_rule(rule_id)
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()
        httpss.stop()


def test_check_https(site: Site, check_https: tuple[str, dict[str, ServiceInfo]]) -> None:
    rule_id, host_services = check_https
    service_name = "HTTPS check_https"
    assert site.openapi.get_rule(rule_id)
    assert service_name in host_services.keys()
    assert host_services[service_name].state == 0
    logger.info(host_services[service_name].summary)
