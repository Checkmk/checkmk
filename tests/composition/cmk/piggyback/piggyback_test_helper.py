#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Final, IO, Literal

from tests.testlib.common.utils2 import ServiceInfo
from tests.testlib.site import Site

CMK_TRACK_TIMEOUT: Final = 30  # secs


@dataclass
class ServiceDiscoveredInfo:
    host_name: str
    check_plugin_name: str
    service_name: str
    service_item: str


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


def piggybacked_service_discovered(
    central_site: Site, source_hostname: str, piggybacked_hostname: str
) -> None:
    """Validate that a desired service has been discovered on host 'piggybacked_hostname'.

    Raises:
        AssertionError: when expected service is not discovered within the provided host.
        TypeError: when REST-API response to `service_discovery.get_discovery_result` changes.
    """
    services = central_site.openapi.service_discovery.get_discovery_result(piggybacked_hostname)[
        "extensions"
    ]
    if isinstance(services, dict) and isinstance((check_table := services["check_table"]), dict):
        expected_service = f"local-Local service piggybacked from {source_hostname}"
        assert expected_service in check_table, (
            f"Missing service '{expected_service}' on host '{piggybacked_hostname}'. "
            f"List of discovered services:\n{sorted(check_table)}"
        )
        return
    raise TypeError("Expected 'extensions' and its nested fields to be a dictionary")


@contextmanager
def set_omd_config_piggyback_hub(site: Site, value: Literal["on", "off"]) -> Iterator[None]:
    with site.omd_config("PIGGYBACK_HUB", value):
        yield


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

    def _raise_timeout(signum, frame):
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
            else:
                return False
        finally:
            # terminate `cmk-piggyback track` run manually,
            # as `cmk-piggyback track` does not terminate by itself.
            track.kill()
