#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger
from pathlib import Path

import pytest

from cmk.mkp_tool import Installer, Manifest, PackageName, PackagePart, PackageVersion
from cmk.update_config.plugins.lib.remove_lib_check_mk_link import convert_manifests


def test_convert_manifests_ok(tmp_path: Path) -> None:
    manifest = Manifest(
        title="Test Package",
        name=(package_name := PackageName("test_package")),
        description="",
        version=PackageVersion("1.0.0"),
        version_packaged="",
        version_min_required="",
        version_usable_until="",
        author="",
        download_url="",
        files={
            PackagePart.LIB: [Path("check_mk/foo/bar.py")],
        },
    )
    (tmp_path / str(package_name)).write_text(manifest.file_content())

    installer = Installer(tmp_path)

    convert_manifests(tmp_path, getLogger(), dry_run=True)
    # Check that the manifest was not yet converted
    assert (m := installer.get_installed_manifest(package_name)) and m.files == {
        PackagePart.LIB: [Path("check_mk/foo/bar.py")]
    }

    convert_manifests(tmp_path, getLogger(), dry_run=False)
    # Check that the manifest was converted correctly
    assert (m := installer.get_installed_manifest(package_name)) and m.files == {
        PackagePart.LIB: [Path("python3/cmk/foo/bar.py")]
    }


def test_convert_manifests_unreadable(tmp_path: Path) -> None:
    (tmp_path / "hug@").write_text("this is not a manifest")

    with pytest.raises(Exception):
        convert_manifests(tmp_path, getLogger(), dry_run=True)
