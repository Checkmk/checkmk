#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import shutil
import tarfile
from collections.abc import Iterable, Mapping
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import cmk.utils.packaging as packaging
import cmk.utils.packaging._installed
import cmk.utils.paths


def _read_manifest(pacname: packaging.PackageName) -> packaging.Manifest:
    manifest = packaging.get_installed_manifest(pacname)
    assert manifest is not None
    return manifest


@pytest.fixture(autouse=True)
def _packages_dir() -> Iterable[None]:
    cmk.utils.packaging._installed.PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(cmk.utils.packaging._installed.PACKAGES_DIR)


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
    manifest = _read_manifest(packaging.PackageName("aaa"))

    # Build MKP in memory
    mkp = packaging.create_mkp_object(manifest)

    # Remove files from local hierarchy
    packaging.uninstall(manifest)
    build_setup_search_index.assert_called_once()
    build_setup_search_index.reset_mock()
    assert packaging.is_installed(packaging.PackageName("aaa")) is False

    return mkp


@pytest.fixture(name="build_setup_search_index")
def fixture_build_setup_search_index_background(mocker: MockerFixture) -> Mock:
    return mocker.patch(
        "cmk.utils.packaging._build_setup_search_index_background",
        side_effect=lambda: None,
    )


@pytest.fixture(name="reload_apache")
def fixture_reload_apache(mocker: MockerFixture) -> Mock:
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
def test_get_permissions(path: str, expected: int) -> None:
    assert packaging._get_permissions(path) == expected


def _create_simple_test_package(pacname: packaging.PackageName) -> packaging.Manifest:
    _create_test_file(pacname)
    manifest = packaging.manifest_template(pacname)

    manifest.files = {
        "checks": [pacname],
    }

    packaging.create(manifest)
    return _read_manifest(pacname)


def _create_test_file(name):
    check_path = cmk.utils.paths.local_checks_dir.joinpath(name)
    with check_path.open("w", encoding="utf-8") as f:
        f.write("lala\n")


def test_create() -> None:
    name = packaging.PackageName("aaa")
    assert not packaging.is_installed(name)
    _create_simple_test_package(name)
    assert packaging.is_installed(name)


def test_create_twice() -> None:
    _create_simple_test_package(packaging.PackageName("aaa"))

    with pytest.raises(packaging.PackageException):
        _create_simple_test_package(packaging.PackageName("aaa"))


def test_edit_not_existing() -> None:
    new_manifest = packaging.manifest_template(packaging.PackageName("aaa"))
    new_manifest.version = packaging.PackageVersion("2.0.0")

    with pytest.raises(packaging.PackageException):
        packaging.edit(packaging.PackageName("aaa"), new_manifest)


def test_edit() -> None:
    new_manifest = packaging.manifest_template(packaging.PackageName("aaa"))
    new_manifest.version = packaging.PackageVersion("2.0.0")

    manifest = _create_simple_test_package(packaging.PackageName("aaa"))
    assert manifest.version == packaging.PackageVersion("1.0.0")

    packaging.edit(packaging.PackageName("aaa"), new_manifest)

    assert _read_manifest(packaging.PackageName("aaa")).version == packaging.PackageVersion("2.0.0")


def test_edit_rename() -> None:
    new_manifest = packaging.manifest_template(packaging.PackageName("bbb"))

    _create_simple_test_package(packaging.PackageName("aaa"))

    packaging.edit(packaging.PackageName("aaa"), new_manifest)

    assert _read_manifest(packaging.PackageName("bbb")).name == packaging.PackageName("bbb")
    assert (
        packaging.get_installed_manifest(packaging.PackageName("aaa"), logging.getLogger()) is None
    )


def test_edit_rename_conflict() -> None:
    new_manifest = packaging.manifest_template(packaging.PackageName("bbb"))
    _create_simple_test_package(packaging.PackageName("aaa"))
    _create_simple_test_package(packaging.PackageName("bbb"))

    with pytest.raises(packaging.PackageException):
        packaging.edit(packaging.PackageName("aaa"), new_manifest)


