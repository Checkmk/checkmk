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
from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    cleanup_hosts,
    cleanup_piggyback_files,
    CMK_TRACK_TIMEOUT,
    create_local_check,
    discovered_service_phases,
    get_piggybacked_service_time,
    HOSTNAME_SOURCE_CENTRAL,
    HOSTNAME_SOURCE_REMOTE,
    piggybacked_data_gets_updated,
    piggybacked_service_discovered,
    piggybacked_service_name,
    record_config_mtimes,
    schedule_check_and_discover,
    set_omd_config_piggyback_hub,
    setup_piggyback_host_and_check,
    wait_for_config_redistributed,
)
from tests.system.multisite.utils import await_broker_ready
from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site

LOGGER = logging.getLogger(__name__)


@pytest.mark.medium_test_chain
def test_piggyback_services_source_remote(piggyback_env_two_site_setup: tuple[Site, Site]) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site central_site, is monitored on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_source_remote"
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        piggybacked_service_discovered(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)


@pytest.mark.skip_if_not_edition("ultimatemt")
def test_piggyback_services_source_remote_diff_customer(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    - Service for host _HOSTNAME_PIGGYBACKED, generated on site central_site, is monitored on remote_site
    - change customer of remote_site to a different one: service is no more monitored on remote_site
    """
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_source_remote"
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

        with _change_remote_site_customer(central_site, remote_site, "customer1"):
            schedule_check_and_discover(
                central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )
            assert not piggybacked_data_gets_updated(
                central_site,
                remote_site,
                HOSTNAME_SOURCE_CENTRAL,
                _HOSTNAME_PIGGYBACKED,
                raise_timeout=False,
            )

        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )


@pytest.mark.skip_if_not_edition("ultimatemt")
def test_piggyback_services_remote_remote_diff_customer(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    - change customer of remote_site to a different one: service is no more monitored on remote_site2
    - Service for host _HOSTNAME_PIGGYBACKED, generated on site remote_site, is monitored on remote_site2
      when both remote sites are on the same customer
    """

    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_remote_remote"

    def _schedule_and_discover() -> None:
        remote_site.schedule_check(HOSTNAME_SOURCE_REMOTE, "Check_MK")
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )

    with setup_piggyback_host_and_check(
        central_site, remote_site_2.id, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
    ):
        # both remote sites on "provider" customer, data flows from remote_site to remote_site_2
        assert piggybacked_data_gets_updated(
            remote_site, remote_site_2, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
        )

        with _change_remote_site_customer(central_site, remote_site, "customer1"):
            _schedule_and_discover()
            # remote_site is on different customer, data does not flow to remote_site_2
            assert not piggybacked_data_gets_updated(
                remote_site,
                remote_site_2,
                HOSTNAME_SOURCE_REMOTE,
                _HOSTNAME_PIGGYBACKED,
                raise_timeout=False,
            )

            with _change_remote_site_customer(central_site, remote_site_2, "customer1"):
                _schedule_and_discover()
                # both remote sites on same customer, data flows from remote_site to remote_site_2
                assert piggybacked_data_gets_updated(
                    remote_site, remote_site_2, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
                )


@contextmanager
def _change_remote_site_customer(
    central_site: Site, remote_site: Site, new_customer: str
) -> Iterator[None]:
    try:
        site_connection = central_site.openapi.sites.show(remote_site.id)
        site_connection["basic_settings"]["customer"] = new_customer
        central_site.openapi.sites.update(remote_site.id, site_connection)
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        site_connection = central_site.openapi.sites.show(remote_site.id)
        site_connection["basic_settings"]["customer"] = "provider"
        central_site.openapi.sites.update(remote_site.id, site_connection)
        central_site.openapi.changes.activate_and_wait_for_completion()


@pytest.mark.skip_if_not_edition("ultimatemt")
def test_config_sync_source_remote_diff_customer(central_site: Site, remote_site: Site) -> None:
    """
    - Changing the customer of the remote site do not block piggyback hub config file distribution.
    - Restoring the customer to the original value keeps piggyback hub config file distribution.
    """

    _HOSTNAME_PIGGYBACKED = "piggybacked_host"
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        # same "provider" customer
        # record the initial config file state
        config_mtimes_ms = record_config_mtimes([central_site, remote_site])

        with _change_remote_site_customer(central_site, remote_site, "customer1"):
            # service are NOT updated anymore (tested elsewhere), but config file is
            wait_for_config_redistributed([central_site, remote_site], config_mtimes_ms)
            config_mtimes_ms = record_config_mtimes([central_site, remote_site])

        # After restoring customer, data distribution resumes, so config file is updated again
        wait_for_config_redistributed([central_site, remote_site], config_mtimes_ms)


