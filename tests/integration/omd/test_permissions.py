#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import stat
from collections.abc import Iterator
from enum import IntFlag
from pathlib import Path

import pytest

from tests.testlib.site import Site


class Mode(IntFlag):
    """Merely aliases for the stat constants

    I found them hard to read, so perhaps that makes it easier?"""

    WORLD_READABLE = stat.S_IROTH
    WORLD_WRITEABLE = stat.S_IWOTH
    WORLD_EXECUTE = stat.S_IXOTH
    GROUP_WRITEABLE = stat.S_IWGRP


KNOWN_WORLD_WRITABLE_FILES = {
    "tmp/run/mkeventd/events",  # So others can write events
}
KNOWN_WORLD_READABLE_FILES = {
    "etc/omd/site.conf",  # Other sites use this to check for free ports
}


def has_permission(path: Path, mode_to_test: Mode) -> bool:
    return bool(path.stat().st_mode & mode_to_test)


def iter_dir(path: Path) -> Iterator[Path]:
    for sub_path in path.iterdir():
        if sub_path.is_symlink():
            logging.info("Skipping Symlink %s", sub_path)
            continue

        yield sub_path
        if sub_path.is_dir():
            yield from iter_dir(sub_path)


def get_site_file_permission(site: Site) -> list[tuple[int, str]]:
    return ast.literal_eval(
        site.python_helper("helper_get_site_file_permissions.py").check_output()
    )


@pytest.mark.parametrize(
    "mode, known_files_set",
    ((Mode.WORLD_WRITEABLE, KNOWN_WORLD_WRITABLE_FILES),),
)
def test_site_file_permissions(site: Site, mode: Mode, known_files_set: set[str]) -> None:
    offenders: set[str] = set()
    for file_mode, rel_path in get_site_file_permission(site):
        if (file_mode & mode) == 0:
            continue

        if rel_path in known_files_set:
            continue

        offenders.add(rel_path)

    assert not offenders, (
        f"Incorrect file permissions! Found writable file(s):\n{'\n'.join(offenders)}"
    )


def test_world_accessible_files_parents(site: Site) -> None:
    """files which are supposed to be accessible need their parents to be also accessible"""
    for file in KNOWN_WORLD_WRITABLE_FILES | KNOWN_WORLD_READABLE_FILES:
        path = site.root / file
        assert path.exists()
        for parent in path.parents:
            if not parent.is_relative_to(site.root):
                break
            assert has_permission(parent, Mode.WORLD_EXECUTE)


def test_version_file_permissions(site: Site) -> None:
    """Test that there are no writeable files in the version dir.

    Check for world writeable and group writeable
    Only the owner should be allowed to write.
    The ownership is checked in `test_version_file_ownership`.
    """
    writable_files = {
        str(p)
        for p in iter_dir(Path(site.version.version_path()))
        if has_permission(p, Mode.WORLD_WRITEABLE ^ Mode.GROUP_WRITEABLE)
    }
    assert not writable_files, (
        f"Incorrect file permissions! Found writable file(s):\n{'\n'.join(writable_files)}"
    )


def test_version_file_ownership(site: Site) -> None:
    """test that version files owned by root

    All files are supposed to be owned by root, hence the hard assert
    There are some files with omd as group, because of some caps, these are
    explicitly listed in the end, therefore the set construct"""

    path_to_version = Path(site.version.version_path())
    non_root_group = set()
    for p in iter_dir(path_to_version):
        assert p.owner() == "root", p
        if p.group() != "root":
            non_root_group.add(str(p.relative_to(path_to_version)))

    # These are exceptions, defined in omd/omd.spec.in
    exceptions = {
        "bin/mkeventd_open514",
        "lib/nagios/plugins/check_dhcp",
        "lib/nagios/plugins/check_icmp",
    }
    if not site.version.is_raw_edition():
        exceptions |= {
            "lib/cmc/icmpsender",
            "lib/cmc/icmpreceiver",
        }

    assert not non_root_group ^ exceptions
