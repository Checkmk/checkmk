#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from subprocess import run as subprocess_run

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


def _reinstall_command(distro: str, specific_version: str = "") -> list[str]:
    if distro.startswith("almalinux"):
        return [
            "dnf",
            "reinstall",
            "-y",
            f"httpd-{specific_version}" if specific_version else "httpd",
        ]
    if distro.startswith("sles"):
        # It would be nice to run this:
        # arch = subprocess_run(
        #     "rpm --eval '%{_arch}'",
        #     shell=True,
        #     capture_output=True,
        #     encoding="utf-8",
        #     check=True,
        # ).stdout.strip()
        # return [
        #     "zypper",
        #     "install",
        #     "--force",
        #     "-y",
        #     f"apache2-{specific_version}.{arch}" if specific_version else "apache2",
        # ]
        # However, although this will re-install the same version of apache2
        # it will not trigger a restart of apache2 and by that not triggering
        # the checkmk postinstall hook adding the expected lines to the log file
        raise NotImplementedError()
    return [
        "sudo",
        "apt",
        "reinstall",
        f"apache2-bin={specific_version}" if specific_version else "apache2-bin",
    ]


def _query_version_command(distro: str) -> str:
    # see http://ftp.rpm.org/api/4.4.2.2/queryformat.html
    rpm_query = "rpm --query --all --queryformat '%{VERSION}-%{RELEASE}\n'"

    if distro.startswith("almalinux"):
        package = "httpd"
    elif distro.startswith("sles"):
        package = "apache2"
    else:
        return "dpkg -s apache2-bin | sed -n 's/^Version: //p'"

    return f"{rpm_query} {package}"


@pytest.mark.skipif(
    os.environ.get("DISTRO", "").startswith("sles"),
    reason="Reinstall on SLES does not trigger an apache2 restart",
)
def test_apache_restart_trigger(site: Site) -> None:
    # The intention of this test is to verify a successfull restart due to an update of apache
    assert site.is_running()
    previous_logs = site.read_file("var/log/apache/error_log")

    distro = os.environ.get("DISTRO", "")

    current_version = subprocess_run(
        _query_version_command(distro=distro),
        shell=True,
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    logger.info("Currently installed version of apache: %s", current_version)
    logger.info(
        "_reinstall_command: %s",
        _reinstall_command(
            distro=distro,
            specific_version=current_version,
        ),
    )
    process = run(
        _reinstall_command(
            distro=distro,
            specific_version=current_version,
        ),
        check=True,
        sudo=True,
    )
    logger.info("STDOUT: %s", process.stdout)
    for line in process.stdout.split("\n"):
        logger.info("%s", line)
    logger.info("STDERR: %s", process.stderr)
    for line in process.stderr.split("\n"):
        logger.info("%s", line)

    logs = site.read_file("var/log/apache/error_log")
    assert "caught SIGTERM, shutting down" in logs.removeprefix(previous_logs)
