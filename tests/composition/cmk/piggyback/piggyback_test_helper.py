#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from tests.testlib.site import Site
from tests.testlib.utils import ServiceInfo


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

    payload = "".join(
        f"<<<<{hostname}>>>>\n<<<local>>>\n0 \"Local service piggybacked from $HOSTNAME$\" - created at '$(date +%s)'\n<<<<>>>>\n"
        for hostname in hostnames_piggybacked
    )

    bash_command = f"""echo '{payload}'"""
    rule_id = site.openapi.create_rule(
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
        yield
    finally:
        site.openapi.delete_rule(rule_id)


def get_piggybacked_service(
    central_site: Site, source_hostname: str, piggybacked_hostname: str
) -> ServiceInfo:
    services = central_site.get_host_services(piggybacked_hostname)
    return services[f"Local service piggybacked from {source_hostname}"]


def get_piggybacked_service_time(
    source_site: Site, source_hostname: str, piggybacked_hostname: str
) -> int:
    service = get_piggybacked_service(source_site, source_hostname, piggybacked_hostname)
    service_time_txt = service.summary.split("created at ")[1]
    return int(service_time_txt)


def piggybacked_service_discovered(
    central_site: Site, source_hostname: str, piggybacked_hostname: str
) -> bool:
    services = central_site.openapi.service_discovery_result(piggybacked_hostname)["extensions"]
    if isinstance(services, dict) and isinstance((check_table := services["check_table"]), dict):
        return f"local-Local service piggybacked from {source_hostname}" in check_table
    raise TypeError("Expected 'extensions' and its nested fields to be a dictionary")
