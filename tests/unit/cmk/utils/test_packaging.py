#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import shutil
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Callable

import pytest
from pytest_mock import MockerFixture

import cmk.utils.packaging as packaging
import cmk.utils.paths
from cmk.utils.i18n import _


def _read_package_info(pacname: packaging.PackageName) -> packaging.PackageInfo:
    package_info = packaging.read_package_info(pacname)
    assert package_info is not None
    return package_info


@pytest.fixture(autouse=True)
def package_dir():
    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(str(packaging.package_dir()))


@pytest.fixture(autouse=True)
def clean_dirs():
    for part in packaging.get_package_parts():
        Path(part.path).mkdir(parents=True, exist_ok=True)

    yield

    for part in packaging.get_package_parts():
        shutil.rmtree(part.path)


@pytest.fixture(name="mkp_bytes")
def fixture_mkp_bytes(build_setup_search_index):
    # Create package information
    _create_simple_test_package("aaa")
    package_info = _read_package_info("aaa")

    # Build MKP in memory
    mkp = BytesIO()
    packaging.write_file(package_info, mkp)
    mkp.seek(0)

    # Remove files from local hierarchy
    packaging.remove(package_info)
    build_setup_search_index.assert_called_once()
    build_setup_search_index.reset_mock()
    assert packaging._package_exists("aaa") is False

    return mkp


@pytest.fixture(name="mkp_file")
def fixture_mkp_file(tmp_path, mkp_bytes):
    mkp_path = tmp_path.joinpath("aaa.mkp")
    with mkp_path.open("wb") as mkp:
        mkp.write(mkp_bytes.getvalue())

    return mkp_path


@pytest.fixture(name="build_setup_search_index")
def fixture_build_setup_search_index_background(mocker: MockerFixture) -> Callable[[], None]:
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


def test_package_parts() -> None:
    assert sorted(packaging.get_package_parts()) == sorted(
        [
            packaging.PackagePart(
                "agent_based",
                _("Agent based plugins (Checks, Inventory)"),
                str(cmk.utils.paths.local_agent_based_plugins_dir),
            ),
            packaging.PackagePart(
                "checks", _("Legacy check plugins"), str(cmk.utils.paths.local_checks_dir)
            ),
            packaging.PackagePart(
                "notifications",
                _("Notification scripts"),
                str(cmk.utils.paths.local_notifications_dir),
            ),
            packaging.PackagePart(
                "inventory", _("Legacy inventory plugins"), str(cmk.utils.paths.local_inventory_dir)
            ),
            packaging.PackagePart(
                "checkman", _("Checks' man pages"), str(cmk.utils.paths.local_check_manpages_dir)
            ),
            packaging.PackagePart("agents", _("Agents"), str(cmk.utils.paths.local_agents_dir)),
            packaging.PackagePart(
                "gui", _("GUI extensions"), str(cmk.utils.paths.local_gui_plugins_dir)
            ),
            packaging.PackagePart(
                "web", _("Legacy GUI extensions"), str(cmk.utils.paths.local_web_dir)
            ),
            packaging.PackagePart(
                "pnp-templates",
                _("PNP4Nagios templates (deprecated)"),
                str(cmk.utils.paths.local_pnp_templates_dir),
            ),
            packaging.PackagePart(
                "doc", _("Documentation files"), str(cmk.utils.paths.local_doc_dir)
            ),
            packaging.PackagePart(
                "locales", _("Localizations"), str(cmk.utils.paths.local_locale_dir)
            ),
            packaging.PackagePart("bin", _("Binaries"), str(cmk.utils.paths.local_bin_dir)),
            packaging.PackagePart("lib", _("Libraries"), str(cmk.utils.paths.local_lib_dir)),
            packaging.PackagePart("mibs", _("SNMP MIBs"), str(cmk.utils.paths.local_mib_dir)),
            packaging.PackagePart(
                "alert_handlers",
                _("Alert handlers"),
                str(cmk.utils.paths.local_share_dir.joinpath("alert_handlers")),
            ),
        ]
    )


