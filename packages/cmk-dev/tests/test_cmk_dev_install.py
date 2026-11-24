# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from cmk_dev_site.cmk_dev_install import (
    CMK_DOWNLOAD_URL,
    create_parser,
    DevInstallArgs,
    distro_candidates,
    DistroVersionInfo,
    find_cached_deb,
    find_last_release,
    FolderLinkParser,
    parse_version,
    resolve_release_candidate_folder,
    select_package,
    setup_parser,
    TSBUILD_URL,
    validate_version_edition,
)
from cmk_dev_site.omd import (
    BaseVersion,
    CMKPackage,
    Edition,
    PartialVersion,
    VersionWithPatch,
    VersionWithReleaseCandidate,
    VersionWithReleaseDate,
)


def test_parse_version() -> None:
    assert parse_version("2.3.0") == BaseVersion(2, 3, 0)
    parsed_version = parse_version("2.3.0p1")
    assert isinstance(parsed_version, VersionWithPatch)
    assert parsed_version.base_version == BaseVersion(2, 3, 0)
    assert parsed_version.patch_type == "p"
    assert parsed_version.patch == 1


def test_parse_version_redirects_2_6_to_3_0() -> None:
    # there is no 2.6 release: 2.5.0 is followed by 3.0.0
    assert parse_version("2.6.0") == BaseVersion(3, 0, 0)

    partial = parse_version("2.6")
    assert isinstance(partial, PartialVersion)
    assert partial == BaseVersion(3, 0, 0)

    with_patch = parse_version("2.6.0p1")
    assert isinstance(with_patch, VersionWithPatch)
    assert with_patch.base_version == BaseVersion(3, 0, 0)
    assert with_patch.patch == 1

    daily = parse_version("2.6.0-daily")
    assert isinstance(daily, VersionWithReleaseDate)
    assert daily.base_version == BaseVersion(3, 0, 0)


def test_parse_version_leaves_other_versions_untouched() -> None:
    assert parse_version("2.5.0") == BaseVersion(2, 5, 0)
    assert isinstance(parse_version("2.5"), PartialVersion)
    assert parse_version("3.0.0") == BaseVersion(3, 0, 0)


def _mock_list_versions_with_date_side_effect(
    cmk_dates: list[str], tst_dates: list[str]
) -> Callable[[str, BaseVersion], list[VersionWithReleaseDate]]:
    def list_versions_with_date_side_effect(
        url: str, _: BaseVersion
    ) -> list[VersionWithReleaseDate]:
        cmk_versions = [
            VersionWithReleaseDate(BaseVersion(2, 5, 0), datetime.strptime(d, "%Y.%m.%d").date())
            for d in cmk_dates
        ]
        tst_versions = [
            VersionWithReleaseDate(BaseVersion(2, 5, 0), datetime.strptime(d, "%Y.%m.%d").date())
            for d in tst_dates
        ]
        if url == CMK_DOWNLOAD_URL:
            return cmk_versions
        if url == TSBUILD_URL:
            return tst_versions
        return []

    return list_versions_with_date_side_effect


