#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import tarfile
from io import BytesIO
from pathlib import Path
from typing import NoReturn

import pytest

from cmk.mkp_tool import _mkp as mkp
from cmk.mkp_tool import (
    create,
    edit,
    get_stored_manifests,
    Installer,
    Manifest,
    PackageError,
    PackageName,
    PackagePart,
    PackageStore,
    PackageVersion,
    PathConfig,
    release,
)
from cmk.mkp_tool._unsorted import (
    _install,
    _raise_for_too_new_cmk_version,
    _raise_for_too_old_cmk_version,
    _uninstall,
    get_unpackaged_files,
    make_post_package_change_actions,
    StoredManifests,
)


def test_raise_for_too_old_cmk_version_raises() -> None:
    with pytest.raises(PackageError):
        _raise_for_too_old_cmk_version(float, "1.4", "1.3")


def test_raise_for_too_old_cmk_version_ok() -> None:
    _raise_for_too_old_cmk_version(float, "1.4", "1.4")


def test_raise_for_too_new_cmk_version_raises() -> None:
    with pytest.raises(PackageError):
        _raise_for_too_new_cmk_version(float, "1.4", "1.4")


def test_raise_for_too_new_cmk_version_ok() -> None:
    _raise_for_too_new_cmk_version(float, "1.4", "1.3")


def _assert_not_called() -> NoReturn:
    assert False


