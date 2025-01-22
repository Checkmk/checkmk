#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.composition.cmk.piggyback.piggyback_test_helper import (
    create_local_check,
    disable_piggyback_hub_globally,
    disable_piggyback_hub_remote_site,
    get_piggybacked_service_time,
    piggybacked_data_gets_updated,
    piggybacked_service_discovered,
)

from tests.testlib.site import Site

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
        central_site.openapi.hosts.create(
            hostname=hostname_source, attributes=host_attributes, bake_agent=False
        )
        yield
    finally:
        central_site.openapi.hosts.delete(hostname_source)


@contextmanager
def _setup_piggyback_host(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        source_site.openapi.hosts.create(
            hostname=hostname_piggyback,
            attributes={
                "site": site_id_target,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )
        source_site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        source_site.openapi.hosts.delete(hostname_piggyback)
        source_site.openapi.changes.activate_and_wait_for_completion()


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
            central_site.openapi.changes.activate_and_wait_for_completion()
            yield
    finally:
        central_site.openapi.changes.activate_and_wait_for_completion()


def _schedule_check_and_discover(site: Site, hostname_source: str, hostname_piggyback: str) -> None:
    site.schedule_check(hostname_source, "Check_MK")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname_piggyback)


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
        assert piggybacked_service_discovered(
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
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED_B
        )

        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED_B
        )


@contextmanager
def _create_and_rename_host(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        source_site.openapi.hosts.create(
            hostname="other_host",
            attributes={
                "site": site_id_target,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )

        source_site.openapi.changes.activate_and_wait_for_completion()

        source_site.openapi.hosts.rename_and_wait_for_completion(
            hostname_old="other_host", hostname_new=hostname_piggyback, etag="*"
        )
        source_site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        source_site.openapi.hosts.delete(hostname_piggyback)
        source_site.openapi.changes.activate_and_wait_for_completion()


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
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )


def _piggybacked_service_gets_updated(
    source_site: Site, target_site: Site, hostname_source: str, hostname_piggybacked: str
) -> bool:
    now = time.time()
    # sleep needed to not enforce decimal positions in the agent output
    time.sleep(1)
    source_site.schedule_check(hostname_source, "Check_MK")
    target_site.schedule_check(hostname_piggybacked, "Check_MK")
    service_time = get_piggybacked_service_time(source_site, hostname_source, hostname_piggybacked)
    return service_time - now > 0


def test_piggyback_hub_disabled_globally(
    central_site: Site,
    remote_site: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Scenario: Disabling global piggyback hub stops piggyback data distribution
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored on remote_site
    - piggyback hub is disabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is not monitored on remote_site
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored again on remote_site
    """

    with _setup_piggyback_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )

        with disable_piggyback_hub_globally(central_site, remote_site.id):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
            )

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )


def test_piggyback_hub_disabled_remote_site(
    central_site: Site,
    remote_site: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Scenario: Disabling piggyback hub for remote site stops piggyback data distribution for that site
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored on remote_site
    - piggyback hub is disabled for remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is not monitored on remote_site
    - piggyback hub is enabled for remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored again on remote_site
    """

    with _setup_piggyback_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )

        with disable_piggyback_hub_remote_site(central_site, remote_site.id):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
            )

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )


def _move_host(central_site: Site, to_remote_site: str, hostname_piggyback: str) -> None:
    central_site.openapi.hosts.update(
        hostname_piggyback,
        update_attributes={"site": to_remote_site},
    )
    central_site.openapi.changes.activate_and_wait_for_completion()


def test_piggyback_services_move_host(
    central_site: Site,
    remote_site: Site,
    remote_site_2: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Scenario: Moving host to another site makes the piggyback data to be monitored on the new site
    - _HOSTNAME_PIGGYBACKED_A is moved from remote_site to remote_site2
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is not monitored and not updated on remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored again on remote_site2
    """

    with _setup_piggyback_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _move_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED_A)
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        assert not piggybacked_data_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        assert piggybacked_data_gets_updated(
            central_site, remote_site_2, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )


def test_piggyback_host_removal(
    central_site: Site,
    remote_site: Site,
    prepare_piggyback_environment: None,
) -> None:
    """
    Scenario: Host removal stops distribution
        - piggyback data for _HOSTNAME_PIGGYBACKED_A is monitored on remote_site
        - remove _HOSTNAME_PIGGYBACKED_A from remote_site
        - piggyback data for _HOSTNAME_PIGGYBACKED_A is not monitored and not updated on remote_site
    """

    with _setup_piggyback_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED_A):
        _schedule_check_and_discover(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        assert piggybacked_data_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
        )

    assert not piggybacked_data_gets_updated(
        central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED_A
    )
