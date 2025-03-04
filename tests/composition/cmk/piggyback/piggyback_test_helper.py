#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import signal
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import IO, Literal

from tests.testlib.common.utils import ServiceInfo
from tests.testlib.site import Site


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
) -> bool:
    services = central_site.openapi.service_discovery.get_discovery_result(piggybacked_hostname)[
        "extensions"
    ]
    if isinstance(services, dict) and isinstance((check_table := services["check_table"]), dict):
        return f"local-Local service piggybacked from {source_hostname}" in check_table
    raise TypeError("Expected 'extensions' and its nested fields to be a dictionary")


@contextmanager
def set_omd_config_piggyback_hub(site: Site, setting: Literal["on", "off"]) -> Iterator[None]:
    current_setting = site.run(["omd", "config", "show", "PIGGYBACK_HUB"]).stdout.strip()
    assert current_setting in ("on", "off")

    if current_setting == setting:
        yield
        return

    with _omd_stopped(site):
        assert site.run(["omd", "config", "set", "PIGGYBACK_HUB", setting]).returncode == 0

    try:
        yield
    finally:
        with _omd_stopped(site):
            assert (
                site.run(["omd", "config", "set", "PIGGYBACK_HUB", current_setting]).returncode == 0
            )


@contextmanager
def _omd_stopped(site: Site) -> Iterator[None]:
    # fail for partially running sites.
    assert (omd_status := site.omd("status")) in (0, 1)

    if omd_status == 1:  # stopped anyway
        yield
        return

    assert site.omd("stop") == 0
    try:
        yield
    finally:
        assert site.omd("start") == 0


class Timeout(RuntimeError):
    pass


@contextmanager
def _timeout(seconds: int, exc: Timeout) -> Iterator[None]:
    """Context manager to raise an exception after a timeout"""

    def _raise_timeout(signum, frame):
        raise exc

    alarm_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, alarm_handler)


def _wait_for_piggyback_track_ready(stdout: IO[str]) -> None:
    """Wait for the cmk-broker-test to be ready"""
    with _timeout(3, Timeout("`cmk-piggyback track` did not start in time")):
        while line := stdout.readline():
            if "Tracking incoming messages" in line:
                return


def piggybacked_data_gets_updated(
    source_site: Site, target_site: Site, hostname_source: str, hostname_piggybacked: str
) -> bool:
    """Track incoming piggybacked data on the target site"""

    try:
        track = target_site.execute(["cmk-piggyback", "track"], stdout=subprocess.PIPE, text=True)
        assert track.stdout
        _wait_for_piggyback_track_ready(track.stdout)

        source_site.schedule_check(hostname_source, "Check_MK")
        with _timeout(5, Timeout("`cmk-piggyback track` timed out after 5s")):
            while line := track.stdout.readline():
                if f"{hostname_source} -> {hostname_piggybacked}" in line:
                    return True
    except Timeout:
        pass

    return False
