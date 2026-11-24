# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import date
from pathlib import Path

import pytest
from cmk_dev_site.cmk_dev_install import build_download_url
from cmk_dev_site.omd import (
    BaseVersion,
    CMKPackage,
    Edition,
    omd_hook_exists,
    VersionWithPatch,
    VersionWithReleaseCandidate,
    VersionWithReleaseDate,
)


def test_base_version_from_str() -> None:
    assert BaseVersion.from_str("2.3") == BaseVersion(2, 3)
    assert BaseVersion.from_str("2.3.0") == BaseVersion(2, 3, 0)
    with pytest.raises(ValueError):
        BaseVersion.from_str("2")
    with pytest.raises(ValueError):
        BaseVersion.from_str("2.3.0.1")


def test_base_version_str() -> None:
    assert str(BaseVersion(2, 3)) == "2.3.0"
    assert str(BaseVersion(2, 3, 1)) == "2.3.1"


def test_base_version_eq() -> None:
    assert BaseVersion(2, 3) == BaseVersion(2, 3, 0)
    assert BaseVersion(2, 3) != BaseVersion(2, 3, 1)


def test_base_version_lt() -> None:
    assert BaseVersion(2, 3) < BaseVersion(2, 3, 1)
    assert BaseVersion(2, 3) < BaseVersion(2, 4)
    assert BaseVersion(2, 3) < BaseVersion(3, 0)


def test_version_with_patch_str() -> None:
    assert str(VersionWithPatch(BaseVersion(2, 3), "p", 1)) == "2.3.0p1"


def test_version_with_release_candidate_str() -> None:
    assert str(VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1)) == "2.3.0p1"


def test_version_with_release_candidate_download_folder_name() -> None:
    assert (
        VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1).download_folder_name
        == "2.3.0p1-rc1"
    )


def test_version_with_release_date_str() -> None:
    assert str(VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1))) == "2.3.0-2025.01.01"


def test_version_with_release_date_iso_format() -> None:
    assert (
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)).iso_format()
        == "2.3.0-2025-01-01"
    )


def test_cmk_package_omd_version() -> None:
    # Test with BaseVersion
    pkg_base = CMKPackage(BaseVersion(2, 3), Edition.COMMUNITY)
    assert pkg_base.omd_version == "2.3.0.community"

    # Test with VersionWithPatch
    pkg_patch = CMKPackage(VersionWithPatch(BaseVersion(2, 3), "p", 1), Edition.PRO)
    assert pkg_patch.omd_version == "2.3.0p1.pro"

    # Test with VersionWithReleaseDate
    pkg_date = CMKPackage(
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)), Edition.ULTIMATE
    )
    assert pkg_date.omd_version == "2.3.0-2025.01.01.ultimate"

    # Test with VersionWithReleaseCandidate
    pkg_rc = CMKPackage(VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1), Edition.CLOUD)
    assert pkg_rc.omd_version == "2.3.0p1.cloud"


def test_cmk_package_package_raw_name() -> None:
    # Test with BaseVersion
    pkg_base = CMKPackage(BaseVersion(2, 3), Edition.COMMUNITY)
    assert pkg_base.package_raw_name == "check-mk-community-2.3.0"

    # Test with VersionWithPatch
    pkg_patch = CMKPackage(VersionWithPatch(BaseVersion(2, 3), "p", 1), Edition.PRO)
    assert pkg_patch.package_raw_name == "check-mk-pro-2.3.0p1"

    # Test with VersionWithReleaseDate
    pkg_date = CMKPackage(
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)), Edition.ULTIMATE
    )
    assert pkg_date.package_raw_name == "check-mk-ultimate-2.3.0-2025.01.01"

    # Test with VersionWithReleaseCandidate
    pkg_rc = CMKPackage(VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1), Edition.CLOUD)
    assert pkg_rc.package_raw_name == "check-mk-cloud-2.3.0p1"


