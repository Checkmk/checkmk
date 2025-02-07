#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import shutil
import tarfile
from collections.abc import Iterable, Iterator, Mapping
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import cmk.utils.packaging as packaging
import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.ec.export as ec

_PATH_CONFIG = packaging.PathConfig(
    local_root=cmk.utils.paths.local_root,
    mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
    agent_based_plugins_dir=cmk.utils.paths.local_agent_based_plugins_dir,
    checks_dir=cmk.utils.paths.local_checks_dir,
    inventory_dir=cmk.utils.paths.local_inventory_dir,
    check_manpages_dir=cmk.utils.paths.local_check_manpages_dir,
    agents_dir=cmk.utils.paths.local_agents_dir,
    notifications_dir=cmk.utils.paths.local_notifications_dir,
    gui_plugins_dir=cmk.utils.paths.local_gui_plugins_dir,
    web_dir=cmk.utils.paths.local_web_dir,
    pnp_templates_dir=cmk.utils.paths.local_pnp_templates_dir,
    doc_dir=cmk.utils.paths.local_doc_dir,
    locale_dir=cmk.utils.paths.local_locale_dir,
    bin_dir=cmk.utils.paths.local_bin_dir,
    lib_dir=cmk.utils.paths.local_lib_dir,
    mib_dir=cmk.utils.paths.local_mib_dir,
    alert_handlers_dir=cmk.utils.paths.local_alert_handlers_dir,
)


@pytest.fixture(name="installer", scope="function")
def _get_installer() -> Iterator[packaging.Installer]:
    cmk.utils.paths.installed_packages_dir.mkdir(parents=True, exist_ok=True)
    yield packaging.Installer(cmk.utils.paths.installed_packages_dir)
    shutil.rmtree(cmk.utils.paths.installed_packages_dir)


def _read_manifest(
    installer: packaging.Installer, pacname: packaging.PackageName
) -> packaging.Manifest:
    manifest = installer.get_installed_manifest(pacname)
    assert manifest is not None
    return manifest


