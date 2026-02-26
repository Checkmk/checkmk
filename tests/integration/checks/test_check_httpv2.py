#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Consolidate tests validating `check_httpv2` executable.

`check_httpv2` is an active check maintained by Checkmk.
"""

import logging
from collections.abc import Callable, Iterator
from pathlib import Path
from subprocess import CalledProcessError

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="check_httpv2", scope="package")
def fixture_check_httpv2(site: Site) -> Iterator[Path]:
    """Return the path of `check_httpv2` plugin, present within the Checkmk site."""
    plugin_path = Path("lib") / "nagios" / "plugins" / "check_httpv2"
    yield site.root / plugin_path


def base_cmd(site: Site) -> list[str]:
    """Return the simplest command required to run `check_httpv2`."""
    return ["--url", f"http://{site.http_address}:{site.apache_port}"]


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(lambda site: base_cmd(site), id="url"),
        pytest.param(lambda site: base_cmd(site) + ["--server", site.http_address], id="server-ip"),
        pytest.param(lambda site: base_cmd(site) + ["--server", "localhost"], id="server-name"),
    ],
)
def test_cli(site: Site, check_httpv2: Path, args: Callable[[Site], list[str]]) -> None:
    """Validate the usage of `check_httpv2` CLI arguments."""
    try:
        cmd = [str(check_httpv2)] + args(site)
        site.run(cmd)
    except CalledProcessError as excp:
        excp.add_note(
            f"\n'{check_httpv2.name}' execution resulted in unexpected failure!\n"
            f"Command: {' '.join(cmd)}"
        )
        raise excp
