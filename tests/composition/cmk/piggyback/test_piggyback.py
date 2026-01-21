#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from cmk.piggyback.backend._paths import source_status_dir
from tests.composition.cmk.piggyback.piggyback_test_helper import (
    create_local_check,
    get_piggybacked_service_time,
    piggybacked_data_gets_updated,
    piggybacked_service_discovered,
    set_omd_config_piggyback_hub,
)
from tests.testlib.site import Site

_HOSTNAME_SOURCE_CENTRAL = "source_central_host"
_HOSTNAME_SOURCE_REMOTE = "source_remote_host"
LOGGER = logging.getLogger(__name__)


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
        LOGGER.info("Creating host '%s' in site '%s'", hostname_source, site_id_source)
        central_site.openapi.hosts.create(
            hostname=hostname_source, attributes=host_attributes, bake_agent=False
        )
        yield
    finally:
        LOGGER.info("Deleting host '%s' from site '%s'", hostname_source, site_id_source)
        central_site.openapi.hosts.delete(hostname_source)


@contextmanager
def _setup_piggyback_host(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        LOGGER.info("Creating piggyback host '%s' in site '%s'", hostname_piggyback, site_id_target)
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
        LOGGER.info(
            "Deleting piggyback host '%s' from site '%s'", hostname_piggyback, site_id_target
        )
        source_site.openapi.hosts.delete(hostname_piggyback)
        source_site.openapi.changes.activate_and_wait_for_completion()


@contextmanager
def _setup_piggyback_host_and_check(
    source_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    with (
        create_local_check(
            source_site,
            [_HOSTNAME_SOURCE_CENTRAL],
            [hostname_piggyback],
        ),
        _setup_piggyback_host(source_site, site_id_target, hostname_piggyback),
    ):
        yield


@contextmanager
def _trace_broker_messages(site: Site) -> Iterator[None]:
    try:
        site.execute(["cmk-monitor-broker", "--enable_tracing"])
        yield
    finally:
        site.execute(["cmk-monitor-broker", "--disable_tracing"])


@pytest.fixture(name="piggyback_env_two_site_setup", scope="module")
def _piggyback_env_two_site_setup(
    central_site: Site,
    remote_site: Site,
) -> Iterator[tuple[Site, Site]]:
    try:
        with (
            _setup_source_host(central_site, central_site.id, _HOSTNAME_SOURCE_CENTRAL),
            _setup_source_host(central_site, remote_site.id, _HOSTNAME_SOURCE_REMOTE),
            set_omd_config_piggyback_hub(central_site, "on"),
            set_omd_config_piggyback_hub(remote_site, "on"),
            _trace_broker_messages(central_site),
            _trace_broker_messages(remote_site),
        ):
            central_site.openapi.changes.activate_and_wait_for_completion()
            yield central_site, remote_site
    finally:
        central_site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="piggyback_env_three_site_setup", scope="module")
def _piggyback_env_three_site_setup(
    piggyback_env_two_site_setup: tuple[Site, Site], remote_site_2: Site
) -> Iterator[tuple[Site, Site, Site]]:
    central_site, remote_site = piggyback_env_two_site_setup
    try:
        with (
            set_omd_config_piggyback_hub(remote_site_2, "on"),
            _trace_broker_messages(remote_site_2),
        ):
            central_site.openapi.changes.activate_and_wait_for_completion()
            yield central_site, remote_site, remote_site_2
    finally:
        central_site.openapi.changes.activate_and_wait_for_completion()


def _schedule_check_and_discover(site: Site, hostname_source: str, hostname_piggyback: str) -> None:
    site.schedule_check(hostname_source, "Check_MK")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname_piggyback)


def test_piggyback_services_source_remote(piggyback_env_two_site_setup: tuple[Site, Site]) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site central_site, is monitored on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_source_remote"
    with _setup_piggyback_host_and_check(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


def test_piggyback_services_remote_remote(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site remote_site, is monitored on remote_site2
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_remote_remote"
    with (
        create_local_check(
            central_site,
            [_HOSTNAME_SOURCE_REMOTE],
            [_HOSTNAME_PIGGYBACKED],
        ),
        _setup_piggyback_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED),
    ):
        remote_site.schedule_check(_HOSTNAME_SOURCE_REMOTE, "Check_MK")
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )

        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
        )


@contextmanager
def _turn_off_piggyback_hub(site: Site) -> Iterator[None]:
    try:
        with site.omd_config("PIGGYBACK_HUB", "off"):
            yield
    finally:
        site.omd_config("PIGGYBACK_HUB", "on")


def test_piggyback_services_remote_remote_central_ph_off(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site remote_site, is monitored on remote_site2
    with the central site's piggyback hub disabled
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_remote_remote"
    with (
        _turn_off_piggyback_hub(central_site),
        create_local_check(
            central_site,
            [_HOSTNAME_SOURCE_REMOTE],
            [_HOSTNAME_PIGGYBACKED],
        ),
        _setup_piggyback_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED),
    ):
        remote_site.schedule_check(_HOSTNAME_SOURCE_REMOTE, "Check_MK")
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )

        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
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


