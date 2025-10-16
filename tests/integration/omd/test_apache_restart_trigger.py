#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import run

LOGGER = logging.getLogger(__name__)


def _reinstall_command(distro: str) -> list[str]:
    if distro.startswith("almalinux"):
        return ["dnf", "reinstall", "httpd", "-y"]
    if distro.startswith("sles"):
        # It would be nice to run this:
        # return ["zypper", "install", "--force", "-y", "apache2"]
        # However, this will install a newer version of apache2, which on `sles-15sp5` is not
        # compatible with apache2-prefork. It might be possible to work around this, but not worth
        # it in my opinion.
        raise NotImplementedError()
    return ["sudo", "apt", "reinstall", "apache2-bin"]


@pytest.mark.skipif(
    os.environ.get("DISTRO", "").startswith("sles"), reason="No reinstall command available on sles"
)
def test_apache_restart_trigger(site: Site) -> None:
    assert site.is_running()
    previous_logs = site.read_file("var/log/apache/error_log")
    process = run(_reinstall_command(os.environ.get("DISTRO", "")), check=True, sudo=True)
    LOGGER.info("STDOUT: %s", process.stdout)
    LOGGER.info("STDERR: %s", process.stderr)
    logs = site.read_file("var/log/apache/error_log")
    assert "caught SIGTERM, shutting down" in logs.removeprefix(previous_logs)
