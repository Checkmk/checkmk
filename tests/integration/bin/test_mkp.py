#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.testlib.site import Site

from cmk.mkp_tool import Manifest, PackageName, PackagePart, PackageVersion


def test_mkp_help(site: Site) -> None:
    assert "usage: mkp [-h] [--debug]" in site.check_output(["mkp", "--help"])


def test_mkp_find(site: Site) -> None:
    assert "File" in site.check_output(["mkp", "find"])


def test_mkp_show_all(site: Site) -> None:
    assert "Local extension packages" in site.check_output(["mkp", "show-all"])


def test_mkp_list(site: Site) -> None:
    assert "Title" in site.check_output(["mkp", "list"])


def test_mkp_update_active(site: Site) -> None:
    site.check_output(["mkp", "update-active"])


def test_mkp_non_existing(site: Site) -> None:
    with pytest.raises(Exception):
        site.check_output(["mkp", "nubbel"])


def test_mkp_install_with_legacy_lib_file(site: Site) -> None:
    """We're removing the link local/lib/check_mk -> local/lib/python3/cmk.

    Make sure we can install mkps that expect the old structure."""
    # nothing there yet:
    assert not _local_stored_mkps(site)

    # add the mkp:
    with _build_mkp_with_legacy_lib_file(site) as manifest:
        assert _local_stored_mkps(site) == [manifest.name]
        assert not _installed_mkps(site)

        # We're set up.

        # We don't have the legacy structure:
        assert not site.file_exists(Path("local/lib/check_mk"))
        # But file refering to the old structure should be there:
        assert "check_mk/myfile.py" in _lib_files_of_mkp(site, manifest.name)
        # And we can still install the package:
        with _enabled_mkp(site, manifest.name):
            assert _installed_mkps(site) == [manifest.name]

            # We also should correctly recognise all files as part of the mkp,
            # so we only see the mkp file itself as unpackaged:
            unpackaged = _unpackaged_files(site)
            assert len(unpackaged) == 1
            assert unpackaged[0].endswith(f"{manifest.name}-{manifest.version}.mkp")

    # make sure we've cleared everything:
    assert not _local_stored_mkps(site)


@contextmanager
def _enabled_mkp(site: Site, name: str) -> Iterator[None]:
    _mkp_cmd(site, "enable", name)
    try:
        yield
    finally:
        _mkp_cmd(site, "disable", name)


@contextmanager
def _temporary_manifest_file(site: Site, manifest: Manifest) -> Iterator[Path]:
    manifest_file = Path("tmp/manifest.tmp")
    site.write_file(manifest_file, manifest.file_content())
    try:
        yield manifest_file
    finally:
        site.delete_file(manifest_file)


@contextmanager
def _legacy_lib_file(site: Site) -> Iterator[Path]:
    lib_dir = Path("local/lib")
    lib_file = Path("check_mk", "myfile.py")
    site_rel_lib_file = lib_dir / lib_file

    with _with_parent_dir(site, site_rel_lib_file):
        site.write_file(site_rel_lib_file, "")

        yield lib_file
        assert not site.file_exists(site_rel_lib_file)


@contextmanager
def _with_parent_dir(site: Site, path: Path) -> Iterator[None]:
    if site.file_exists(parent_dir := path.parent):
        yield
        return

    site.makedirs(parent_dir)
    try:
        yield
    finally:
        site.delete_dir(parent_dir)


@contextmanager
def _build_mkp_with_legacy_lib_file(site: Site) -> Iterator[Manifest]:
    with _legacy_lib_file(site) as lib_file:
        manifest = Manifest(
            title="Integration test",
            name=PackageName("integration_test"),
            description="Test mkp for integration tests",
            version=PackageVersion("1.0.0"),
            version_packaged="mkp-tool 1.0.0",
            version_min_required="2.0.0",
            version_usable_until="42.0.0",  # I should be retired by then
            author="",
            download_url="",
            files={PackagePart.LIB: [lib_file]},
        )
        with _temporary_manifest_file(site, manifest) as manifest_file:
            _mkp_cmd(site, "package", str(manifest_file))

        _mkp_cmd(site, "disable", manifest.name)

    try:
        yield manifest
    finally:
        _mkp_cmd(site, "remove", manifest.name)


def _mkp_cmd(site: Site, *args: str) -> str:
    return site.check_output(["mkp", "--debug", *args])


def _local_stored_mkps(site: Site) -> Sequence[str]:
    # Get the list of installed packages
    return [p["name"] for p in json.loads(_mkp_cmd(site, "list", "--json"))["stored"]["local"]]


def _installed_mkps(site: Site) -> Sequence[str]:
    # Get the list of installed packages
    return [p["name"] for p in json.loads(_mkp_cmd(site, "list", "--json"))["installed"]]


def _lib_files_of_mkp(site: Site, mkp_name: str) -> Sequence[str]:
    return json.loads(_mkp_cmd(site, "show", "--json", mkp_name))["files"].get("lib", [])


def _unpackaged_files(site: Site) -> Sequence[str]:
    return [p["file"] for p in json.loads(_mkp_cmd(site, "find", "--json"))]