@pytest.mark.skip_if_not_edition("ultimatemt")
def test_config_sync_source_remote_remote_diff_customer(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Test with 2 remote sites, source on remote_site, target on remote_site_2:
    - Changing customer on both remote sites blocks direct data distribution
    - remote_site_2 still receives data from remote_site (both on same customer)
    - All sites receive config file updates throughout
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_two_remotes_both_customer"
    with setup_piggyback_host_and_check(
        central_site, remote_site_2.id, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
    ):
        remote_site.schedule_check(HOSTNAME_SOURCE_REMOTE, "Check_MK")
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )

        # Initially both sites on "provider" customer - data flows from remote_site to remote_site_2
        # record the initial config file state
        config_mtimes_ms = record_config_mtimes(piggyback_env_three_site_setup)

        # Change customer on one remote sites; data must stop flowing, config updates must continue
        with _change_remote_site_customer(central_site, remote_site, "customer1"):
            # all sites get config updates
            wait_for_config_redistributed(piggyback_env_three_site_setup, config_mtimes_ms)
            config_mtimes_ms = record_config_mtimes(piggyback_env_three_site_setup)

            # now change customer on the other remote site as well
            with _change_remote_site_customer(central_site, remote_site_2, "customer1"):
                # all sites get config updates
                wait_for_config_redistributed(piggyback_env_three_site_setup, config_mtimes_ms)
                config_mtimes_ms = record_config_mtimes(piggyback_env_three_site_setup)

        # all sites get config updates
        wait_for_config_redistributed(piggyback_env_three_site_setup, config_mtimes_ms)