def test_config_parts() -> None:
    assert packaging.get_config_parts() == [
        packaging.PackagePart(
            "ec_rule_packs",
            "Event Console rule packs",
            "%s/mkeventd.d/mkp/rule_packs" % cmk.utils.paths.default_config_dir,
        )
    ]


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
def test_get_permissions(path, expected) -> None:
    assert packaging._get_permissions(path) == expected


def test_package_dir() -> None:
    assert isinstance(packaging.package_dir(), Path)


def test_get_config_parts() -> None:
    assert [p.ident for p in packaging.get_config_parts()] == ["ec_rule_packs"]


def test_get_package_parts() -> None:
    assert sorted([p.ident for p in packaging.get_package_parts()]) == sorted(
        [
            "agent_based",
            "agents",
            "alert_handlers",
            "bin",
            "checkman",
            "checks",
            "doc",
            "inventory",
            "lib",
            "locales",
            "mibs",
            "notifications",
            "pnp-templates",
            "web",
            "gui",
        ]
    )


def _create_simple_test_package(pacname):
    _create_test_file(pacname)
    package_info = packaging.get_initial_package_info(pacname)

    package_info["files"] = {
        "checks": [pacname],
    }

    packaging.create(package_info)
    return packaging.read_package_info("aaa")


def _create_test_file(name):
    check_path = cmk.utils.paths.local_checks_dir.joinpath(name)
    with check_path.open("w", encoding="utf-8") as f:
        f.write("lala\n")


def test_create() -> None:
    assert packaging.installed_names() == []
    _create_simple_test_package("aaa")
    assert packaging.installed_names() == ["aaa"]


def test_create_twice() -> None:
    _create_simple_test_package("aaa")

    with pytest.raises(packaging.PackageException):
        _create_simple_test_package("aaa")


def test_read_package_info() -> None:
    _create_simple_test_package("aaa")
    package_info = _read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert packaging.package_num_files(package_info) == 1


def test_read_package_info_not_existing() -> None:
    assert packaging.read_package_info("aaa") is None


def test_edit_not_existing() -> None:
    new_package_info = packaging.get_initial_package_info("aaa")
    new_package_info["version"] = "2.0"

    with pytest.raises(packaging.PackageException):
        packaging.edit("aaa", new_package_info)


def test_edit() -> None:
    new_package_info = packaging.get_initial_package_info("aaa")
    new_package_info["version"] = "2.0"

    package_info = _create_simple_test_package("aaa")
    assert package_info["version"] == "1.0"

    packaging.edit("aaa", new_package_info)

    assert _read_package_info("aaa")["version"] == "2.0"


def test_edit_rename() -> None:
    new_package_info = packaging.get_initial_package_info("bbb")

    _create_simple_test_package("aaa")

    packaging.edit("aaa", new_package_info)

    assert _read_package_info("bbb")["name"] == "bbb"
    assert packaging.read_package_info("aaa") is None


def test_edit_rename_conflict() -> None:
    new_package_info = packaging.get_initial_package_info("bbb")
    _create_simple_test_package("aaa")
    _create_simple_test_package("bbb")

    with pytest.raises(packaging.PackageException):
        packaging.edit("aaa", new_package_info)