@pytest.fixture(autouse=True)
def clean_dirs() -> Iterable[None]:
    paths = [_PATH_CONFIG.get_path(p) for p in packaging.PackagePart] + [
        cmk.utils.paths.local_optional_packages_dir,
        cmk.utils.paths.local_enabled_packages_dir,
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    yield

    for path in paths:
        try:
            shutil.rmtree(str(path))
        except FileNotFoundError:
            pass  # some dirs are nested.


@pytest.fixture(name="mkp_bytes")
def fixture_mkp_bytes(installer: packaging.Installer) -> bytes:
    # Create package information
    manifest = _create_simple_test_package(installer, packaging.PackageName("aaa"))

    # Build MKP in memory
    mkp = packaging.create_mkp_object(manifest, _PATH_CONFIG)

    # Remove files from local hierarchy
    packaging.uninstall(installer, _PATH_CONFIG, manifest)
    assert installer.is_installed(packaging.PackageName("aaa")) is False

    return mkp


@pytest.fixture(name="reload_apache")
def fixture_reload_apache(mocker: MockerFixture) -> Mock:
    return mocker.patch(
        "cmk.utils.packaging._reload_apache",
        side_effect=lambda: None,
    )


@pytest.mark.parametrize(
    "part,file,expected",
    [
        (packaging.PackagePart.AGENT_BASED, Path("some_check.py"), 0o644),
        (packaging.PackagePart.BIN, Path("some_binary"), 0o755),
        (packaging.PackagePart.LIB, Path("nagios/plugins/check_foobar"), 0o755),
        (packaging.PackagePart.LIB, Path("something/else/check_foobar"), 0o644),
    ],
)
def test_get_permissions(part: packaging.PackagePart, file: Path, expected: int) -> None:
    assert packaging._get_permissions(part, file) == expected


def _create_simple_test_package(
    installer: packaging.Installer, pacname: packaging.PackageName
) -> packaging.Manifest:
    _create_test_file(pacname)
    manifest = packaging.manifest_template(
        name=pacname,
        version_packaged=cmk_version.__version__,
        files={
            packaging.PackagePart.CHECKS: [Path(pacname)],
        },
    )

    packaging.create(installer, manifest, _PATH_CONFIG)
    return _read_manifest(installer, pacname)


def _create_test_file(name):
    check_path = cmk.utils.paths.local_checks_dir.joinpath(name)
    with check_path.open("w", encoding="utf-8") as f:
        f.write("lala\n")


def test_create(installer: packaging.Installer) -> None:
    name = packaging.PackageName("aaa")
    assert not installer.is_installed(name)
    _create_simple_test_package(installer, name)
    assert installer.is_installed(name)


def test_create_twice(installer: packaging.Installer) -> None:
    _create_simple_test_package(installer, packaging.PackageName("aaa"))

    with pytest.raises(packaging.PackageException):
        _create_simple_test_package(installer, packaging.PackageName("aaa"))


def test_edit_not_existing(installer: packaging.Installer) -> None:
    new_manifest = packaging.manifest_template(
        name=packaging.PackageName("aaa"),
        version_packaged=cmk_version.__version__,
        version=packaging.PackageVersion("2.0.0"),
    )

    with pytest.raises(packaging.PackageException):
        packaging.edit(installer, packaging.PackageName("aaa"), new_manifest, _PATH_CONFIG)


def test_edit(installer: packaging.Installer) -> None:
    new_manifest = packaging.manifest_template(
        name=packaging.PackageName("aaa"),
        version_packaged=cmk_version.__version__,
        version=packaging.PackageVersion("2.0.0"),
    )

    manifest = _create_simple_test_package(installer, packaging.PackageName("aaa"))
    assert manifest.version == packaging.PackageVersion("1.0.0")

    packaging.edit(installer, packaging.PackageName("aaa"), new_manifest, _PATH_CONFIG)

    assert _read_manifest(
        installer, packaging.PackageName("aaa")
    ).version == packaging.PackageVersion("2.0.0")


def test_edit_rename(installer: packaging.Installer) -> None:
    new_manifest = packaging.manifest_template(
        packaging.PackageName("bbb"),
        version_packaged=cmk_version.__version__,
    )

    _create_simple_test_package(installer, packaging.PackageName("aaa"))

    packaging.edit(installer, packaging.PackageName("aaa"), new_manifest, _PATH_CONFIG)

    assert _read_manifest(installer, packaging.PackageName("bbb")).name == packaging.PackageName(
        "bbb"
    )
    assert installer.get_installed_manifest(packaging.PackageName("aaa")) is None


def test_edit_rename_conflict(installer: packaging.Installer) -> None:
    new_manifest = packaging.manifest_template(
        packaging.PackageName("bbb"),
        version_packaged=cmk_version.__version__,
    )
    _create_simple_test_package(installer, packaging.PackageName("aaa"))
    _create_simple_test_package(installer, packaging.PackageName("bbb"))

    with pytest.raises(packaging.PackageException):
        packaging.edit(installer, packaging.PackageName("aaa"), new_manifest, _PATH_CONFIG)


def test_install(mkp_bytes: bytes, installer: packaging.Installer) -> None:
    packaging._install(
        installer,
        mkp_bytes,
        _PATH_CONFIG,
        allow_outdated=False,
        post_package_change_actions=True,
    )
    assert installer.is_installed(packaging.PackageName("aaa")) is True
    manifest = _read_manifest(installer, packaging.PackageName("aaa"))
    assert manifest.version == "1.0.0"
    assert manifest.files[packaging.PackagePart.CHECKS] == [Path("aaa")]
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_release_not_existing(installer: packaging.Installer) -> None:
    with pytest.raises(packaging.PackageException):
        packaging.release(installer, packaging.PackageName("abc"))


def test_release(installer: packaging.Installer) -> None:
    _create_simple_test_package(installer, packaging.PackageName("aaa"))
    assert installer.is_installed(packaging.PackageName("aaa")) is True
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()

    packaging.release(installer, packaging.PackageName("aaa"))

    assert installer.is_installed(packaging.PackageName("aaa")) is False
    assert cmk.utils.paths.local_checks_dir.joinpath("aaa").exists()


def test_write_file(installer: packaging.Installer) -> None:
    manifest = _create_simple_test_package(installer, packaging.PackageName("aaa"))

    mkp = packaging.create_mkp_object(manifest, _PATH_CONFIG)

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


def test_uninstall(installer: packaging.Installer) -> None:
    manifest = _create_simple_test_package(installer, packaging.PackageName("aaa"))
    packaging.uninstall(installer, _PATH_CONFIG, manifest)
    assert not installer.is_installed(packaging.PackageName("aaa"))


def test_unpackaged_files_none(installer: packaging.Installer) -> None:
    assert {
        part.ident: files
        for part, files in packaging.get_unpackaged_files(installer, _PATH_CONFIG).items()
    } == {
        "agent_based": [],
        "agents": [],
        "alert_handlers": [],
        "bin": [],
        "checkman": [],
        "checks": [],
        "cmk_addons_plugins": [],
        "cmk_plugins": [],
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


def test_unpackaged_files(installer: packaging.Installer) -> None:
    _create_test_file("abc")

    p = cmk.utils.paths.local_doc_dir.joinpath("docxx")
    with p.open("w", encoding="utf-8") as f:
        f.write("lala\n")

    p = cmk.utils.paths.local_agent_based_plugins_dir.joinpath("dada")
    with p.open("w", encoding="utf-8") as f:
        f.write("huhu\n")

    assert {
        part.ident: files
        for part, files in packaging.get_unpackaged_files(installer, _PATH_CONFIG).items()
    } == {
        packaging.PackagePart.AGENT_BASED: [Path("dada")],
        packaging.PackagePart.AGENTS: [],
        packaging.PackagePart.ALERT_HANDLERS: [],
        packaging.PackagePart.BIN: [],
        packaging.PackagePart.CHECKMAN: [],
        packaging.PackagePart.CHECKS: [Path("abc")],
        packaging.PackagePart.DOC: [Path("docxx")],
        packaging.PackagePart.EC_RULE_PACKS: [],
        packaging.PackagePart.HASI: [],
        packaging.PackagePart.LIB: [],
        packaging.PackagePart.LOCALES: [],
        packaging.PackagePart.MIBS: [],
        packaging.PackagePart.NOTIFICATIONS: [],
        packaging.PackagePart.PNP_TEMPLATES: [],
        packaging.PackagePart.WEB: [],
        packaging.PackagePart.GUI: [],
        packaging.PackagePart.CMK_PLUGINS: [],
        packaging.PackagePart.CMK_ADDONS_PLUGINS: [],
    }


def test_get_optional_manifests_none() -> None:
    stored = packaging.get_stored_manifests(packaging.PackageStore())
    assert not stored.local
    assert not stored.shipped


def test_get_stored_manifests(
    monkeypatch: pytest.MonkeyPatch, installer: packaging.Installer, tmp_path: Path
) -> None:
    mkp_dir = tmp_path.joinpath("optional_packages")
    mkp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "optional_packages_dir", mkp_dir)

    # Create package
    _create_simple_test_package(installer, packaging.PackageName("optional"))
    expected_manifest = _read_manifest(installer, packaging.PackageName("optional"))

    assert packaging.get_stored_manifests(packaging.PackageStore()) == packaging.StoredManifests(
        local=[expected_manifest],
        shipped=[],
    )


def test_reload_gui_without_gui_files(reload_apache: Mock) -> None:
    package = packaging.manifest_template(
        packaging.PackageName("ding"),
        version_packaged=cmk_version.__version__,
    )
    packaging._execute_post_package_change_actions(package)
    reload_apache.assert_not_called()


def test_reload_gui_with_gui_part(reload_apache: Mock) -> None:
    package = packaging.manifest_template(
        name=packaging.PackageName("ding"),
        version_packaged=cmk_version.__version__,
        files={packaging.PackagePart.GUI: [Path("a")]},
    )

    packaging._execute_post_package_change_actions(package)
    reload_apache.assert_called_once()


def test_reload_gui_with_web_part(reload_apache: Mock) -> None:
    package = packaging.manifest_template(
        name=packaging.PackageName("ding"),
        version_packaged=cmk_version.__version__,
        files={packaging.PackagePart.WEB: [Path("a")]},
    )

    packaging._execute_post_package_change_actions(package)
    reload_apache.assert_called_once()


def _get_test_manifest(properties: Mapping) -> packaging.Manifest:
    pi = packaging.manifest_template(
        packaging.PackageName("test-package"),
        version_packaged=cmk_version.__version__,
    )
    for k, v in properties.items():
        setattr(pi, k, v)
    return pi


@pytest.mark.parametrize(
    "until_version, site_version",
    [
        ("1.6.0", "2.0.0i1"),
        ("2.0.0i1", "2.0.0i2"),
        ("2.0.0", "2.0.0"),
        ("1.6.0", "1.6.0-2010.02.01"),
    ],
)
def test_raise_for_too_new_cmk_version_raises(until_version: str | None, site_version: str) -> None:
    with pytest.raises(packaging.PackageException):
        packaging._raise_for_too_new_cmk_version(until_version, site_version)


@pytest.mark.parametrize(
    "until_version, site_version",
    [
        (None, "2.0.0i1"),
        ("2.0.0", "2.0.0i1"),
        ("2.0.0", "2010.02.01"),
        ("", "1.6.0"),
        ("1.6.0", ""),
        ("1.6.0-2010.02.01", "1.6.0"),
    ],
)
def test_raise_for_too_new_cmk_version_ok(until_version: str | None, site_version: str) -> None:
    packaging._raise_for_too_new_cmk_version(until_version, site_version)


def _setup_local_files_structure() -> None:
    """Let's hope this gets easier during the upcomming changes."""
    for part in packaging.PackagePart:
        part_path = _PATH_CONFIG.get_path(part)
        subdir = part_path / "subdir"
        subdir.mkdir(parents=True)
        (part_path / f"regular_file_of_{part.ident}.py").touch()
        (part_path / f".hidden_file_of_{part.ident}.py").touch()
        (part_path / f"editor_file_of_{part.ident}.py~").touch()
        (part_path / f"compiled_file_of_{part.ident}.pyc").touch()
        (subdir / f"subdir_file_of_{part.ident}.py").touch()

    other_file = cmk.utils.paths.local_root / "some" / "other" / "file.sh"
    other_file.parent.mkdir(parents=True)
    other_file.touch()


def test_get_local_files_by_part() -> None:
    _setup_local_files_structure()
    expected: dict[packaging.PackagePart | None, set[Path]] = {
        **{
            p: {Path(f"regular_file_of_{p.ident}.py"), Path(f"subdir/subdir_file_of_{p.ident}.py")}
            for p in packaging.PackagePart
            if p is not packaging.PackagePart.EC_RULE_PACKS
        },
        None: {
            cmk.utils.paths.local_root / "some" / "other" / "file.sh",
        },
    }
    assert packaging.all_local_files(_PATH_CONFIG) == expected
