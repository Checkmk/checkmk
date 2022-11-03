#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import time
from pathlib import Path
from typing import Sequence

from tests.testlib.site import Site


def wait_for_baking_job(central_site: Site, expected_start_time: float) -> None:
    waiting_time = 1
    waiting_cycles = 20
    for _ in range(waiting_cycles):
        time.sleep(waiting_time)
        baking_status = central_site.openapi.get_baking_status()
        assert baking_status.state in (
            "running",
            "finished",
        ), f"Unexpected baking state: {baking_status}"
        assert (
            baking_status.started >= expected_start_time
        ), f"No baking job started after expected starting time: {expected_start_time}"
        if baking_status.state == "finished":
            return
    raise AssertionError(
        f"Now waiting {waiting_cycles*waiting_time} seconds for baking job to finish, giving up..."
    )


def get_package_type() -> str:
    if os.path.exists("/var/lib/dpkg/status"):
        return "linux_deb"
    if (
        os.path.exists("/var/lib/rpm")
        and os.path.exists("/bin/rpm")
        or os.path.exists("/usr/bin/rpm")
    ):
        return "linux_rpm"
    raise NotImplementedError(
        "package_type recognition for the current environment is not supported yet. Please"
        " implement it if needed"
    )


def execute(command: Sequence[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        command,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        check=False,
    )
    return proc


def install_package(package_path: Path) -> subprocess.CompletedProcess:
    package_type = get_package_type()
    if package_type == "linux_deb":
        return execute(["sudo", "dpkg", "-i", package_path.as_posix()])
    if package_type == "linux_rpm":
        return execute(
            ["sudo", "rpm", "-vU", "--oldpackage", "--replacepkgs", package_path.as_posix()]
        )
    raise NotImplementedError(
        f"Installation of package type {package_type} is not supported yet, please implement it"
    )