def test_install(mkp_bytes, build_setup_search_index) -> None:
    packaging.install(mkp_bytes)
    build_setup_search_index.assert_called_once()

    assert packaging._package_exists("aaa") is True
    package_info = _read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert package_info["files"]["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_install_by_path(mkp_file, build_setup_search_index) -> None:
    packaging.install_by_path(mkp_file)
    build_setup_search_index.assert_called_once()

    assert packaging._package_exists("aaa") is True
    package_info = _read_package_info("aaa")
    assert package_info["version"] == "1.0"
    assert package_info["files"]["checks"] == ["aaa"]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_release_not_existing() -> None:
    with pytest.raises(packaging.PackageException):
        packaging.release("abc")


def test_release() -> None:
    _create_simple_test_package("aaa")
    assert packaging._package_exists("aaa") is True
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()

    packaging.release("aaa")

    assert packaging._package_exists("aaa") is False
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_write_file() -> None:
    package_info = _create_simple_test_package("aaa")

    mkp = BytesIO()
    packaging.write_file(package_info, mkp)
    mkp.seek(0)

    with tarfile.open(fileobj=mkp, mode="r:gz") as tar:
        assert sorted(tar.getnames()) == sorted(["info", "info.json", "checks.tar"])

        info_file = tar.extractfile("info")
        assert info_file is not None
        info = ast.literal_eval(info_file.read().decode())

        info_json_file = tar.extractfile("info.json")
        assert info_json_file is not None
        info2 = json.loads(info_json_file.read())

    assert info["name"] == "aaa"
    assert info2["name"] == "aaa"


def test_remove(build_setup_search_index) -> None:
    package_info = _create_simple_test_package("aaa")
    packaging.remove(package_info)
    build_setup_search_index.assert_called_once()
    assert packaging._package_exists("aaa") is False


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
    assert packaging.get_optional_package_infos() == {}


def test_get_optional_package_infos(monkeypatch, tmp_path) -> None:
    mkp_dir = tmp_path.joinpath("optional_packages")
    mkp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "optional_packages_dir", mkp_dir)

    # Create package
    _create_simple_test_package("optional")
    package_info = _read_package_info("optional")

    # Write MKP file
    mkp_path = mkp_dir.joinpath("optional.mkp")
    with mkp_path.open("wb") as mkp:
        packaging.write_file(package_info, mkp)

    assert packaging.get_optional_package_infos() == {"optional.mkp": package_info}


def test_parse_package_info_pre_160() -> None:
    assert packaging.parse_package_info(repr({"name": "aaa"}))["version.usable_until"] is None


def test_parse_package_info() -> None:
    info_str = repr(packaging.get_initial_package_info("pkgname"))
    assert packaging.parse_package_info(info_str)["name"] == "pkgname"


def test_disable_package(mkp_file, build_setup_search_index) -> None:
    _install_and_disable_package(mkp_file, build_setup_search_index)


def test_is_disabled(mkp_file, build_setup_search_index) -> None:
    package_file_name = _install_and_disable_package(mkp_file, build_setup_search_index)
    assert packaging.is_disabled(package_file_name)

    packaging.enable(package_file_name)
    build_setup_search_index.assert_called_once()
    assert not packaging.is_disabled(package_file_name)


def _install_and_disable_package(mkp_file, build_setup_search_index):
    packaging.install_by_path(mkp_file)
    build_setup_search_index.assert_called_once()
    build_setup_search_index.reset_mock()
    assert packaging._package_exists("aaa") is True

    package_info = packaging.read_package_info("aaa")
    assert package_info is not None
    package_file_name = packaging.format_file_name(name="aaa", version=package_info["version"])

    packaging.disable("aaa", package_info)
    build_setup_search_index.assert_called_once()
    build_setup_search_index.reset_mock()
    assert packaging._package_exists("aaa") is False
    assert cmk.utils.paths.disabled_packages_dir.joinpath(package_file_name).exists()
    assert not cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()
    return package_file_name


def test_enable_disabled_package(mkp_file, build_setup_search_index) -> None:
    package_file_name = _install_and_disable_package(mkp_file, build_setup_search_index)

    packaging.enable(package_file_name)
    build_setup_search_index.assert_called_once()
    assert packaging._package_exists("aaa") is True
    assert not cmk.utils.paths.disabled_packages_dir.joinpath(package_file_name).exists()
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_remove_disabled_package(mkp_file, build_setup_search_index) -> None:
    package_file_name = _install_and_disable_package(mkp_file, build_setup_search_index)

    packaging.remove_disabled(package_file_name)
    build_setup_search_index.assert_not_called()
    assert packaging._package_exists("aaa") is False
    assert not cmk.utils.paths.disabled_packages_dir.joinpath(package_file_name).exists()


def test_reload_gui_without_gui_files(reload_apache, build_setup_search_index) -> None:
    package = packaging.get_initial_package_info("ding")
    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_not_called()


def test_reload_gui_with_gui_part(reload_apache, build_setup_search_index) -> None:
    package = packaging.get_initial_package_info("ding")
    package["files"] = {"gui": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()


def test_reload_gui_with_web_part(reload_apache, build_setup_search_index) -> None:
    package = packaging.get_initial_package_info("ding")
    package["files"] = {"web": ["a"]}

    packaging._execute_post_package_change_actions(package)
    build_setup_search_index.assert_called_once()
    reload_apache.assert_called_once()
