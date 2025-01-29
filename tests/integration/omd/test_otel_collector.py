#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
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