@pytest.mark.parametrize(
    "download_urls,cmk_dates,tst_dates,expected_version",
    [
        pytest.param(
            [CMK_DOWNLOAD_URL, TSBUILD_URL],
            ["2025.11.06", "2025.11.07", "2025.11.08", "2025.11.09", "2025.11.10", "2025.11.11"],
            ["2025.11.09", "2025.11.10", "2025.11.11"],
            "2.5.0-2025.11.11",
            id="both_available",
        ),
        pytest.param(
            [CMK_DOWNLOAD_URL],
            ["2025.11.06", "2025.11.07", "2025.11.08", "2025.11.09", "2025.11.10", "2025.11.11"],
            [],
            "2.5.0-2025.11.11",
            id="only_cmk_available",
        ),
        pytest.param(
            [TSBUILD_URL],
            [],
            ["2025.11.09", "2025.11.10", "2025.11.11"],
            "2.5.0-2025.11.11",
            id="only_tst_available_no_cmk",
        ),
        pytest.param(
            [TSBUILD_URL],
            [],
            [],
            RuntimeError,
            id="No package available",
        ),
    ],
)
def test_find_last_release(
    download_urls: list[str],
    cmk_dates: list[str],
    tst_dates: list[str],
    expected_version: str | type[RuntimeError],
) -> None:
    mock_file_server = MagicMock()

    mock_file_server.list_versions_with_date.side_effect = (
        _mock_list_versions_with_date_side_effect(cmk_dates, tst_dates)
    )
    mock_file_server.url_exists.return_value = True

    if expected_version is RuntimeError:
        with pytest.raises(RuntimeError):
            find_last_release(
                download_urls=download_urls,
                file_server=mock_file_server,
                base_version=BaseVersion(2, 5, 0),
                edition=Edition.PRO,
                distro_codenames=["jammy"],
            )
    else:
        result = find_last_release(
            download_urls=download_urls,
            file_server=mock_file_server,
            base_version=BaseVersion(2, 5, 0),
            edition=Edition.PRO,
            distro_codenames=["jammy"],
        )

        assert str(result.version) == expected_version


def _make_pkg() -> CMKPackage:
    return CMKPackage(
        version=VersionWithPatch(base_version=BaseVersion(2, 5, 0), patch_type="p", patch=1),
        edition=Edition.PRO,
        distro_codename="jammy",
    )


def test_find_cached_deb_returns_path_when_exists(tmp_path: Path) -> None:
    pkg = _make_pkg()
    deb = tmp_path / pkg.package_name
    deb.touch()
    assert find_cached_deb(pkg, download_dir=tmp_path) == deb


def test_find_cached_deb_returns_none_when_missing(tmp_path: Path) -> None:
    pkg = _make_pkg()
    assert find_cached_deb(pkg, download_dir=tmp_path) is None


def test_distro_candidates_without_fallback() -> None:
    noble = DistroVersionInfo(version_id="24.04", version_codename="noble")
    assert distro_candidates(noble) == [noble]


def test_distro_candidates_falls_back_to_noble() -> None:
    resolute = DistroVersionInfo(version_id="26.04", version_codename="resolute")
    assert distro_candidates(resolute) == [
        resolute,
        DistroVersionInfo(version_id="24.04", version_codename="noble"),
    ]


def _file_server_with(existing_codename: str) -> MagicMock:
    def url_exists(url: str) -> bool:
        return f".{existing_codename}_" in url

    file_server = MagicMock()
    file_server.url_exists.side_effect = url_exists
    return file_server


def test_find_last_release_falls_back_to_older_distro() -> None:
    file_server = _file_server_with("noble")
    file_server.list_versions_with_date.return_value = [
        VersionWithReleaseDate(BaseVersion(2, 5, 0), datetime(2025, 11, 11).date())
    ]

    result = find_last_release(
        download_urls=[CMK_DOWNLOAD_URL],
        file_server=file_server,
        base_version=BaseVersion(2, 5, 0),
        edition=Edition.PRO,
        distro_codenames=["resolute", "noble"],
    )

    assert result.distro_codename == "noble"


@pytest.mark.parametrize(
    "existing_codename,expected_codename",
    [
        pytest.param("resolute", "resolute", id="native_available"),
        pytest.param("noble", "noble", id="fallback_available"),
        pytest.param("jammy", "noble", id="none_available"),
    ],
)
def test_select_package(existing_codename: str, expected_codename: str, tmp_path: Path) -> None:
    result = select_package(
        file_server=_file_server_with(existing_codename),
        download_urls=[CMK_DOWNLOAD_URL],
        version=VersionWithPatch(base_version=BaseVersion(2, 5, 0), patch_type="p", patch=1),
        edition=Edition.PRO,
        distro_codenames=["resolute", "noble"],
        download_dir=tmp_path,
    )

    assert result.distro_codename == expected_codename


