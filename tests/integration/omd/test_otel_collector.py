#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.testlib.site import Site
from tests.testlib.version import version_from_env

# Apply the skipif marker to all tests in this file for non Managed or Cloud edition
pytestmark = [
    pytest.mark.skipif(
        True
        not in [version_from_env().is_cloud_edition(), version_from_env().is_managed_edition()],
        reason="otel-collector only shipped with Cloud or Managed",
    )
]


def test_otel_collector_exists(site: Site) -> None:
    assert Path(site.root, "bin", "otelcol").exists()


@pytest.mark.skipif(
    os.environ.get("DISTRO") == "sles-15sp5",
    reason="No GLIBC_2.32 found, see CMK-20960",
)
@pytest.mark.parametrize(
    "command",
    [
        ["otelcol", "--help"],
        ["otelcol", "components"],
    ],
)
def test_otel_collector_command_availability(site: Site, command: list[str]) -> None:
    # Commands executed here should return with exit code 0
    site.check_output(command)


@pytest.mark.skipif(
    os.environ.get("DISTRO") == "sles-15sp5",
    reason="No GLIBC_2.32 found, see CMK-20960",
)
def test_otel_collector_version(site: Site) -> None:
    cmd = [
        "otelcol",
        "--version",
    ]
    assert "0.113.0" in site.check_output(cmd)


@contextmanager
def _modify_test_site(site: Site, hostname: str) -> Iterator[None]:
    rule_id = ""
    try:
        site.set_config("OPENTELEMETRY_COLLECTOR", "on", with_restart=True)
        site.openapi.hosts.create(
            hostname,
            attributes={
                "tag_address_family": "no-ip",
                "tag_agent": "special-agents",
                "tag_piggyback": "no-piggyback",
            },
            folder="/",
        )
        rule_id = site.openapi.rules.create(
            ruleset_name="special_agents:otel",
            value={"include_self_monitoring": True},
            conditions={
                "host_name": {
                    "match_on": [hostname],
                    "operator": "one_of",
                },
            },
            folder="/",
        )
        yield
    finally:
        if rule_id:
            site.openapi.rules.delete(rule_id)
        site.openapi.hosts.delete(hostname)
        site.set_config("OPENTELEMETRY_COLLECTOR", "off", with_restart=True)


def test_otel_collector_self_monitoring(site: Site) -> None:
    hostname = "otelhost"
    with _modify_test_site(site, hostname):
        site.ensure_running()
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname)
        result = site.openapi.service_discovery.get_discovery_result(hostname)
    assert result["extensions"] == {
        "check_table": {},
        "host_labels": {
            "cmk/otel/metrics": {
                # Means: section is there (special agent otel was executed!) but empty.
                # First dataset will be generated 60000ms after the start
                "value": "pending",
                "plugin_name": "otel_metrics",
            }
        },
        "vanished_labels": {},
        "changed_labels": {},
    }
