#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.testlib.site import Site

from tests.composition.cmk.piggyback.piggyback_test_helper import (
    create_local_check,
    piggybacked_service_discovered,
)

_HOSTNAME_SOURCE_CENTRAL = "source_central_host"
_HOSTNAME_SOURCE_REMOTE = "source_remote_host"
_HOSTNAME_PIGGYBACKED_A = "piggybacked_host_a"
_HOSTNAME_PIGGYBACKED_B = "piggybacked_host_b"


@contextmanager
def _setup_source_host(
    central_site: Site, site_id_source: str, hostname_source: str
) -> Iterator[None]:
    host_attributes = {
        "site": site_id_source,
        "ipaddress": "127.0.0.1",
        "tag_agent": "cmk-agent",
    }
    try:
        central_site.openapi.create_host(
            hostname=hostname_source, attributes=host_attributes, bake_agent=False
        )
        yield
    finally:
        central_site.openapi.delete_host(hostname_source)


@contextmanager
def _setup_piggyback_host(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        source_site.openapi.create_host(
            hostname=hostname_piggyback,
            attributes={
                "site": site_id_target,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )
        source_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)
        yield
    finally:
        source_site.openapi.delete_host(hostname_piggyback)
        source_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


@pytest.fixture(name="prepare_piggyback_environment", scope="module")
def _prepare_piggyback_environment(central_site: Site, remote_site: Site) -> Iterator[None]:
    try:
        with (
            _setup_source_host(central_site, central_site.id, _HOSTNAME_SOURCE_CENTRAL),
            _setup_source_host(central_site, remote_site.id, _HOSTNAME_SOURCE_REMOTE),
            create_local_check(
                central_site,
                [_HOSTNAME_SOURCE_CENTRAL],
                [_HOSTNAME_PIGGYBACKED_A],
            ),
            create_local_check(
                central_site,
                [_HOSTNAME_SOURCE_REMOTE],
                [_HOSTNAME_PIGGYBACKED_B],
            ),
        ):
            central_site.openapi.activate_changes_and_wait_for_completion(
                force_foreign_changes=True
            )
            yield
    finally:
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


def _schedule_check_and_discover(site: Site, hostname_source: str, hostname_piggyback: str) -> None:
    site.schedule_check(hostname_source, "Check_MK")
    site.openapi.discover_services_and_wait_for_completion(hostname_piggyback)


def test_piggyback_services_source_remote(
    central_site: Site,
    remote_site: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED_A, generated on site central_site, is monitored on remote_site
    """
    with _setup_piggyback_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        _ = piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )


def test_piggyback_services_remote_remote(
    central_site: Site,
    remote_site: Site,
    remote_site_2: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED_B, generated on site remote_site, is monitored on remote_site2
    """
    with _setup_piggyback_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED_B):
        remote_site.schedule_check(_HOSTNAME_SOURCE_REMOTE, "Check_MK")
        central_site.openapi.discover_services_and_wait_for_completion(_HOSTNAME_PIGGYBACKED_B)

        _ = piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED_B
        )


@contextmanager
def _create_and_rename_host(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        source_site.openapi.create_host(
            hostname="other_host",
            attributes={
                "site": site_id_target,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )

        source_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)

        source_site.openapi.rename_host_and_wait_for_completion(
            hostname_old="other_host", hostname_new=hostname_piggyback, etag="*"
        )
        source_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)
        yield
    finally:
        source_site.openapi.delete_host(hostname_piggyback)
        source_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


def test_piggyback_rename_host(
    central_site: Site,
    remote_site: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Scenario: Host renaming triggers piggyback config re-distribution
    - host "other_host" is created on remote_site
    - host "other_host" is renamed to _HOSTNAME_PIGGYBACKED_A
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored on remote_site
    """

    with _create_and_rename_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        _ = piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