def test_piggyback_rename_host(piggyback_env_two_site_setup: tuple[Site, Site]) -> None:
    """
    Scenario: Host renaming triggers piggyback config re-distribution
    - host "other_host" is created on remote_site
    - host "other_host" is renamed to _HOSTNAME_PIGGYBACKED
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_rename"
    with (
        create_local_check(
            central_site,
            [_HOSTNAME_SOURCE_CENTRAL],
            [_HOSTNAME_PIGGYBACKED],
        ),
        _create_and_rename_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED),
    ):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


def _piggybacked_service_gets_updated(
    source_site: Site, target_site: Site, hostname_source: str, hostname_piggybacked: str
) -> bool:
    now = time.time()

    # sleep needed to make sure the integer timestamp is increased.
    time.sleep(1)

    # fetch new piggybacked data from the source
    source_site.schedule_check(hostname_source, "Check_MK")

    # It may take some time for the piggyback hub to forward the data.
    # We are defensive here to avoid flakes in the test, and retry a few times.
    # It should be quite fast, though
    for _retry in range(5):
        # check that the piggybacked source host has a new dataset
        target_site.schedule_check(hostname_piggybacked, "Check_MK", wait_timeout=60)
        service_time = get_piggybacked_service_time(
            source_site, hostname_source, hostname_piggybacked
        )
        if service_time - now > 0:
            return True
        time.sleep(1)
    return False


def test_piggyback_hub_disabled_globally(piggyback_env_two_site_setup: tuple[Site, Site]) -> None:
    """
    Scenario: Disabling global piggyback hub stops piggyback data distribution
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored on remote_site
    - piggyback hub is disabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED is not monitored on remote_site
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored again on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_hub_disabled"
    with _setup_piggyback_host_and_check(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

        with (
            set_omd_config_piggyback_hub(central_site, "off"),
            set_omd_config_piggyback_hub(remote_site, "off"),
        ):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


def test_piggyback_hub_disabled_remote_site(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    Scenario: Disabling piggyback hub for remote site stops piggyback data distribution for that site
    - piggyback hub is enabled globally
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored on remote_site
    - piggyback hub is disabled for remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED is not monitored on remote_site
    - piggyback hub is enabled for remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored again on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_hub_disabled_remote_site"
    with _setup_piggyback_host_and_check(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

        with (
            set_omd_config_piggyback_hub(central_site, "off"),
            set_omd_config_piggyback_hub(remote_site, "off"),
        ):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


def _move_host(central_site: Site, to_remote_site: str, hostname_piggyback: str) -> None:
    central_site.openapi.hosts.update(
        hostname_piggyback,
        update_attributes={"site": to_remote_site},
    )
    central_site.openapi.changes.activate_and_wait_for_completion()


def test_piggyback_services_move_host(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Scenario: Moving host to another site makes the piggyback data to be monitored on the new site
    - _HOSTNAME_PIGGYBACKED is moved from remote_site to remote_site2
    - piggyback data for _HOSTNAME_PIGGYBACKED is not monitored and not updated on remote_site
    - piggyback data for _HOSTNAME_PIGGYBACKED is monitored again on remote_site2
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_move_host"
    with _setup_piggyback_host_and_check(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
        _move_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED)
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert not piggybacked_data_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
        assert piggybacked_data_gets_updated(
            central_site, remote_site_2, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


def test_piggyback_host_removal(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    Scenario: Host removal stops distribution
        - piggyback data for _HOSTNAME_PIGGYBACKED is monitored on remote_site
        - remove _HOSTNAME_PIGGYBACKED from remote_site
        - piggyback data for _HOSTNAME_PIGGYBACKED is not monitored and not updated on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_removal"
    with _setup_piggyback_host_and_check(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
        assert piggybacked_service_discovered(
            central_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

    assert not piggybacked_data_gets_updated(
        central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    )


def test_piggyback_status_file_deletion_transport(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    Scenario: Deletion of status file on a piggybacked host is transported to target host so that
              the dcd can remove the host
        Given piggybacked data on central_site for a host monitored on remote_site
        When source status file on central_site is removed
        Then source status file is removed on remote_site as well
    """
    central_site, remote_site = piggyback_env_two_site_setup
    # given
    piggybacked_host_name = "remote_host_removal"

    with (
        create_local_check(
            central_site,
            [_HOSTNAME_SOURCE_CENTRAL],
            [piggybacked_host_name],
        ),
        _setup_piggyback_host(central_site, remote_site.id, piggybacked_host_name),
    ):
        _schedule_check_and_discover(central_site, _HOSTNAME_SOURCE_CENTRAL, piggybacked_host_name)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, _HOSTNAME_SOURCE_CENTRAL, piggybacked_host_name
        )
        assert remote_site.file_exists(
            source_status_dir(remote_site.root) / _HOSTNAME_SOURCE_CENTRAL
        )

        # when
        central_site.delete_file(source_status_dir(central_site.root) / _HOSTNAME_SOURCE_CENTRAL)
        assert (
            central_site.file_exists(
                source_status_dir(central_site.root) / _HOSTNAME_SOURCE_CENTRAL
            )
            is False
        )

        # then
        assert (
            remote_site.file_exists(source_status_dir(remote_site.root) / _HOSTNAME_SOURCE_CENTRAL)
            is False
        )
