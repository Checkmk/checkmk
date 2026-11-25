#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import signal
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager, ExitStack
from types import FrameType
from typing import Final, IO, Literal

from cmk.piggyback.backend._paths import payload_dir, source_status_dir
from cmk.piggyback.hub import RELATIVE_CONFIG_PATH
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import ServiceInfo
from tests.testlib.system.site import Site

CMK_TRACK_TIMEOUT: Final = 30  # secs
HOSTNAME_SOURCE_CENTRAL: Final = "source_central_host"
HOSTNAME_SOURCE_REMOTE: Final = "source_remote_host"
LOGGER = logging.getLogger(__name__)

# "INFO" logs the hub's config receive and save, which is what the config sync tests
# compare against. "DEBUG" adds every AMQP frame from pika, noisy enough to shift the
# timing those tests measure.
PIGGYBACK_HUB_LOG_LEVEL: Final = ""


@contextmanager
def setup_source_host(
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
def create_local_check(
    site: Site, hostnames_source: list[str], hostnames_piggybacked: list[str]
) -> Iterator[None]:
    """
    Creates a local check on the passed site and host, using the datasource_programs ruleset.
    """

    bash_command = f"cmk-piggyback create-sections 'Local service piggybacked from $HOSTNAME$' {' '.join(hostnames_piggybacked)}"
    rule_id = site.openapi.rules.create(
        ruleset_name="datasource_programs",
        value=bash_command,
        conditions={
            "host_name": {
                "match_on": hostnames_source,
                "operator": "one_of",
            }
        },
    )
    try:
        site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        site.openapi.rules.delete(rule_id)
        site.openapi.changes.activate_and_wait_for_completion()


@contextmanager
def setup_piggyback_host(
    central_site: Site, site_id_target: str, hostname_piggyback: str
) -> Iterator[None]:
    try:
        LOGGER.info("Creating piggyback host '%s' in site '%s'", hostname_piggyback, site_id_target)
        central_site.openapi.hosts.create(
            hostname=hostname_piggyback,
            attributes={
                "site": site_id_target,
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
            },
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield
    finally:
        LOGGER.info(
            "Deleting piggyback host '%s' from site '%s'", hostname_piggyback, site_id_target
        )
        central_site.openapi.hosts.delete(hostname_piggyback)
        central_site.openapi.changes.activate_and_wait_for_completion()


@contextmanager
def setup_piggyback_host_and_check(
    source_site: Site, site_id_target: str, hostname_source: str, hostname_piggyback: str
) -> Iterator[None]:
    with (
        create_local_check(
            source_site,
            [hostname_source],
            [hostname_piggyback],
        ),
        setup_piggyback_host(source_site, site_id_target, hostname_piggyback),
    ):
        yield


def schedule_check_and_discover(site: Site, hostname_source: str, hostname_piggyback: str) -> None:
    site.schedule_check(hostname_source, "Check_MK")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname_piggyback)


def piggybackhub_conf_mtime_ms(site: Site) -> int | None:
    path = site.root / RELATIVE_CONFIG_PATH
    return site.file_timestamp_ms(path) if site.file_exists(path) else None


def wait_for_conf_redistributed(site: Site, previous_mtime_ms: int, timeout: int) -> None:
    """
    Wait until piggyback_hub.conf has been rewritten on site.

    The hub rewrites the config whenever it receives a config message, so its
    modification time advances on every redistribution.

    Do not compare inodes here: the hub writes to a temporary file and renames it over
    the target, and the allocator hands the inode freed by one write straight back to
    the next one, so after an even number of rewrites the inode is back to the value it
    had before (CMK-35803).
    """

    LOGGER.info(
        "Waiting for piggyback_hub.conf on %s to pass mtime %d ms", site.id, previous_mtime_ms
    )

    def _conf_rewritten() -> bool:
        current_mtime_ms = piggybackhub_conf_mtime_ms(site)
        return current_mtime_ms is not None and current_mtime_ms > previous_mtime_ms

    wait_until(
        _conf_rewritten,
        timeout=timeout,
        interval=1,
        condition_name=f"piggyback_hub.conf redistributed for site {site.id}",
    )


def record_config_mtimes(sites: Sequence[Site]) -> dict[str, int]:
    """Snapshot piggyback_hub.conf mtimes before triggering a redistribution."""
    mtimes_ms = {}
    for site in sites:
        mtime_ms = piggybackhub_conf_mtime_ms(site)
        assert mtime_ms is not None, f"piggyback_hub.conf should exist for site {site.id}"
        mtimes_ms[site.id] = mtime_ms
    LOGGER.info("Recorded piggyback_hub.conf mtimes: %s", mtimes_ms)
    return mtimes_ms


def wait_for_config_redistributed(
    sites: Sequence[Site], previous_mtimes_ms: Mapping[str, int], timeout: int = 60
) -> None:
    for site in sites:
        wait_for_conf_redistributed(site, previous_mtimes_ms[site.id], timeout)


@contextmanager
def cleanup_piggyback_files(
    sites: Sequence[Site],
    *,
    piggybacked_hosts: Sequence[str] = (),
    source_hosts: Sequence[str] = (),
) -> Iterator[None]:
    try:
        yield
    finally:
        for site in sites:
            for hostname in piggybacked_hosts:
                site.delete_dir(payload_dir(site.root) / hostname)
            for hostname in source_hosts:
                site.delete_file(source_status_dir(site.root) / hostname)


@contextmanager
def cleanup_hosts(central_site: Site, *hostnames: str) -> Iterator[None]:
    try:
        yield
    finally:
        central_site.openapi.hosts.bulk_delete(list(hostnames), ignore_missing=True)
        central_site.openapi.changes.activate_and_wait_for_completion()


def _get_piggybacked_service(
    central_site: Site, source_hostname: str, piggybacked_hostname: str
) -> ServiceInfo:
    services = central_site.get_host_services(piggybacked_hostname)
    return services[f"Local service piggybacked from {source_hostname}"]


def get_piggybacked_service_time(
    source_site: Site, source_hostname: str, piggybacked_hostname: str
) -> int:
    service = _get_piggybacked_service(source_site, source_hostname, piggybacked_hostname)
    service_time_txt = service.summary.split("created at ")[1]
    return int(service_time_txt)


def discovered_service_phases(central_site: Site, hostname: str) -> Mapping[str, str]:
    """The phase ('monitored', 'vanished', 'undecided', ...) of each service on 'hostname'."""
    services = central_site.openapi.service_discovery.get_discovery_result(hostname)["extensions"]
    if not isinstance(services, dict) or not isinstance(
        (check_table := services["check_table"]), dict
    ):
        raise TypeError("Expected 'extensions' and its nested fields to be a dictionary")

    phases = {}
    for name, entry in check_table.items():
        if not isinstance(entry, dict) or not isinstance((extensions := entry["extensions"]), dict):
            raise TypeError("Expected every check table entry and its extensions to be a dict")
        phases[str(name)] = str(extensions["service_phase"])
    return phases


def piggybacked_service_name(source_hostname: str) -> str:
    """The service `create_local_check` produces for data coming from 'source_hostname'."""
    return f"local-Local service piggybacked from {source_hostname}"


def piggybacked_service_discovered(
    central_site: Site, source_hostname: str, piggybacked_hostname: str
) -> None:
    """Validate that a desired service has been discovered on host 'piggybacked_hostname'.

    Raises:
        AssertionError: when expected service is not discovered within the provided host.
        TypeError: when REST-API response to `service_discovery.get_discovery_result` changes.
    """
    discovered = set(discovered_service_phases(central_site, piggybacked_hostname))
    expected_service = piggybacked_service_name(source_hostname)
    assert expected_service in discovered, (
        f"Missing service '{expected_service}' on host '{piggybacked_hostname}'. "
        f"List of discovered services:\n{sorted(discovered)}"
    )


@contextmanager
def set_omd_config_piggyback_hub(site: Site, value: Literal["on", "off"]) -> Iterator[None]:
    with site.omd_config("PIGGYBACK_HUB", value):
        yield


@contextmanager
def piggyback_hub_log_level(*sites: Site) -> Iterator[None]:
    """
    Run the piggyback hub daemons at PIGGYBACK_HUB_LOG_LEVEL, when one is set.
    The init script starts the daemon without `--log-level`, so at its default (NOTSET)
    """
    if not PIGGYBACK_HUB_LOG_LEVEL:
        yield
        return

    with ExitStack() as stack:
        for site in sites:
            stack.enter_context(_restart_hub_with_log_level(site, PIGGYBACK_HUB_LOG_LEVEL))
        yield


@contextmanager
def _restart_hub_with_log_level(site: Site, level: str) -> Iterator[None]:
    site.omd("stop", "piggyback-hub")
    site.run(
        [
            f"{site.root}/bin/cmk-piggyback-hub",
            f"--log-level={level}",
            f"{site.root}/tmp/run/piggyback-hub.pid",
            f"{site.root}/var/log/piggyback-hub.log",
            str(site.root),
            site.id,
        ],
        check=True,
    )
    try:
        yield
    finally:
        site.omd("stop", "piggyback-hub")
        site.omd("start", "piggyback-hub")


class PBTimeoutError(TimeoutError):
    pass


@contextmanager
def _timeout(seconds: int, error_msg: str) -> Iterator[None]:
    """Context manager to raise an exception after a timeout.

    Uses `signal.SIGALRM` to monitor the time passed.

    Args:
        seconds (int): time in seconds to wait before raising `PBTimeoutError`
        error_msg (str): custom error message passed to `PBTimeoutError`

    Raises:
        PBTimeoutError: when `seconds` amount of time has passed.
    """

    def _raise_timeout(signum: int, frame: FrameType | None) -> None:  # noqa: ARG001
        raise PBTimeoutError(error_msg)

    alarm_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, alarm_handler)


