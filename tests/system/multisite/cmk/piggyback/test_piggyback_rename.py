#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from cmk.piggyback.backend._paths import payload_dir, source_status_dir
from tests.system.multisite.cmk.piggyback.piggyback_test_helper import (
    cleanup_hosts,
    cleanup_piggyback_files,
    create_local_check,
    discovered_service_phases,
    HOSTNAME_SOURCE_CENTRAL,
    piggybacked_service_discovered,
    piggybacked_service_name,
    record_config_mtimes,
    schedule_check_and_discover,
    setup_piggyback_host_and_check,
    wait_for_config_redistributed,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site


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


def test_renaming_a_source_host_moves_its_data_on_other_sites(
    piggyback_env_two_site_setup: tuple[Site, Site],
) -> None:
    """The site of a piggybacked host takes over the data of a renamed source from another site"""
    central_site, remote_site = piggyback_env_two_site_setup
    _HOSTNAME_SOURCE = "source_central_host_to_rename_remote"
    _HOSTNAME_RENAMED = "source_central_host_renamed_remote"
    _HOSTNAME_PIGGYBACKED = "piggybacked_remote_host_source_renamed"
    with (
        cleanup_piggyback_files(
            (central_site, remote_site),
            piggybacked_hosts=(_HOSTNAME_PIGGYBACKED,),
            source_hosts=(_HOSTNAME_SOURCE, _HOSTNAME_RENAMED),
        ),
        cleanup_hosts(central_site, _HOSTNAME_SOURCE, _HOSTNAME_RENAMED),
        setup_piggyback_host_and_check(
            central_site, remote_site.id, _HOSTNAME_SOURCE, _HOSTNAME_PIGGYBACKED
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
        central_site.schedule_check(_HOSTNAME_SOURCE, "Check_MK")
        _wait_for_files(
            remote_site,
            present=_source_files(remote_site, _HOSTNAME_SOURCE, _HOSTNAME_PIGGYBACKED),
            absent=(),
        )
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED
        )
        central_site.openapi.changes.activate_and_wait_for_completion()

        _rename_host(central_site, _HOSTNAME_SOURCE, _HOSTNAME_RENAMED)

        # No further check of the renamed source: the hub has to forward what the rename moved.
        # The status file of the old name stays until the cleanup, see remove_piggyback_raw_data.
        _wait_for_files(
            remote_site,
            present=_source_files(remote_site, _HOSTNAME_RENAMED, _HOSTNAME_PIGGYBACKED),
            absent=(payload_dir(remote_site.root) / _HOSTNAME_PIGGYBACKED / _HOSTNAME_SOURCE,),
        )
        # The moved data still names the old source in its service, only a check renews it.
        central_site.schedule_check(_HOSTNAME_RENAMED, "Check_MK")
        wait_until(
            lambda: (
                _HOSTNAME_RENAMED
                in remote_site.read_file(
                    payload_dir(remote_site.root) / _HOSTNAME_PIGGYBACKED / _HOSTNAME_RENAMED
                )
            ),
            timeout=60,
            interval=1,
            condition_name="renewed piggyback data on the remote site",
        )
        central_site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            _HOSTNAME_PIGGYBACKED, mode="refresh"
        )
        phases = discovered_service_phases(central_site, _HOSTNAME_PIGGYBACKED)
        # Same as on a single site, see test_renaming_a_source_host_keeps_delivering_the_piggybacked_service
        assert phases[piggybacked_service_name(_HOSTNAME_RENAMED)] == "undecided"
        assert phases[piggybacked_service_name(_HOSTNAME_SOURCE)] == "vanished"


def _source_files(site: Site, source: str, piggybacked: str) -> Sequence[Path]:
    return (
        source_status_dir(site.root) / source,
        payload_dir(site.root) / piggybacked / source,
    )


def _wait_for_files(site: Site, *, present: Sequence[Path], absent: Sequence[Path]) -> None:
    wait_until(
        lambda: (
            all(site.file_exists(p) for p in present)
            and not any(site.file_exists(p) for p in absent)
        ),
        timeout=60,
        interval=1,
        condition_name=f"piggyback files on site {site.id}",
    )