def test_install(mkp_bytes: bytes, build_setup_search_index: Mock) -> None:
    packaging._install(mkp_bytes, allow_outdated=False, post_package_change_actions=True)
    build_setup_search_index.assert_called_once()

    assert packaging.is_installed(packaging.PackageName("aaa")) is True
    manifest = _read_manifest(packaging.PackageName("aaa"))
    assert manifest.version == "1.0.0"
    assert manifest.files["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_release_not_existing() -> None:
    with pytest.raises(packaging.PackageException):
        packaging.release(packaging.PackageName("abc"))


def test_release() -> None:
    _create_simple_test_package(packaging.PackageName("aaa"))
    assert packaging.is_installed(packaging.PackageName("aaa")) is True
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()

    packaging.release(packaging.PackageName("aaa"))

    assert packaging.is_installed(packaging.PackageName("aaa")) is False
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_write_file() -> None:
    manifest = _create_simple_test_package(packaging.PackageName("aaa"))

    mkp = packaging.create_mkp_object(manifest)

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
    manifest = _create_simple_test_package(packaging.PackageName("aaa"))
    packaging.uninstall(manifest)
    build_setup_search_index.assert_called_once()
    assert not packaging.is_installed(packaging.PackageName("aaa"))


def test_unpackaged_files_none() -> None:
    assert {part.ident: files for part, files in packaging.get_unpackaged_files().items()} == {
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

    assert {part.ident: files for part, files in packaging.get_unpackaged_files().items()} == {
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


def test_get_optional_manifests_none() -> None:
    assert packaging.get_optional_manifests(packaging.PackageStore()) == {}


def test_get_optional_manifests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mkp_dir = tmp_path.joinpath("optional_packages")
    mkp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "optional_packages_dir", mkp_dir)

    # Create package
    _create_simple_test_package(packaging.PackageName("optional"))
    expected_manifest = _read_manifest(packaging.PackageName("optional"))

    assert packaging.get_optional_manifests(packaging.PackageStore()) == {
        packaging.PackageID(  # pylint: disable=unhashable-member  # you're wrong, pylint.
            name=packaging.PackageName("optional"),
            version=packaging.PackageVersion("1.0.0"),
        ): (expected_manifest, True)
    }


def test_reload_gui_without_gui_files(reload_apache: Mock, build_setup_search_index: Mock) -> None:
    package = packaging.manifest_template(packaging.PackageName("ding"))
    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_not_called()


def test_reload_gui_with_gui_part(reload_apache: Mock, build_setup_search_index: Mock) -> None:
    package = packaging.manifest_template(packaging.PackageName("ding"))
    package.files = {"gui": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()


def test_reload_gui_with_web_part(reload_apache: Mock, build_setup_search_index: Mock) -> None:
    package = packaging.manifest_template(packaging.PackageName("ding"))
    package.files = {"web": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()


def _get_test_manifest(properties: Mapping) -> packaging.Manifest:
    pi = packaging.manifest_template(packaging.PackageName("test-package"))
    for k, v in properties.items():
        setattr(pi, k, v)
    return pi


@pytest.mark.parametrize(
    "manifest, site_version",
    [
        (_get_test_manifest({"version_usable_until": "1.6.0"}), "2.0.0i1"),
        (_get_test_manifest({"version_usable_until": "2.0.0i1"}), "2.0.0i2"),
        (_get_test_manifest({"version_usable_until": "2.0.0"}), "2.0.0"),
        (_get_test_manifest({"version_usable_until": "1.6.0"}), "1.6.0-2010.02.01"),
    ],
)
def test_raise_for_too_new_cmk_version_raises(
    manifest: packaging.Manifest, site_version: str
) -> None:
    with pytest.raises(packaging.PackageException):
        packaging._raise_for_too_new_cmk_version(manifest, site_version)


@pytest.mark.parametrize(
    "manifest, site_version",
    [
        (_get_test_manifest({"version_usable_until": None}), "2.0.0i1"),
        (_get_test_manifest({"version_usable_until": "2.0.0"}), "2.0.0i1"),
        (_get_test_manifest({"version_usable_until": "2.0.0"}), "2010.02.01"),
        (_get_test_manifest({"version_usable_until": ""}), "1.6.0"),
        (_get_test_manifest({"version_usable_until": "1.6.0"}), ""),
        (_get_test_manifest({"version_usable_until": "1.6.0-2010.02.01"}), "1.6.0"),
    ],
)
def test_raise_for_too_new_cmk_version_ok(manifest: packaging.Manifest, site_version: str) -> None:
    packaging._raise_for_too_new_cmk_version(manifest, site_version)