def test_reload_gui_without_gui_files() -> None:
    package = mkp.manifest_template(
        PackageName("ding"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
    )

    make_post_package_change_actions(((PackagePart.GUI,), _assert_not_called), on_any_change=())(
        [package]
    )


def test_reload_gui_with_gui_part() -> None:
    package = mkp.manifest_template(
        name=PackageName("ding"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
        files={PackagePart.GUI: [Path("a")]},
    )

    with pytest.raises(AssertionError):
        make_post_package_change_actions(
            ((PackagePart.GUI,), _assert_not_called), on_any_change=()
        )([package])


def test_reload_gui_on_unrelated_change() -> None:
    package = mkp.manifest_template(
        name=PackageName("ding"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
        files={PackagePart.MIBS: [Path("a")]},  # arbitrary non-gui file.
    )

    with pytest.raises(AssertionError):
        make_post_package_change_actions(on_any_change=(_assert_not_called,))([package])


def _create_simple_test_package(
    installer: Installer, pacname: PackageName, path_config: PathConfig, package_store: PackageStore
) -> Manifest:
    _create_test_file(str(pacname), path_config)

    create(
        installer,
        mkp.manifest_template(
            name=pacname,
            version_packaged="3.14.0p15",
            version_required="3.14.0p1",
            files={PackagePart.AGENT_BASED: [Path(pacname)]},
        ),
        path_config,
        package_store,
        lambda s, b: Path(s).write_bytes(b),
        version_packaged="3.14.0p15",
    )
    manifest = installer.get_installed_manifest(pacname)
    assert manifest
    return manifest


def _create_test_file(name: str, path_config: PathConfig) -> None:
    path_config.agent_based_plugins_dir.joinpath(name).write_text("lala\n")


def test_get_stored_manifests(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    # Create package
    expected_manifest = _create_simple_test_package(
        installer, PackageName("optional"), path_config, package_store
    )

    assert get_stored_manifests(package_store) == StoredManifests(
        local=[expected_manifest], shipped=[]
    )


def test_create(installer: Installer, path_config: PathConfig, package_store: PackageStore) -> None:
    name = PackageName("aaa")
    assert not installer.is_installed(name)
    _create_simple_test_package(installer, name, path_config, package_store)
    assert installer.is_installed(name)


def test_create_twice(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    _create_simple_test_package(installer, PackageName("aaa"), path_config, package_store)

    with pytest.raises(PackageError):
        _create_simple_test_package(installer, PackageName("aaa"), path_config, package_store)


def test_edit_not_existing(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    new_manifest = mkp.manifest_template(
        name=PackageName("aaa"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
        version=PackageVersion("2.0.0"),
    )

    with pytest.raises(PackageError):
        edit(
            installer,
            PackageName("aaa"),
            new_manifest,
            path_config,
            package_store,
            lambda s, b: Path(s).write_bytes(b),
            version_packaged="3.14.0p15",
        )


def _get_asserted_manifest(installer: Installer, name: PackageName) -> Manifest:
    m = installer.get_installed_manifest(name)
    assert m
    return m


def test_edit(installer: Installer, path_config: PathConfig, package_store: PackageStore) -> None:
    new_manifest = mkp.manifest_template(
        name=PackageName("aaa"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
        version=PackageVersion("2.0.0"),
    )

    manifest = _create_simple_test_package(
        installer, PackageName("aaa"), path_config, package_store
    )
    assert manifest.version == PackageVersion("1.0.0")

    edit(
        installer,
        PackageName("aaa"),
        new_manifest,
        path_config,
        package_store,
        lambda s, b: Path(s).write_bytes(b),
        version_packaged="3.14.0p15",
    )

    assert _get_asserted_manifest(installer, PackageName("aaa")).version == PackageVersion("2.0.0")


def test_edit_rename(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    new_manifest = mkp.manifest_template(
        PackageName("bbb"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
    )

    _create_simple_test_package(installer, PackageName("aaa"), path_config, package_store)

    edit(
        installer,
        PackageName("aaa"),
        new_manifest,
        path_config,
        package_store,
        lambda s, b: Path(s).write_bytes(b),
        version_packaged="3.14.0p15",
    )

    assert _get_asserted_manifest(installer, PackageName("bbb")).name == PackageName("bbb")
    assert installer.get_installed_manifest(PackageName("aaa")) is None


def test_edit_rename_conflict(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    new_manifest = mkp.manifest_template(
        PackageName("bbb"),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
    )
    _create_simple_test_package(installer, PackageName("aaa"), path_config, package_store)
    _create_simple_test_package(installer, PackageName("bbb"), path_config, package_store)

    with pytest.raises(PackageError):
        edit(
            installer,
            PackageName("aaa"),
            new_manifest,
            path_config,
            package_store,
            lambda s, b: Path(s).write_bytes(b),
            version_packaged="3.14.0p15",
        )


def _make_mkp_bytes(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> bytes:
    # Create package information
    manifest = _create_simple_test_package(
        installer, PackageName("aaa"), path_config, package_store
    )

    # Build MKP in memory
    mkp_bytes = mkp.create_mkp(manifest, path_config.get_path, "3.14.0p15")

    # Remove files from local hierarchy
    _uninstall(installer, path_config, {}, manifest)
    assert installer.is_installed(PackageName("aaa")) is False

    return mkp_bytes


def test_install(
    installer: Installer,
    package_store: PackageStore,
    path_config: PathConfig,
) -> None:
    _install(
        installer,
        _make_mkp_bytes(installer, path_config, package_store),
        path_config,
        {},
        site_version="3.14",
        version_check=True,
        parse_version=float,
    )
    assert installer.is_installed(PackageName("aaa")) is True
    manifest = _get_asserted_manifest(installer, PackageName("aaa"))
    assert manifest.version == "1.0.0"
    assert manifest.files[PackagePart.AGENT_BASED] == [Path("aaa")]
    assert path_config.agent_based_plugins_dir.joinpath("aaa").exists()


def test_release_not_existing(installer: Installer) -> None:
    with pytest.raises(PackageError):
        release(installer, PackageName("abc"), {})


def test_release(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    _create_simple_test_package(installer, PackageName("aaa"), path_config, package_store)
    assert installer.is_installed(PackageName("aaa"))
    assert path_config.agent_based_plugins_dir.joinpath("aaa").exists()

    release(installer, PackageName("aaa"), {})

    assert not installer.is_installed(PackageName("aaa"))
    assert path_config.agent_based_plugins_dir.joinpath("aaa").exists()


def test_write_file(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    manifest = _create_simple_test_package(
        installer, PackageName("aaa"), path_config, package_store
    )

    mkp_bytes = mkp.create_mkp(manifest, path_config.get_path, "3.14.0p15")

    with tarfile.open(fileobj=BytesIO(mkp_bytes), mode="r:gz") as tar:
        assert sorted(tar.getnames()) == sorted(["info", "info.json", "agent_based.tar"])

        info_file = tar.extractfile("info")
        assert info_file is not None
        info = ast.literal_eval(info_file.read().decode())

        info_json_file = tar.extractfile("info.json")
        assert info_json_file is not None
        info2 = json.loads(info_json_file.read())

    assert info["name"] == "aaa"
    assert info2["name"] == "aaa"


def test_uninstall(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    manifest = _create_simple_test_package(
        installer, PackageName("aaa"), path_config, package_store
    )
    _uninstall(installer, path_config, {}, manifest)
    assert not installer.is_installed(PackageName("aaa"))


def test_unpackaged_files_none(installer: Installer, path_config: PathConfig) -> None:
    assert {
        part.ident: files for part, files in get_unpackaged_files(installer, path_config).items()
    } == {
        "cmk_plugins": [],
        "cmk_addons_plugins": [],
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


def test_unpackaged_files(installer: Installer, path_config: PathConfig) -> None:
    _create_test_file("abc", path_config)

    p = path_config.doc_dir.joinpath("docxx")
    with p.open("w", encoding="utf-8") as f:
        f.write("lala\n")

    p = path_config.agent_based_plugins_dir.joinpath("dada")
    with p.open("w", encoding="utf-8") as f:
        f.write("huhu\n")

    assert get_unpackaged_files(installer, path_config) == {
        PackagePart.CMK_PLUGINS: [],
        PackagePart.CMK_ADDONS_PLUGINS: [],
        PackagePart.AGENT_BASED: [Path("abc"), Path("dada")],
        PackagePart.AGENTS: [],
        PackagePart.ALERT_HANDLERS: [],
        PackagePart.BIN: [],
        PackagePart.CHECKMAN: [],
        PackagePart.CHECKS: [],
        PackagePart.DOC: [Path("docxx")],
        PackagePart.EC_RULE_PACKS: [],
        PackagePart.HASI: [],
        PackagePart.LIB: [],
        PackagePart.LOCALES: [],
        PackagePart.MIBS: [],
        PackagePart.NOTIFICATIONS: [],
        PackagePart.PNP_TEMPLATES: [],
        PackagePart.WEB: [],
        PackagePart.GUI: [],
    }


def test_get_optional_manifests_none(package_store: PackageStore) -> None:
    stored = get_stored_manifests(package_store)
    assert not stored.local
    assert not stored.shipped