def _wait_for_piggyback_track_ready(stdout: IO[str], timeout: int) -> None:
    """Wait for the cmk-broker-test to be ready

    Returns:
        None: on successful execution within `timeout` seconds.

    Raises:
        PBTimeoutError: raised after `timeout` seconds.
    """
    with _timeout(
        timeout,
        f"`cmk-piggyback track` did not start within {timeout} secs",
    ):
        while line := stdout.readline():
            if "Tracking incoming messages" in line:
                return


def piggybacked_data_gets_updated(
    source_site: Site,
    target_site: Site,
    hostname_source: str,
    hostname_piggybacked: str,
    timeout: int = CMK_TRACK_TIMEOUT,
    raise_timeout: bool = True,
) -> bool:
    """Track incoming piggybacked data on the target site.

    Use `timeout` to provide thresholds on how long it takes for
    + `cmk-piggyback track` to be ready.
    + desired data to be present in STDOUT of `cmk-piggyback track`.

    Returns:
        True: desired changes to piggyback data is reflected in incoming data.
        False: desired changes to piggyback data is not reflected in incoming data.

    Raises:
        PBTimeoutError: raised when `timeout` thresholds are crossed.
    """

    with target_site.execute(["cmk-piggyback", "track"], stdout=subprocess.PIPE) as track:
        try:
            if track.stdout is None:
                raise RuntimeError(
                    "The method expects STDOUT to be available, "
                    "consider initializing `execute(..., stdout=subprocess.PIPE)`!"
                )
            _wait_for_piggyback_track_ready(track.stdout, timeout)

            source_site.schedule_check(hostname_source, "Check_MK")
            with _timeout(timeout, f"`cmk-piggyback track` timed out after {timeout} secs"):
                while line := track.stdout.readline():
                    if f"{hostname_source} -> {hostname_piggybacked}" in line:
                        return True
                return False
        except PBTimeoutError:
            if raise_timeout:
                raise
            return False
        finally:
            # terminate `cmk-piggyback track` run manually,
            # as `cmk-piggyback track` does not terminate by itself.
            track.kill()