def test_cmk_package_package_name() -> None:
    # Test with BaseVersion
    pkg_base = CMKPackage(BaseVersion(2, 3), Edition.COMMUNITY)
    assert pkg_base.package_name == "check-mk-community-2.3.0_0.noble_amd64.deb"

    # Test with VersionWithPatch
    pkg_patch = CMKPackage(
        VersionWithPatch(BaseVersion(2, 3), "p", 1),
        Edition.PRO,
        distro_codename="focal",
        arch="arm64",
    )
    assert pkg_patch.package_name == "check-mk-pro-2.3.0p1_0.focal_arm64.deb"

    # Test with VersionWithReleaseDate
    pkg_date = CMKPackage(
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)), Edition.ULTIMATE
    )
    assert pkg_date.package_name == "check-mk-ultimate-2.3.0-2025.01.01_0.noble_amd64.deb"

    # Test with VersionWithReleaseCandidate
    pkg_rc = CMKPackage(VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1), Edition.CLOUD)
    assert pkg_rc.package_name == "check-mk-cloud-2.3.0p1_0.noble_amd64.deb"


def test_cmk_package_base_version() -> None:
    assert CMKPackage(BaseVersion(2, 3), Edition.COMMUNITY).base_version == BaseVersion(2, 3)
    assert CMKPackage(
        VersionWithPatch(BaseVersion(2, 3), "p", 1), Edition.COMMUNITY
    ).base_version == BaseVersion(2, 3)
    assert CMKPackage(
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)),
        Edition.COMMUNITY,
    ).base_version == BaseVersion(2, 3)
    assert CMKPackage(
        VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1),
        Edition.COMMUNITY,
    ).base_version == BaseVersion(2, 3)


def test_build_download_url() -> None:
    base_url = "https://download.checkmk.com/checkmk"
    pkg = CMKPackage(BaseVersion(2, 3), Edition.COMMUNITY)
    expected_url = (
        "https://download.checkmk.com/checkmk/2.3.0/check-mk-community-2.3.0_0.noble_amd64.deb"
    )
    assert build_download_url(base_url, pkg) == expected_url

    pkg_patch = CMKPackage(VersionWithPatch(BaseVersion(2, 3), "p", 1), Edition.PRO)
    expected_url_patch = (
        "https://download.checkmk.com/checkmk/2.3.0p1/check-mk-pro-2.3.0p1_0.noble_amd64.deb"
    )
    assert build_download_url(base_url, pkg_patch) == expected_url_patch

    pkg_rc = CMKPackage(VersionWithReleaseCandidate(BaseVersion(2, 3), "p", 1, 1), Edition.CLOUD)
    expected_url_rc = (
        "https://download.checkmk.com/checkmk/2.3.0p1-rc1/check-mk-cloud-2.3.0p1_0.noble_amd64.deb"
    )
    assert build_download_url(base_url, pkg_rc) == expected_url_rc

    pkg_date = CMKPackage(
        VersionWithReleaseDate(BaseVersion(2, 3), date(2025, 1, 1)), Edition.ULTIMATE
    )
    expected_url_date = "https://download.checkmk.com/checkmk/2.3.0-2025.01.01/check-mk-ultimate-2.3.0-2025.01.01_0.noble_amd64.deb"
    assert build_download_url(base_url, pkg_date) == expected_url_date


def test_omd_hook_exists_finds_installed_hook(tmp_path: Path) -> None:
    hooks = tmp_path / "3.0.0.ultimate" / "lib" / "omd" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "MCP_SERVER").write_text("# Alias: Start daemon for the MCP server\n")

    assert omd_hook_exists("3.0.0.ultimate", "MCP_SERVER", installation_path=tmp_path)


def test_omd_hook_exists_false_for_missing_hook(tmp_path: Path) -> None:
    """The community edition ships no cmk-mcp package, so no MCP hooks."""
    hooks = tmp_path / "3.0.0.community" / "lib" / "omd" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "LIVESTATUS_TCP").write_text("# Alias: Send livestatus data via TCP\n")

    assert not omd_hook_exists("3.0.0.community", "MCP_SERVER", installation_path=tmp_path)


def test_omd_hook_exists_false_for_missing_version(tmp_path: Path) -> None:
    """Checkmk before 3.0.0 has no cmk-mcp package at all."""
    assert not omd_hook_exists("2.4.0.cee", "MCP_SERVER", installation_path=tmp_path)