def test_renaming_a_piggybacked_host_redistributes_config(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    Scenario: Host renaming triggers piggyback config re-distribution
    """

    _HOSTNAME_PIGGYBACKED = "piggybacked_host_rename"
    central_site, remote_site = piggyback_env_two_site_setup
    with (
        create_local_check(
            central_site,
            [HOSTNAME_SOURCE_CENTRAL],
            [_HOSTNAME_PIGGYBACKED],
        ),
    ):
        # record the initial config file state
        config_mtimes_ms = record_config_mtimes([central_site, remote_site])

        with _create_and_rename_host(central_site, remote_site.id, _HOSTNAME_PIGGYBACKED):
            # config distribution is triggered on both sites after renaming
            wait_for_config_redistributed([central_site, remote_site], config_mtimes_ms)
            config_mtimes_ms = record_config_mtimes([central_site, remote_site])

        # config distribution is triggered on both sites after deleting the host
        wait_for_config_redistributed([central_site, remote_site], config_mtimes_ms)


@pytest.mark.medium_test_chain
def test_piggyback_services_remote_remote(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site remote_site, is monitored on remote_site2
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_remote_remote"
    with setup_piggyback_host_and_check(
        central_site, remote_site_2.id, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
    ):
        # Wait for the data from remote_1 to actually arrive to remote_2 before running
        # discovery.
        # This also isolates a propagation failure (this assert) from a
        # discovery failure (the assert below).
        assert piggybacked_data_gets_updated(
            remote_site, remote_site_2, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
        ), "Piggybacked data did not get updated on remote_site_2"

        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )
        piggybacked_service_discovered(central_site, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED)


@contextmanager
def _turn_off_piggyback_hub(site: Site) -> Iterator[None]:
    try:
        with site.omd_config("PIGGYBACK_HUB", "off"):
            yield
    finally:
        with site.omd_config("PIGGYBACK_HUB", "on"):
            ...
        # not really needed for the use we are doing at the moment of this method,
        # but for the tests executed after this one
        await_broker_ready(site)


def test_piggyback_services_remote_remote_central_ph_off(
    piggyback_env_three_site_setup: tuple[Site, Site, Site],
) -> None:
    """
    Service for host _HOSTNAME_PIGGYBACKED, generated on site remote_site, is not monitored on remote_site2
    with the central site's piggyback hub disabled
    """
    central_site, remote_site, remote_site_2 = piggyback_env_three_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_remote_remote"
    with setup_piggyback_host_and_check(
        central_site, remote_site_2.id, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
    ):
        assert piggybacked_data_gets_updated(
            remote_site, remote_site_2, HOSTNAME_SOURCE_REMOTE, _HOSTNAME_PIGGYBACKED
        )

        with _turn_off_piggyback_hub(central_site):
            time.sleep(5)
            assert not piggybacked_data_gets_updated(
                remote_site,
                remote_site_2,
                HOSTNAME_SOURCE_REMOTE,
                _HOSTNAME_PIGGYBACKED,
                raise_timeout=False,
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


def _rename_host(central_site: Site, hostname_old: str, hostname_new: str) -> str:
    summary = central_site.openapi.hosts.rename_and_wait_for_completion(
        hostname_old=hostname_old, hostname_new=hostname_new, etag="*"
    )
    central_site.openapi.changes.activate_and_wait_for_completion()
    return summary


def test_renaming_a_piggybacked_host_keeps_its_piggybacked_service(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """A renamed piggybacked host is still fed by its source"""
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_to_rename"
    _HOSTNAME_RENAMED = "piggybacked_host_renamed"
    with (
        cleanup_piggyback_files(
            (central_site, remote_site),
            piggybacked_hosts=(_HOSTNAME_PIGGYBACKED, _HOSTNAME_RENAMED),
        ),
        cleanup_hosts(central_site, _HOSTNAME_PIGGYBACKED, _HOSTNAME_RENAMED),
        create_local_check(central_site, [HOSTNAME_SOURCE_CENTRAL], [_HOSTNAME_PIGGYBACKED]),
    ):
        central_site.openapi.hosts.create(
            hostname=_HOSTNAME_PIGGYBACKED,
            attributes={
                "site": remote_site.id,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        summary = _rename_host(central_site, _HOSTNAME_PIGGYBACKED, _HOSTNAME_RENAMED)
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_RENAMED
        )
        piggybacked_service_discovered(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_RENAMED)
        assert "Piggyback information from other host" in summary


def test_renaming_a_source_host_keeps_delivering_the_piggybacked_service(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """A renamed source host does not orphan the data it delivered to a host on its own site"""
    # Copies the hub distributed to other sites are not moved, they expire by their maximum age.
    central_site, _remote_site = piggyback_env_two_site_setup
    _HOSTNAME_SOURCE = "source_central_host_to_rename"
    _HOSTNAME_RENAMED = "source_central_host_renamed"
    _HOSTNAME_PIGGYBACKED = "piggybacked_host_source_renamed"
    with (
        cleanup_piggyback_files(
            (central_site,),
            piggybacked_hosts=(_HOSTNAME_PIGGYBACKED,),
            source_hosts=(_HOSTNAME_SOURCE, _HOSTNAME_RENAMED),
        ),
        cleanup_hosts(central_site, _HOSTNAME_SOURCE, _HOSTNAME_RENAMED),
        setup_piggyback_host_and_check(
            central_site, central_site.id, _HOSTNAME_SOURCE, _HOSTNAME_PIGGYBACKED
        ),
    ):
        central_site.openapi.hosts.create(
            hostname=_HOSTNAME_SOURCE,
            attributes={
                "site": central_site.id,
                "ipaddress": "127.0.0.1",
                "tag_agent": "cmk-agent",
            },
            bake_agent=False,
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        schedule_check_and_discover(central_site, _HOSTNAME_SOURCE, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        summary = _rename_host(central_site, _HOSTNAME_SOURCE, _HOSTNAME_RENAMED)
        central_site.schedule_check(_HOSTNAME_RENAMED, "Check_MK")
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED, mode="refresh"
        )

        phases = discovered_service_phases(central_site, _HOSTNAME_PIGGYBACKED)
        # The service name carries the source name, so the service from the old name stops
        # being fed and the one from the new name appears.
        assert phases[piggybacked_service_name(_HOSTNAME_RENAMED)] == "undecided"
        assert phases[piggybacked_service_name(_HOSTNAME_SOURCE)] == "vanished"
        assert "Piggyback information for other hosts" in summary


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
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

        with (
            set_omd_config_piggyback_hub(central_site, "off"),
            set_omd_config_piggyback_hub(remote_site, "off"),
        ):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )

        # how is the piggyback hub restarted here?! Should we wait for the broker ready?
        assert _piggybacked_service_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
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
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        central_site.openapi.changes.activate_and_wait_for_completion()

        assert _piggybacked_service_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )

        with (
            set_omd_config_piggyback_hub(central_site, "off"),
            set_omd_config_piggyback_hub(remote_site, "off"),
        ):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )

        # how is the piggyback hub restarted here?! Should we wait for the broker ready?
        assert _piggybacked_service_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
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
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        _move_host(central_site, remote_site_2.id, _HOSTNAME_PIGGYBACKED)
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert not piggybacked_data_gets_updated(
            central_site,
            remote_site,
            HOSTNAME_SOURCE_CENTRAL,
            _HOSTNAME_PIGGYBACKED,
            raise_timeout=False,
        )
        assert piggybacked_data_gets_updated(
            central_site, remote_site_2, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
        piggybacked_service_discovered(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)


@pytest.mark.medium_test_chain
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
    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
        piggybacked_service_discovered(central_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED)

    assert not piggybacked_data_gets_updated(
        central_site,
        remote_site,
        HOSTNAME_SOURCE_CENTRAL,
        _HOSTNAME_PIGGYBACKED,
        raise_timeout=False,
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

    with setup_piggyback_host_and_check(
        central_site, remote_site.id, HOSTNAME_SOURCE_CENTRAL, piggybacked_host_name
    ):
        schedule_check_and_discover(central_site, HOSTNAME_SOURCE_CENTRAL, piggybacked_host_name)
        assert piggybacked_data_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, piggybacked_host_name
        )
        assert remote_site.file_exists(
            source_status_dir(remote_site.root) / HOSTNAME_SOURCE_CENTRAL
        )

        # when
        central_site.delete_file(source_status_dir(central_site.root) / HOSTNAME_SOURCE_CENTRAL)
        assert (
            central_site.file_exists(source_status_dir(central_site.root) / HOSTNAME_SOURCE_CENTRAL)
            is False
        )

        # then
        wait_until(
            lambda: (
                not remote_site.file_exists(
                    source_status_dir(remote_site.root) / HOSTNAME_SOURCE_CENTRAL
                )
            ),
            timeout=CMK_TRACK_TIMEOUT,
            interval=1,
            condition_name=f"source status file removed on site {remote_site.id}",
        )
