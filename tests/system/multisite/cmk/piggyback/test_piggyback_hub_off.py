#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator
from contextlib import contextmanager

from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    get_piggybacked_service_time,
    HOSTNAME_SOURCE_CENTRAL,
    HOSTNAME_SOURCE_REMOTE,
    piggybacked_data_gets_updated,
    schedule_check_and_discover,
    set_omd_config_piggyback_hub,
    setup_piggyback_host_and_check,
)
from tests.system.multisite.utils import await_broker_ready
from tests.testlib.system.site import Site


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

        with set_omd_config_piggyback_hub(remote_site, "off"):
            assert not _piggybacked_service_gets_updated(
                central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
            )

        # how is the piggyback hub restarted here?! Should we wait for the broker ready?
        assert _piggybacked_service_gets_updated(
            central_site, remote_site, HOSTNAME_SOURCE_CENTRAL, _HOSTNAME_PIGGYBACKED
        )
