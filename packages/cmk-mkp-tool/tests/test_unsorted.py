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
from unittest.mock import patch

import pytest

from cmk.mkp_tool import _mkp as mkp
from cmk.mkp_tool import (
    create,
    edit,
    format_file_name,
    get_classified_manifests,
    get_stored_manifests,
    id_to_mkp,
    Installer,
    Manifest,
    PackageError,
    PackageID,
    PackageName,
    PackagePart,
    PackageStore,
    PackageVersion,
    PathConfig,
    release,
    VersionMismatch,
    VersionTooHigh,
    VersionTooLow,
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


def test_create_package_with_folder_fails(
    installer: Installer, path_config: PathConfig, package_store: PackageStore
) -> None:
    folder = "invalid_mkp"
    path_config.agent_based_plugins_dir.joinpath(folder).mkdir()

    with pytest.raises(PackageError, match="is not a file"):
        create(
            installer,
            mkp.manifest_template(
                name=PackageName("my_mkp"),
                version_packaged="3.14.0p15",
                version_required="3.14.0p1",
                files={PackagePart.AGENT_BASED: [Path(folder)]},
            ),
            path_config,
            package_store,
            persisting_function=lambda _a, _b: 0,
            version_packaged="3.14.0p15",
        )


def test_remove(installer: Installer, path_config: PathConfig, package_store: PackageStore) -> None:
    name = PackageName("foo")
    installed_ver = PackageVersion("1.0.0")
    missing_ver = PackageVersion("1.3.3.7")
    _create_simple_test_package(installer, name, path_config, package_store)

    with pytest.raises(PackageError, match="Package foo 1.3.3.7 not found"):
        pkg_id = PackageID(name=name, version=missing_ver)
        package_store.remove(pkg_id)

    with patch("cmk.mkp_tool._unsorted.Path.unlink") as unlink:
        pkg_id = PackageID(name=name, version=installed_ver)
        package_store.remove(pkg_id)
        unlink.assert_called_once()


def _mkp_bytes(name: str, version: str = "1.0.0") -> bytes:
    """Build the smallest MKP that extract_manifest accepts."""
    manifest = mkp.manifest_template(
        name=PackageName(name),
        version_packaged="3.14.0p15",
        version_required="3.14.0p1",
        version=PackageVersion(version),
    )
    content = manifest.file_content().encode()
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("info")
        info.size = len(content)
        tar.addfile(info, BytesIO(content))
    return buffer.getvalue()


def _package_id(name: str, version: str = "1.0.0") -> PackageID:
    return PackageID(name=PackageName(name), version=PackageVersion(version))


def test_format_file_name() -> None:
    assert format_file_name(_package_id("cool_package", "1.2.3")) == "cool_package-1.2.3.mkp"


class TestVersionMismatch:
    def test_is_a_package_error(self) -> None:
        assert isinstance(VersionMismatch("2.4.0", "too bad"), PackageError)

    def test_requirement_is_kept(self) -> None:
        assert VersionMismatch("2.4.0", "too bad").requirement == "2.4.0"

    def test_subclasses_carry_the_requirement(self) -> None:
        assert VersionTooLow("2.4.0", "too low").requirement == "2.4.0"
        assert VersionTooHigh("2.6.0", "too high").requirement == "2.6.0"

    def test_subclasses_are_version_mismatches(self) -> None:
        assert isinstance(VersionTooLow("2.4.0", "too low"), VersionMismatch)
        assert isinstance(VersionTooHigh("2.6.0", "too high"), VersionMismatch)

    def test_too_low_and_too_high_are_distinguishable(self) -> None:
        assert not isinstance(VersionTooLow("2.4.0", "too low"), VersionTooHigh)


class TestPackageStore:
    def test_listing_without_directories(self, package_store: PackageStore) -> None:
        # the directories do not exist yet - that must not raise
        assert package_store.list_local_packages() == []
        assert package_store.list_shipped_packages() == []
        assert package_store.get_enabled_manifests() == {}

    def test_store_writes_a_local_package(self, package_store: PackageStore) -> None:
        manifest = package_store.store(_mkp_bytes("cool_package"), lambda p, c: p.write_bytes(c))

        assert str(manifest.name) == "cool_package"
        assert package_store.list_local_packages() == [
            package_store.local_packages / "cool_package-1.0.0.mkp"
        ]

    def test_store_twice_is_an_error(self, package_store: PackageStore) -> None:
        content = _mkp_bytes("cool_package")
        package_store.store(content, lambda p, c: p.write_bytes(c))

        with pytest.raises(PackageError, match="exists on the site"):
            package_store.store(content, lambda p, c: p.write_bytes(c))

    def test_store_twice_with_overwrite(self, package_store: PackageStore) -> None:
        content = _mkp_bytes("cool_package")
        package_store.store(content, lambda p, c: p.write_bytes(c))

        package_store.store(content, lambda p, c: p.write_bytes(c), overwrite=True)

    def test_store_refuses_to_shadow_a_shipped_package(self, package_store: PackageStore) -> None:
        package_store.shipped_packages.mkdir(parents=True)
        (package_store.shipped_packages / "cool_package-1.0.0.mkp").write_bytes(b"shipped")

        # even with overwrite: a shipped package must never be shadowed
        with pytest.raises(PackageError, match="exists on the site"):
            package_store.store(
                _mkp_bytes("cool_package"), lambda p, c: p.write_bytes(c), overwrite=True
            )

    def test_read_bytes_of_unknown_package(self, package_store: PackageStore) -> None:
        with pytest.raises(PackageError, match="No such package: cool_package 1.0.0"):
            _ = package_store.read_bytes(_package_id("cool_package"))

    def test_read_bytes_finds_shipped_package(self, package_store: PackageStore) -> None:
        package_store.shipped_packages.mkdir(parents=True)
        (package_store.shipped_packages / "cool_package-1.0.0.mkp").write_bytes(b"shipped")

        assert package_store.read_bytes(_package_id("cool_package")) == b"shipped"

    def test_read_bytes_prefers_enabled_over_shipped(self, package_store: PackageStore) -> None:
        for directory, content in (
            (package_store.shipped_packages, b"shipped"),
            (package_store.enabled_packages, b"enabled"),
        ):
            directory.mkdir(parents=True)
            (directory / "cool_package-1.0.0.mkp").write_bytes(content)

        assert package_store.read_bytes(_package_id("cool_package")) == b"enabled"

    def test_read_bytes_prefers_local_over_everything(self, package_store: PackageStore) -> None:
        for directory, content in (
            (package_store.shipped_packages, b"shipped"),
            (package_store.enabled_packages, b"enabled"),
            (package_store.local_packages, b"local"),
        ):
            directory.mkdir(parents=True)
            (directory / "cool_package-1.0.0.mkp").write_bytes(content)

        assert package_store.read_bytes(_package_id("cool_package")) == b"local"

    def test_mark_as_enabled(self, package_store: PackageStore) -> None:
        content = _mkp_bytes("cool_package")
        package_store.store(content, lambda p, c: p.write_bytes(c))

        package_store.mark_as_enabled(_package_id("cool_package"))

        enabled = package_store.enabled_packages / "cool_package-1.0.0.mkp"
        assert enabled.read_bytes() == content
        # the local copy is kept, so it still syncs to remote sites
        assert (package_store.local_packages / "cool_package-1.0.0.mkp").exists()

    def test_mark_as_enabled_unknown_package(self, package_store: PackageStore) -> None:
        with pytest.raises(PackageError, match="No such package"):
            package_store.mark_as_enabled(_package_id("cool_package"))

    def test_remove_enabled_mark(self, package_store: PackageStore) -> None:
        package_store.store(_mkp_bytes("cool_package"), lambda p, c: p.write_bytes(c))
        package_store.mark_as_enabled(_package_id("cool_package"))

        package_store.remove_enabled_mark(_package_id("cool_package"))

        assert not (package_store.enabled_packages / "cool_package-1.0.0.mkp").exists()

    def test_remove_enabled_mark_is_forgiving(self, package_store: PackageStore) -> None:
        # a messed up state must not crash
        package_store.remove_enabled_mark(_package_id("cool_package"))

    def test_get_enabled_manifests(self, package_store: PackageStore) -> None:
        for name in ("package_a", "package_b"):
            package_store.store(_mkp_bytes(name), lambda p, c: p.write_bytes(c))
            package_store.mark_as_enabled(_package_id(name))

        enabled = package_store.get_enabled_manifests()

        assert {str(pkg_id.name) for pkg_id in enabled} == {"package_a", "package_b"}
        assert enabled[_package_id("package_a")].name == PackageName("package_a")

    def test_get_enabled_manifests_ignores_broken_files(self, package_store: PackageStore) -> None:
        package_store.store(_mkp_bytes("cool_package"), lambda p, c: p.write_bytes(c))
        package_store.mark_as_enabled(_package_id("cool_package"))
        (package_store.enabled_packages / "garbage.mkp").write_bytes(b"not an MKP")

        assert list(package_store.get_enabled_manifests()) == [_package_id("cool_package")]


class TestClassifiedManifests:
    def test_enabled_is_installed_plus_inactive(
        self, installer: Installer, package_store: PackageStore, path_config: PathConfig
    ) -> None:
        _create_simple_test_package(installer, PackageName("installed"), path_config, package_store)
        package_store.store(_mkp_bytes("inactive"), lambda p, c: p.write_bytes(c))
        package_store.mark_as_enabled(_package_id("inactive"))

        classified = get_classified_manifests(package_store, installer)

        assert [str(m.name) for m in classified.installed] == ["installed"]
        assert [str(m.name) for m in classified.inactive] == ["inactive"]
        assert [str(m.name) for m in classified.enabled] == ["installed", "inactive"]

    def test_installed_package_is_not_also_inactive(
        self, installer: Installer, package_store: PackageStore, path_config: PathConfig
    ) -> None:
        manifest = _create_simple_test_package(
            installer, PackageName("installed"), path_config, package_store
        )
        package_store.mark_as_enabled(manifest.id)

        classified = get_classified_manifests(package_store, installer)

        assert classified.inactive == []
        assert [str(m.name) for m in classified.enabled] == ["installed"]


class TestIdToMkp:
    def test_no_files(self, installer: Installer) -> None:
        assert id_to_mkp(installer, [], PackagePart.EC_RULE_PACKS) == {}

    def test_maps_stem_to_package_name(self, installer: Installer) -> None:
        installer.add_installed_manifest(
            mkp.manifest_template(
                name=PackageName("cool_package"),
                version_packaged="3.14.0p15",
                version_required="3.14.0p1",
                files={PackagePart.EC_RULE_PACKS: [Path("my_rule_pack.mk")]},
            )
        )

        assert id_to_mkp(installer, [Path("my_rule_pack.mk")], PackagePart.EC_RULE_PACKS) == {
            "my_rule_pack": PackageName("cool_package")
        }

    def test_unpackaged_file_is_omitted(self, installer: Installer) -> None:
        assert id_to_mkp(installer, [Path("not_in_a_package.mk")], PackagePart.EC_RULE_PACKS) == {}
