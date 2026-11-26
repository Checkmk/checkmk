#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Debian package declares how much disk space it needs (Installed-Size)."""

import os
import re
import subprocess
import tarfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

_AGENT_DEB = re.compile(r"/share/check_mk/agents/check-mk-agent_[^/]+\.deb$")


@pytest.fixture(name="deb_path")
def fixture_deb_path(package_path: str) -> Path:
    if not package_path.endswith(".deb"):
        pytest.skip(f"{os.path.basename(package_path)}: Installed-Size is a Debian control field")
    return Path(package_path)


def _installed_size_kib(deb: Path) -> int:
    """The declared Installed-Size, 0 if the package does not declare one."""
    field = subprocess.check_output(["dpkg-deb", "--field", str(deb), "Installed-Size"]).strip()
    return int(field) if field else 0


@contextmanager
def _data_tar(deb: Path) -> Iterator[tarfile.TarFile]:
    """Stream the files the package installs, without extracting them."""
    with subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(deb)], stdout=subprocess.PIPE) as proc:
        assert proc.stdout is not None
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            yield tar
    if proc.returncode:
        raise RuntimeError(f"dpkg-deb --fsys-tarfile {deb} failed with {proc.returncode}")


def _kib(size: int) -> int:
    return (size + 1023) // 1024


def _disk_usage_kib(member: tarfile.TarInfo) -> int:
    """The space an entry takes once installed, estimated like dpkg-gencontrol does."""
    if member.islnk():
        return 0  # shares the data of the file it points to
    if member.isreg():
        return _kib(member.size)
    if member.issym():
        return _kib(len(member.linkname.encode()))
    return 1


def test_installed_size_matches_packaged_files(deb_path: Path) -> None:
    with _data_tar(deb_path) as tar:
        packaged_kib = sum(_disk_usage_kib(member) for member in tar)

    assert _installed_size_kib(deb_path) == pytest.approx(packaged_kib, rel=0.01)


def test_agent_debs_declare_installed_size(deb_path: Path, tmp_path: Path) -> None:
    agent_debs = []
    with _data_tar(deb_path) as tar:
        for member in tar:
            if member.isreg() and _AGENT_DEB.search(member.name):
                assert (content := tar.extractfile(member)) is not None
                (agent_deb := tmp_path / Path(member.name).name).write_bytes(content.read())
                agent_debs.append(agent_deb)

    assert agent_debs, "The package ships no agent .deb packages"
    assert not [d.name for d in agent_debs if _installed_size_kib(d) <= 0]
