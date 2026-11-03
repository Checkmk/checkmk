#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    HOSTNAME_SOURCE_CENTRAL,
    HOSTNAME_SOURCE_REMOTE,
    piggybacked_data_gets_updated,
    record_config_mtimes,
    schedule_check_and_discover,
    setup_piggyback_host_and_check,
    wait_for_config_redistributed,
)
from tests.testlib.system.site import Site

pytestmark = pytest.mark.skip_if_not_edition("ultimatemt")


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


def test_config_sync_source_remote_diff_customer(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """
    - Changing the customer of the remote site do not block piggyback hub config file distribution.
    - Restoring the customer to the original value keeps piggyback hub config file distribution.
    """
    central_site, remote_site = piggyback_env_two_site_setup
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
