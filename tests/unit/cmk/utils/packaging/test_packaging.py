#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import shutil
import tarfile
from collections.abc import Callable, Iterable, Mapping
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import cmk.utils.packaging as packaging
import cmk.utils.paths


def _read_package_info(pacname: packaging.PackageName) -> packaging.PackageInfo:
    package_info = packaging.read_package_info_optionally(
        packaging.package_dir() / pacname, logging.getLogger()
    )
    assert package_info is not None
    return package_info


@pytest.fixture(autouse=True)
def package_dir() -> Iterable[None]:
    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(str(packaging.package_dir()))


@pytest.fixture(autouse=True)
def clean_dirs() -> Iterable[None]:
    paths = [Path(p.path) for p in packaging.PACKAGE_PARTS] + [
        cmk.utils.paths.local_optional_packages_dir,
        cmk.utils.paths.local_enabled_packages_dir,
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    yield

    for path in paths:
        shutil.rmtree(str(path))


@pytest.fixture(name="mkp_bytes")
def fixture_mkp_bytes(build_setup_search_index: Mock) -> bytes:
    # Create package information
    _create_simple_test_package(packaging.PackageName("aaa"))
    package_info = _read_package_info(packaging.PackageName("aaa"))

    # Build MKP in memory
    mkp = packaging.create_mkp_object(package_info)

    # Remove files from local hierarchy
    packaging.uninstall(package_info)
    build_setup_search_index.assert_called_once()
    build_setup_search_index.reset_mock()
    assert packaging._package_exists(packaging.PackageName("aaa")) is False

    return mkp


@pytest.fixture(name="build_setup_search_index")
def fixture_build_setup_search_index_background(mocker: MockerFixture) -> Mock:
    return mocker.patch(
        "cmk.utils.packaging._build_setup_search_index_background",
        side_effect=lambda: None,
    )


@pytest.fixture(name="reload_apache")
def fixture_reload_apache(mocker: MockerFixture) -> Callable[[], None]:
    return mocker.patch(
        "cmk.utils.packaging._reload_apache",
        side_effect=lambda: None,
    )


def test_get_permissions_unknown_path() -> None:
    with pytest.raises(packaging.PackageException):
        assert packaging._get_permissions("lala")


@pytest.mark.parametrize(
    "path,expected",
    [
        (str(cmk.utils.paths.local_checks_dir), 0o644),
        (str(cmk.utils.paths.local_bin_dir), 0o755),
    ],
)
def test_get_permissions(path, expected) -> None:  # type:ignore[no-untyped-def]
    assert packaging._get_permissions(path) == expected


def test_package_dir() -> None:
    assert isinstance(packaging.package_dir(), Path)


def _create_simple_test_package(pacname: packaging.PackageName) -> packaging.PackageInfo:
    _create_test_file(pacname)
    package_info = packaging.package_info_template(pacname)

    package_info.files = {
        "checks": [pacname],
    }

    packaging.create(package_info)
    return _read_package_info(pacname)


def _create_test_file(name):
    check_path = cmk.utils.paths.local_checks_dir.joinpath(name)
    with check_path.open("w", encoding="utf-8") as f:
        f.write("lala\n")


def test_create() -> None:
    assert packaging.installed_names() == []
    _create_simple_test_package(packaging.PackageName("aaa"))
    assert packaging.installed_names() == ["aaa"]


def test_create_twice() -> None:
    _create_simple_test_package(packaging.PackageName("aaa"))

    with pytest.raises(packaging.PackageException):
        _create_simple_test_package(packaging.PackageName("aaa"))


def test_read_package_info() -> None:
    _create_simple_test_package(packaging.PackageName("aaa"))
    package_info = _read_package_info(packaging.PackageName("aaa"))
    assert package_info.version == "1.0.0"
    assert packaging.package_num_files(package_info) == 1


def test_read_package_info_not_existing() -> None:
    assert (
        packaging.read_package_info_optionally(packaging.package_dir() / "aaa", logging.getLogger())
        is None
    )


def test_edit_not_existing() -> None:
    new_package_info = packaging.package_info_template(packaging.PackageName("aaa"))
    new_package_info.version = packaging.PackageVersion("2.0.0")

    with pytest.raises(packaging.PackageException):
        packaging.edit(packaging.PackageName("aaa"), new_package_info)


def test_edit() -> None:
    new_package_info = packaging.package_info_template(packaging.PackageName("aaa"))
    new_package_info.version = packaging.PackageVersion("2.0.0")

    package_info = _create_simple_test_package(packaging.PackageName("aaa"))
    assert package_info.version == packaging.PackageVersion("1.0.0")

    packaging.edit(packaging.PackageName("aaa"), new_package_info)

    assert _read_package_info(packaging.PackageName("aaa")).version == packaging.PackageVersion(
        "2.0.0"
    )


def test_edit_rename() -> None:
    new_package_info = packaging.package_info_template(packaging.PackageName("bbb"))

    _create_simple_test_package(packaging.PackageName("aaa"))

    packaging.edit(packaging.PackageName("aaa"), new_package_info)

    assert _read_package_info(packaging.PackageName("bbb")).name == packaging.PackageName("bbb")
    assert (
        packaging.read_package_info_optionally(packaging.package_dir() / "aaa", logging.getLogger())
        is None
    )


def test_edit_rename_conflict() -> None:
    new_package_info = packaging.package_info_template(packaging.PackageName("bbb"))
    _create_simple_test_package(packaging.PackageName("aaa"))
    _create_simple_test_package(packaging.PackageName("bbb"))

    with pytest.raises(packaging.PackageException):
        packaging.edit(packaging.PackageName("aaa"), new_package_info)


def test_install(mkp_bytes: bytes, build_setup_search_index: Mock) -> None:
    packaging._install(mkp_bytes, allow_outdated=False, post_package_change_actions=True)
    build_setup_search_index.assert_called_once()

    assert packaging._package_exists(packaging.PackageName("aaa")) is True
    package_info = _read_package_info(packaging.PackageName("aaa"))
    assert package_info.version == "1.0.0"
    assert package_info.files["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_release_not_existing() -> None:
    with pytest.raises(packaging.PackageException):
        packaging.release(packaging.PackageName("abc"))


def test_release() -> None:
    _create_simple_test_package(packaging.PackageName("aaa"))
    assert packaging._package_exists(packaging.PackageName("aaa")) is True
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()

    packaging.release(packaging.PackageName("aaa"))

    assert packaging._package_exists(packaging.PackageName("aaa")) is False
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_write_file() -> None:
    package_info = _create_simple_test_package(packaging.PackageName("aaa"))

    mkp = packaging.create_mkp_object(package_info)

    with tarfile.open(fileobj=BytesIO(mkp), mode="r:gz") as tar:
        assert sorted(tar.getnames()) == sorted(["info", "info.json", "checks.tar"])

        info_file = tar.extractfile("info")
        assert info_file is not None
        info = ast.literal_eval(info_file.read().decode())

        info_json_file = tar.extractfile("info.json")
        assert info_json_file is not None
        info2 = json.loads(info_json_file.read())

    assert info["name"] == "aaa"
    assert info2["name"] == "aaa"


def test_uninstall(build_setup_search_index: Mock) -> None:
    package_info = _create_simple_test_package(packaging.PackageName("aaa"))
    packaging.uninstall(package_info)
    build_setup_search_index.assert_called_once()
    assert packaging._package_exists(packaging.PackageName("aaa")) is False


def test_unpackaged_files_none() -> None:
    assert {part.ident: files for part, files in packaging.unpackaged_files().items()} == {
        "agent_based": [],
        "agents": [],
        "alert_handlers": [],
        "bin": [],
        "checkman": [],
        "checks": [],
        "doc": [],
        "ec_rule_packs": [],
        "inventory": [],
        "lib": [],
        "locales": [],
        "mibs": [],
        "notifications": [],
        "pnp-templates": [],
        "web": [],
        "gui": [],
    }


def test_unpackaged_files() -> None:
    _create_test_file("abc")

    p = cmk.utils.paths.local_doc_dir.joinpath("docxx")
    with p.open("w", encoding="utf-8") as f:
        f.write("lala\n")

    p = cmk.utils.paths.local_agent_based_plugins_dir.joinpath("dada")
    with p.open("w", encoding="utf-8") as f:
        f.write("huhu\n")

    assert {part.ident: files for part, files in packaging.unpackaged_files().items()} == {
        "agent_based": ["dada"],
        "agents": [],
        "alert_handlers": [],
        "bin": [],
        "checkman": [],
        "checks": ["abc"],
        "doc": ["docxx"],
        "ec_rule_packs": [],
        "inventory": [],
        "lib": [],
        "locales": [],
        "mibs": [],
        "notifications": [],
        "pnp-templates": [],
        "web": [],
        "gui": [],
    }


# TODO:
# def test_package_part_info()


def test_get_optional_package_infos_none() -> None:
    assert packaging.get_optional_package_infos(packaging.PackageStore()) == {}


def test_get_optional_package_infos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mkp_dir = tmp_path.joinpath("optional_packages")
    mkp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "optional_packages_dir", mkp_dir)

    # Create package
    _create_simple_test_package(packaging.PackageName("optional"))
    expected_package_info = _read_package_info(packaging.PackageName("optional"))

    assert packaging.get_optional_package_infos(packaging.PackageStore()) == {
        "optional-1.0.0.mkp": (expected_package_info, True)
    }


def test_parse_package_info_pre_160() -> None:
    # make sure we can read old packages without "usable until"
    raw = {
        k: v
        for k, v in packaging.package_info_template(packaging.PackageName("testpackage"))
        .dict(by_alias=True)
        .items()
        if k != "version.usable_until"
    }
    assert packaging.PackageInfo.parse_python_string(repr(raw)).version_usable_until is None


def test_parse_package_info() -> None:
    info_str = packaging.package_info_template(packaging.PackageName("pkgname")).file_content()
    assert packaging.PackageInfo.parse_python_string(info_str).name == packaging.PackageName(
        "pkgname"
    )


def test_reload_gui_without_gui_files(  # type:ignore[no-untyped-def]
    reload_apache, build_setup_search_index
) -> None:
    package = packaging.package_info_template(packaging.PackageName("ding"))
    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_not_called()


def test_reload_gui_with_gui_part(  # type:ignore[no-untyped-def]
    reload_apache, build_setup_search_index
) -> None:
    package = packaging.package_info_template(packaging.PackageName("ding"))
    package.files = {"gui": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()


def test_reload_gui_with_web_part(  # type:ignore[no-untyped-def]
    reload_apache, build_setup_search_index
) -> None:
    package = packaging.package_info_template(packaging.PackageName("ding"))
    package.files = {"web": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()


def _get_test_package_info(properties: Mapping) -> packaging.PackageInfo:
    pi = packaging.package_info_template(packaging.PackageName("test-package"))
    for k, v in properties.items():
        setattr(pi, k, v)
    return pi


@pytest.mark.parametrize(
    "package_info, site_version",
    [
        (_get_test_package_info({"version_usable_until": "1.6.0"}), "2.0.0i1"),
        (_get_test_package_info({"version_usable_until": "2.0.0i1"}), "2.0.0i2"),
        (_get_test_package_info({"version_usable_until": "2.0.0"}), "2.0.0"),
        (_get_test_package_info({"version_usable_until": "1.6.0"}), "1.6.0-2010.02.01"),
        (_get_test_package_info({"version_usable_until": "1.6.0-2010.02.01"}), "1.6.0"),
    ],
)
def test_raise_for_too_new_cmk_version_raises(
    package_info: packaging.PackageInfo, site_version: str
) -> None:
    with pytest.raises(packaging.PackageException):
        packaging._raise_for_too_new_cmk_version(package_info, site_version)


@pytest.mark.parametrize(
    "package_info, site_version",
    [
        (_get_test_package_info({"version_usable_until": None}), "2.0.0i1"),
        (_get_test_package_info({"version_usable_until": "2.0.0"}), "2.0.0i1"),
        (_get_test_package_info({"version_usable_until": "2.0.0"}), "2010.02.01"),
        (_get_test_package_info({"version_usable_until": ""}), "1.6.0"),
        (_get_test_package_info({"version_usable_until": "1.6.0"}), ""),
    ],
)
def test_raise_for_too_new_cmk_version_ok(
    package_info: packaging.PackageInfo, site_version: str
) -> None:
    packaging._raise_for_too_new_cmk_version(package_info, site_version)
