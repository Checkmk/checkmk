#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Debian package declares how much disk space it needs (Installed-Size)."""

import os
import re
import stat
from pathlib import Path

import pytest

from tests.testlib.common.utils2 import run
from tests.testlib.system.package_manager import (
    ABCPackageManager,
    PackageManagerDEB,
    PACKAGES_DIR,
)
from tests.testlib.system.site import Site

_APT_SPACE_MESSAGE = re.compile(
    r"After this operation, ([\d.,]+) ([kMGT]?)B of additional disk space will be used\."
)
_SI_FACTORS = {"": 1, "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}


@pytest.fixture(name="deb_package_manager")
def fixture_deb_package_manager() -> PackageManagerDEB:
    package_manager = ABCPackageManager.factory()
    if not isinstance(package_manager, PackageManagerDEB):
        pytest.skip("DEB-only: Installed-Size is a Debian control field")
    return package_manager


@pytest.fixture(name="installed_package")
def fixture_installed_package(deb_package_manager: PackageManagerDEB, site: Site) -> str:
    return deb_package_manager.installed_package_name(
        site.package.edition, site.package.version.version
    )


@pytest.fixture(name="deb_file")
def fixture_deb_file(deb_package_manager: PackageManagerDEB, site: Site) -> Path:
    deb_file = PACKAGES_DIR / deb_package_manager.package_name(
        site.package.edition, site.package.version.version
    )
    if not deb_file.exists():
        pytest.skip(f"Package file {deb_file} is not available (only installed)")
    return deb_file


def _kib(size: int) -> int:
    return (size + 1023) // 1024


def _installed_files_kib(package: str) -> int:
    """Estimate the size of the installed files like dpkg-gencontrol does."""
    total = 0
    seen_inodes: set[tuple[int, int]] = set()
    for line in run(["dpkg-query", "--listfiles", package]).stdout.splitlines():
        try:
            st = os.lstat(line)
        except FileNotFoundError:
            continue  # e.g. removed by a maintainer script
        if stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            if st.st_nlink > 1 and stat.S_ISREG(st.st_mode):
                if (st.st_dev, st.st_ino) in seen_inodes:
                    continue
                seen_inodes.add((st.st_dev, st.st_ino))
            total += _kib(st.st_size)
        else:
            total += 1
    return total


def test_installed_size_matches_installed_files(installed_package: str) -> None:
    declared_kib = int(
        run(["dpkg-query", "--show", "--showformat=${Installed-Size}", installed_package]).stdout
    )

    assert declared_kib == pytest.approx(_installed_files_kib(installed_package), rel=0.01)


@pytest.mark.usefixtures("deb_package_manager")
def test_agent_debs_declare_installed_size(site: Site) -> None:
    agent_debs = sorted((site.root / "share/check_mk/agents").glob("check-mk-agent_*.deb"))
    assert agent_debs, "The site ships no agent .deb packages"

    for agent_deb in agent_debs:
        installed_size = run(["dpkg-deb", "--field", str(agent_deb), "Installed-Size"]).stdout
        assert int(installed_size) > 0, agent_deb


def _status_without(package: str, target: Path) -> Path:
    """A copy of the dpkg database in which `package` is not installed."""
    stanzas = Path("/var/lib/dpkg/status").read_text().split("\n\n")
    target.write_text("\n\n".join(s for s in stanzas if not s.startswith(f"Package: {package}\n")))
    return target


def _apt_install_output(deb_file: Path, status: Path, tmp_path: Path) -> str:
    """Let apt plan the installation of `deb_file` without changing the system.

    Debug::pkgDPkgPM makes apt print the dpkg calls instead of running them. The
    settings go to APT_CONFIG, which apt reads before anything else, so that the
    system's apt.conf.d with its dpkg hooks (e.g. debconf preconfiguration) is
    never loaded. State, cache and logs are redirected to `tmp_path`.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    (tmp_path / "archives" / "partial").mkdir(parents=True)
    (tmp_path / "log").mkdir()
    (sources := tmp_path / "sources.list").touch()
    settings = {
        "Debug::pkgDPkgPM": "true",
        "Dir::Etc::Main": empty_dir / "none",
        "Dir::Etc::Parts": empty_dir,
        "Dir::Etc::SourceList": sources,
        "Dir::Etc::SourceParts": empty_dir,
        "Dir::State": tmp_path / "state",
        "Dir::State::status": status,
        "Dir::Cache": tmp_path / "cache",
        "Dir::Cache::Archives": tmp_path / "archives",
        "Dir::Log": tmp_path / "log",
    }
    (apt_conf := tmp_path / "apt.conf").write_text(
        "".join(f'{key} "{value}";\n' for key, value in settings.items())
    )
    return run(
        ["apt-get", "install", "--yes", str(deb_file)],
        check=False,
        env={
            **os.environ,
            "APT_CONFIG": str(apt_conf),
            "LC_ALL": "C",
            "DEBIAN_FRONTEND": "noninteractive",
        },
    ).stdout


def test_apt_announces_required_disk_space(
    installed_package: str, deb_file: Path, tmp_path: Path
) -> None:
    declared_kib = int(run(["dpkg-deb", "--field", str(deb_file), "Installed-Size"]).stdout)
    status = _status_without(installed_package, tmp_path / "status")

    output = _apt_install_output(deb_file, status, tmp_path)

    assert (match := _APT_SPACE_MESSAGE.search(output)), output
    announced_bytes = float(match.group(1).replace(",", "")) * _SI_FACTORS[match.group(2)]
    # apt rounds to three significant digits
    assert announced_bytes == pytest.approx(declared_kib * 1024, rel=0.01)
