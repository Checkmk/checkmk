#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.piggyback.backend._paths import source_status_dir
from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    CMK_TRACK_TIMEOUT,
    HOSTNAME_SOURCE_CENTRAL,
    HOSTNAME_SOURCE_REMOTE,
    piggybacked_data_gets_updated,
    piggybacked_service_discovered,
    schedule_check_and_discover,
    setup_piggyback_host_and_check,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site


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
