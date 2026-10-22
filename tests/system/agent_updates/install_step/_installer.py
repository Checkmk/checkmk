#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The attacker's path to the privileged install step.

A compromised agent user needs no controller to reach root. It may connect to the installer socket
and send an InstallRequest of its own, for a package and with a certificate that it chose. Only the
cases whose exploit is such a request use these helpers. All others take the controller's path.
"""

import base64
import json
import secrets
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import assert_never

from tests.system.agent_updates.install_step._agent import (
    AGENT_USER,
    INSTALLER_SOCKET,
    IntegratedUpdaterAgent,
    SigningKey,
)
from tests.system.agent_updates.install_step._units import wait_for_installer
from tests.testlib.system.agent import get_package_type
from tests.testlib.system.host_under_test import HostUnderTest

# The installer reads until the sender shuts down its write side, and answers nothing yet. The
# timeout turns an installer that never closes the connection into a failure instead of a hang.
_HAND_OVER = textwrap.dedent(
    """
    import socket, sys
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(60)
    connection.connect(sys.argv[1])
    connection.sendall(sys.argv[2].encode() + b"\\n")
    connection.shutdown(socket.SHUT_WR)
    while connection.recv(65536):
        pass
    """
)

_MARKER_PACKAGE = "cmk-40788-marker"
_MARKER_DIR = PurePosixPath("/usr/share", _MARKER_PACKAGE)


@dataclass(frozen=True)
class MarkerPackage:
    """A package that installs nothing but one file, so that its installation is observable."""

    local_path: Path
    marker: PurePosixPath
    build_dir: PurePosixPath

    @property
    def suffix(self) -> str:
        return self.local_path.suffix


def build_marker_package(host: HostUnderTest, target_dir: Path) -> MarkerPackage:
    """Build a package whose marker file is unique to this case, so that a marker left by
    another case cannot satisfy is_installed."""
    tag = secrets.token_hex(4)
    build_dir = PurePosixPath(
        host.run(
            ["mktemp", "-d", "--tmpdir", f"{_MARKER_PACKAGE}.XXXXXXXX"], sudo=True
        ).stdout.strip()
    )
    marker = _MARKER_DIR / tag
    match package_type := get_package_type(host):
        case "linux_deb":
            on_host = _build_deb(host, build_dir, marker)
        case "linux_rpm":
            on_host = _build_rpm(host, build_dir, marker)
        case _:
            assert_never(package_type)
    local_path = target_dir / f"marker-{tag}{PurePosixPath(on_host).suffix}"
    host.copy_from(on_host, local_path)
    return MarkerPackage(local_path=local_path, marker=marker, build_dir=build_dir)


def _build_deb(
    host: HostUnderTest, build_dir: PurePosixPath, marker: PurePosixPath
) -> PurePosixPath:
    control = textwrap.dedent(
        f"""\
        Package: {_MARKER_PACKAGE}
        Version: 1.0
        Architecture: all
        Maintainer: Checkmk QA <qa@checkmk.com>
        Description: Marks an installation by the agent installer in a system test
        """
    )
    root = build_dir / "root"
    _run_script(
        host,
        f"mkdir -p {root}/DEBIAN {root}{marker.parent}"
        f" && printf '%s' '{control}' > {root}/DEBIAN/control"
        f" && touch {root}{marker}"
        f" && dpkg-deb --build --root-owner-group {root} {build_dir}/marker.deb",
    )
    return build_dir / "marker.deb"


def _build_rpm(
    host: HostUnderTest, build_dir: PurePosixPath, marker: PurePosixPath
) -> PurePosixPath:
    spec = textwrap.dedent(
        f"""\
        Name: {_MARKER_PACKAGE}
        Version: 1.0
        Release: 1
        Summary: Marks an installation by the agent installer in a system test
        License: GPL-2.0-only
        BuildArch: noarch

        %description
        Marks an installation by the agent installer in a system test.

        %install
        mkdir -p %{{buildroot}}{marker.parent}
        touch %{{buildroot}}{marker}

        %files
        {marker}
        """
    )
    _run_script(
        host,
        f"mkdir -p {build_dir}"
        f" && printf '%s' '{spec}' > {build_dir}/marker.spec"
        f" && rpmbuild --quiet -bb --define '_topdir {build_dir}/rpmbuild' {build_dir}/marker.spec"
        f" && cp {build_dir}/rpmbuild/RPMS/noarch/*.rpm {build_dir}/marker.rpm",
    )
    return build_dir / "marker.rpm"


def _run_script(host: HostUnderTest, script: str) -> None:
    result = host.run(["sh", "-c", script], sudo=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Building the marker package failed:\n{result.stdout}{result.stderr}")


def is_installed(host: HostUnderTest, package: MarkerPackage) -> bool:
    return host.run(["test", "-e", package.marker.as_posix()], check=False).returncode == 0


def remove_marker_package(host: HostUnderTest, package: MarkerPackage) -> None:
    host.run(["rm", "-rf", package.build_dir.as_posix()], sudo=True)
    match package_type := get_package_type(host):
        case "linux_deb":
            host.run(["dpkg", "--purge", _MARKER_PACKAGE], sudo=True)
        case "linux_rpm":
            if host.run(["rpm", "-q", _MARKER_PACKAGE], check=False).returncode == 0:
                host.run(["rpm", "--erase", _MARKER_PACKAGE], sudo=True)
        case _:
            assert_never(package_type)


def signature(package: Path, key: SigningKey) -> dict[str, str]:
    """One entry of InstallRequest.signatures, in the form the site delivers it."""
    return {
        "certificate": key.certificate,
        "signature": base64.b64encode(key.sign(package.read_bytes())).decode("ascii"),
    }


def plant_package(
    host: HostUnderTest, agent: IntegratedUpdaterAgent, package: MarkerPackage
) -> PurePosixPath:
    """Put the package into the download directory as the agent user, under a valid name.

    The installer checks the place and the name before the signature, so a package that fails
    either is refused for a reason that says nothing about the trust anchors.
    """
    staging = PurePosixPath("/tmp", package.local_path.name)
    host.copy_to(package.local_path, staging)
    host.run(["chmod", "0644", staging.as_posix()], sudo=True)
    target = agent.download_dir / f"{secrets.token_hex(8)}{package.suffix}"
    host.run(["mkdir", "-p", agent.download_dir.as_posix()], user=AGENT_USER)
    host.run(["cp", staging.as_posix(), target.as_posix()], user=AGENT_USER)
    host.run(["rm", "-f", staging.as_posix()], sudo=True)
    return target


def write_as_agent_user(host: HostUnderTest, content: str, target: PurePosixPath) -> None:
    host.run(
        ["sh", "-c", 'printf "%s" "$1" > "$2"', "sh", content, target.as_posix()], user=AGENT_USER
    )


def _request(package: PurePosixPath, signatures: Sequence[dict[str, str]]) -> str:
    return json.dumps({"package": package.as_posix(), "signatures": list(signatures)})


def hand_over(
    host: HostUnderTest, package: PurePosixPath, signatures: Sequence[dict[str, str]]
) -> None:
    """Send one InstallRequest as the agent user, and wait until its instance has finished."""
    host.run(
        ["python3", "-c", _HAND_OVER, INSTALLER_SOCKET.as_posix(), _request(package, signatures)],
        user=AGENT_USER,
    )
    wait_for_installer(host)
