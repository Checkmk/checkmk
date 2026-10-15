#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent package of the site, and installing it on the host under test."""

import logging
import subprocess
from pathlib import Path, PurePosixPath
from typing import Literal

from tests.testlib.system.agent import bake_agents
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site

logger = logging.getLogger(__name__)

AGENT_CTL = PurePosixPath("/usr/bin/cmk-agent-ctl")

PackageType = Literal["linux_deb", "linux_rpm"]


def package_type(host: HostUnderTest) -> PackageType:
    if host.run(["test", "-e", "/var/lib/dpkg/status"], check=False).returncode == 0:
        return "linux_deb"
    if host.run(["sh", "-c", "command -v rpm"], check=False).returncode == 0:
        return "linux_rpm"
    raise RuntimeError("The host under test has neither dpkg nor rpm")


def download_agent_package(site: Site, os_type: PackageType, target_dir: Path) -> Path:
    """Download the generic agent package, baked first where the edition can bake.

    The Community edition cannot bake and serves the vanilla package instead.
    """
    if site.edition.is_community_edition():
        response = site.openapi.get(
            "domain-types/agent/actions/download/invoke",
            params={"os_type": os_type},
            headers={"Accept": "application/octet-stream"},
        )
    else:
        bake_agents(site)
        response = site.openapi.get(
            "domain-types/agent/actions/download_by_host/invoke",
            params={"agent_type": "generic", "os_type": os_type},
            headers={"Accept": "application/octet-stream"},
        )
    if not response.ok:
        raise RuntimeError(f"Agent download failed ({response.status_code}): {response.text}")

    suffix = {"linux_deb": "deb", "linux_rpm": "rpm"}[os_type]
    package = target_dir / f"check-mk-agent.{suffix}"
    with package.open(mode="wb") as file:
        for chunk in response.iter_content(chunk_size=None):
            file.write(chunk)
    return package


def install_agent_package(host: HostUnderTest, package: Path) -> subprocess.CompletedProcess[str]:
    """Install the package on the host and hand back what the maintainer scripts printed.

    The maintainer scripts run without `set -e`, and the super server dispatcher runs its loop
    in a pipeline subshell, so a deployment that went wrong still exits zero. Callers that care
    have to look at the output.
    """
    on_host = PurePosixPath("/tmp") / package.name
    host.copy_to(package, on_host)
    match package.suffix:
        case ".deb":
            command = ["dpkg", "-i", on_host.as_posix()]
        case ".rpm":
            command = ["rpm", "-vU", "--oldpackage", "--replacepkgs", on_host.as_posix()]
        case _:
            raise RuntimeError(f"Cannot install {package}, which is neither a .deb nor an .rpm")

    installation = host.run(command, sudo=True, check=False)
    logger.info("Agent installation output:\n%s\n%s", installation.stdout, installation.stderr)
    if installation.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} exited with {installation.returncode}.\n"
            f"stdout:\n{installation.stdout}\nstderr:\n{installation.stderr}"
        )

    if host.run(["test", "-x", AGENT_CTL.as_posix()], check=False).returncode != 0:
        # agents/scripts/super-server/0_systemd/setup deletes a controller it cannot run.
        raise RuntimeError(
            f"The agent package installed, but {AGENT_CTL} is missing.\n"
            f"stdout:\n{installation.stdout}\nstderr:\n{installation.stderr}"
        )
    return installation
