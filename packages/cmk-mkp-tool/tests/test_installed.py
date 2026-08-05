#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.mkp_tool import Installer, PackageID, PackageName, PackagePart, PackageVersion
from cmk.mkp_tool._installed import (
    cleanup_legacy_linked_lib_check_mk_path,
    replace_legacy_linked_lib_check_mk_path,
)
from cmk.mkp_tool._mkp import Manifest, manifest_template


def _manifest(name: str, files: dict[PackagePart, list[Path]] | None = None) -> Manifest:
    return manifest_template(
        PackageName(name),
        version_packaged="2.5.0",
        version_required="2.4.0",
        version=PackageVersion("1.0.0"),
        files=files or {},
    )


class TestInstaller:
    def test_not_installed(self, installer: Installer) -> None:
        assert not installer.is_installed(PackageName("nonexistent"))
        assert installer.get_installed_manifest(PackageName("nonexistent")) is None

    def test_no_manifests_at_all(self, installer: Installer) -> None:
        assert installer.get_installed_manifests() == []

    def test_add_then_get(self, installer: Installer) -> None:
        manifest = _manifest("cool_package")

        installer.add_installed_manifest(manifest)

        assert installer.is_installed(PackageName("cool_package"))
        assert installer.get_installed_manifest(PackageName("cool_package")) == manifest

    def test_add_then_remove(self, installer: Installer) -> None:
        manifest = _manifest("cool_package")
        installer.add_installed_manifest(manifest)

        installer.remove_installed_manifest(PackageName("cool_package"))

        assert not installer.is_installed(PackageName("cool_package"))
        assert installer.get_installed_manifests() == []

    def test_remove_not_installed_is_no_error(self, installer: Installer) -> None:
        installer.remove_installed_manifest(PackageName("nonexistent"))

    def test_get_installed_manifests_is_sorted_by_name(self, installer: Installer) -> None:
        for name in ("charlie", "alpha", "bravo"):
            installer.add_installed_manifest(_manifest(name))

        assert [str(m.name) for m in installer.get_installed_manifests()] == [
            "alpha",
            "bravo",
            "charlie",
        ]

    def test_get_packaged_files_lists_every_part(self, installer: Installer) -> None:
        installer.add_installed_manifest(
            _manifest("cool_package", {PackagePart.LIB: [Path("some/file.py")]})
        )

        packaged_files = installer.get_packaged_files()

        # every part is present, even if it holds no files
        assert set(packaged_files) == set(PackagePart)
        assert packaged_files[PackagePart.LIB] == {
            Path("some/file.py"): PackageID(
                name=PackageName("cool_package"), version=PackageVersion("1.0.0")
            )
        }
        assert packaged_files[PackagePart.AGENTS] == {}

    def test_get_packaged_files_merges_packages(self, installer: Installer) -> None:
        installer.add_installed_manifest(
            _manifest("package_a", {PackagePart.AGENTS: [Path("a.sh")]})
        )
        installer.add_installed_manifest(
            _manifest("package_b", {PackagePart.AGENTS: [Path("b.sh")]})
        )

        assert set(installer.get_packaged_files()[PackagePart.AGENTS]) == {
            Path("a.sh"),
            Path("b.sh"),
        }


class TestReplaceLegacyLinkedLibCheckMkPath:
    def test_no_lib_files_returns_same_manifest(self) -> None:
        manifest = _manifest("cool_package", {PackagePart.AGENTS: [Path("agent")]})

        assert replace_legacy_linked_lib_check_mk_path(manifest) is manifest

    def test_no_legacy_reference_returns_same_manifest(self) -> None:
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("python3/cmk/thing.py")]})

        assert replace_legacy_linked_lib_check_mk_path(manifest) is manifest

    def test_legacy_reference_is_rewritten(self) -> None:
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("check_mk/thing.py")]})

        assert replace_legacy_linked_lib_check_mk_path(manifest).files[PackagePart.LIB] == [
            Path("python3/cmk/thing.py")
        ]

    def test_only_legacy_references_are_rewritten(self) -> None:
        manifest = _manifest(
            "cool_package",
            {
                PackagePart.LIB: [
                    Path("check_mk/legacy.py"),
                    Path("nagios/keep_me.py"),
                ]
            },
        )

        assert replace_legacy_linked_lib_check_mk_path(manifest).files[PackagePart.LIB] == [
            Path("python3/cmk/legacy.py"),
            Path("nagios/keep_me.py"),
        ]

    def test_other_parts_are_preserved(self) -> None:
        manifest = _manifest(
            "cool_package",
            {
                PackagePart.LIB: [Path("check_mk/thing.py")],
                PackagePart.AGENTS: [Path("agent")],
            },
        )

        rewritten = replace_legacy_linked_lib_check_mk_path(manifest)

        assert rewritten.files[PackagePart.AGENTS] == [Path("agent")]
        # the rest of the metadata survives the rebuild
        assert rewritten.name == manifest.name
        assert rewritten.version == manifest.version
        assert rewritten.title == manifest.title

    def test_a_bare_check_mk_path_is_not_confused_with_a_prefix(self) -> None:
        # "check_mk_extra" merely starts with the same string; it is a different directory
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("check_mk_extra/thing.py")]})

        assert replace_legacy_linked_lib_check_mk_path(manifest) is manifest


class TestCleanupLegacyLinkedLibCheckMkPath:
    def test_file_is_moved_and_empty_dirs_removed(self, tmp_path: Path) -> None:
        lib_path = tmp_path / "lib"
        (lib_path / "check_mk" / "nested").mkdir(parents=True)
        (lib_path / "check_mk" / "nested" / "thing.py").write_text("content")
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("check_mk/nested/thing.py")]})

        cleanup_legacy_linked_lib_check_mk_path(lib_path, manifest)

        assert (lib_path / "python3" / "cmk" / "nested" / "thing.py").read_text() == "content"
        # the now-empty legacy directories are cleaned up
        assert not (lib_path / "check_mk").exists()

    def test_non_empty_legacy_dir_is_kept(self, tmp_path: Path) -> None:
        lib_path = tmp_path / "lib"
        (lib_path / "check_mk").mkdir(parents=True)
        (lib_path / "check_mk" / "thing.py").write_text("content")
        (lib_path / "check_mk" / "unrelated.py").write_text("keep me")
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("check_mk/thing.py")]})

        cleanup_legacy_linked_lib_check_mk_path(lib_path, manifest)

        assert (lib_path / "python3" / "cmk" / "thing.py").read_text() == "content"
        assert (lib_path / "check_mk" / "unrelated.py").read_text() == "keep me"

    def test_nothing_to_do_without_legacy_files(self, tmp_path: Path) -> None:
        manifest = _manifest("cool_package", {PackagePart.LIB: [Path("python3/cmk/thing.py")]})

        cleanup_legacy_linked_lib_check_mk_path(tmp_path, manifest)

        assert list(tmp_path.iterdir()) == []