def test_select_package_prefers_cached_native_package(tmp_path: Path) -> None:
    version = VersionWithPatch(base_version=BaseVersion(2, 5, 0), patch_type="p", patch=1)
    cached = CMKPackage(version=version, edition=Edition.PRO, distro_codename="resolute")
    (tmp_path / cached.package_name).touch()

    result = select_package(
        file_server=_file_server_with("noble"),
        download_urls=[CMK_DOWNLOAD_URL],
        version=version,
        edition=Edition.PRO,
        distro_codenames=["resolute", "noble"],
        download_dir=tmp_path,
    )

    assert result.distro_codename == "resolute"


def test_select_package_without_fallback_skips_lookup(tmp_path: Path) -> None:
    file_server = MagicMock()

    result = select_package(
        file_server=file_server,
        download_urls=[CMK_DOWNLOAD_URL],
        version=VersionWithPatch(base_version=BaseVersion(2, 5, 0), patch_type="p", patch=1),
        edition=Edition.PRO,
        distro_codenames=["noble"],
        download_dir=tmp_path,
    )

    assert result.distro_codename == "noble"
    file_server.url_exists.assert_not_called()


def test_validate_version_edition_pre_250_uses_old_editions() -> None:
    assert validate_version_edition(BaseVersion(2, 4, 0), None) == (
        BaseVersion(2, 4, 0),
        Edition.OLD_ENTERPRISE,
    )


def test_validate_version_edition_post_240_uses_new_editions() -> None:
    assert validate_version_edition(BaseVersion(2, 5, 0), None) == (
        BaseVersion(2, 5, 0),
        Edition.PRO,
    )


def test_validate_version_edition_supports_3x() -> None:
    assert validate_version_edition(BaseVersion(3, 0, 0), None) == (
        BaseVersion(3, 0, 0),
        Edition.PRO,
    )


def test_folder_link_parser_keeps_only_subfolders() -> None:
    parser = FolderLinkParser()
    parser.feed(
        '<a href="?C=N;O=D">Name</a><a href="/">Parent</a>'
        '<a href="2.4.0p40-rc1+security/">x</a><a href="2.5.0-2026.11.04/">x</a>'
        '<a href="check-mk-pro-2.5.0_0.noble_amd64.deb">x</a>'
    )
    assert parser.folders == ["2.4.0p40-rc1+security", "2.5.0-2026.11.04"]


@pytest.mark.parametrize(
    "folders,expected_folder",
    [
        pytest.param(
            ["2.4.0p40-rc1+security", "2.4.0p40-rc10", "2.4.0p4-rc1"],
            "2.4.0p40-rc1+security",
            id="suffixed",
        ),
        pytest.param(
            ["2.4.0p40-rc1+security", "2.4.0p40-rc1"],
            "2.4.0p40-rc1",
            id="prefers_plain",
        ),
    ],
)
def test_resolve_release_candidate_folder(folders: list[str], expected_folder: str) -> None:
    file_server = MagicMock()
    file_server.list_folders.return_value = folders
    rc = VersionWithReleaseCandidate(BaseVersion(2, 4, 0), "p", 40, 1)

    resolved = resolve_release_candidate_folder(file_server, TSBUILD_URL, rc)

    assert resolved.download_folder_name == expected_folder
    assert str(CMKPackage(resolved, Edition.OLD_ENTERPRISE)) == "2.4.0p40.cee"


def test_resolve_release_candidate_folder_not_found() -> None:
    file_server = MagicMock()
    file_server.list_folders.return_value = ["2.4.0p40-rc2+security"]
    rc = VersionWithReleaseCandidate(BaseVersion(2, 4, 0), "p", 40, 1)

    with pytest.raises(RuntimeError, match=r"2\.4\.0p40-rc1 not found"):
        resolve_release_candidate_folder(file_server, TSBUILD_URL, rc)


def test_path_argument_is_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "check-mk-pro-2.5.0p1_0.noble_amd64.deb").touch()
    monkeypatch.chdir(tmp_path)
    parser = create_parser()
    setup_parser(parser)

    args = parser.parse_args(
        ["-p", "./check-mk-pro-2.5.0p1_0.noble_amd64.deb"], namespace=DevInstallArgs()
    )

    assert args.path == tmp_path / "check-mk-pro-2.5.0p1_0.noble_amd64.deb"
