#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import tarfile
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest

from cmk.mkp_tool import _mkp as mkp
from cmk.mkp_tool import (
    Installer,
    PackageError,
    PackageName,
    PackageStore,
    PackageVersion,
    PathConfig,
)
from cmk.mkp_tool.cli import main, SiteContext


@pytest.fixture(name="site_context")
def fixture_site_context(package_store: PackageStore, tmp_path: Path) -> SiteContext:
    (installed_packages_dir := tmp_path / "installed_packages_dir").mkdir(exist_ok=True)
    return SiteContext(
        package_store=package_store,
        installed_packages_dir=installed_packages_dir,
        callbacks={},
        post_package_change_actions=lambda _manifests: None,
        version="2.5.0",
        parse_version=lambda v: (v,),
    )


def _mkp_file(tmp_path: Path, name: str = "cool_package", version: str = "1.0.0") -> Path:
    """Write out the smallest MKP the tooling accepts"""
    manifest = mkp.manifest_template(
        name=PackageName(name),
        version_packaged="2.5.0",
        version_required="2.4.0",
        version=PackageVersion(version),
    )
    content = manifest.file_content().encode()
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("info")
        info.size = len(content)
        tar.addfile(info, BytesIO(content))
    (path := tmp_path / f"{name}-{version}.mkp").write_bytes(buffer.getvalue())
    return path


@pytest.mark.parametrize("command", ["add", "inspect"])
def test_unreadable_file_is_reported(
    command: str,
    site_context: SiteContext,
    path_config: PathConfig,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # a directory can't be read as a file, no matter which user we are
    unreadable = tmp_path / "coolstuff.mkp"
    unreadable.mkdir()

    assert (
        main(path_config, site_context, lambda _path, _content: None, [command, str(unreadable)])
        == 1
    )

    assert str(unreadable) in capsys.readouterr().err


class TestArgumentParsing:
    def test_without_arguments_usage_is_shown(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:

        with pytest.raises(SystemExit):
            main(argv=[])

        assert "usage" in capsys.readouterr().err

    def test_unknown_command(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
    ) -> None:
        with pytest.raises(SystemExit):
            main(path_config, site_context, argv=["no-such-command"])

    def test_site_only_commands_are_unavailable_without_site_context(
        self,
        path_config: PathConfig,
    ) -> None:
        with pytest.raises(SystemExit):
            main(path_config, None, lambda _p, _c: None, argv=["list"])


class TestReadOnlyCommands:
    def test_path_config_template(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["path-config-template"]) == 0

        out = capsys.readouterr().out
        assert "[paths]" in out
        assert "cmk_plugins_dir" in out

    def test_template(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["template", "cool_package"]) == 0

        out = capsys.readouterr().out
        assert "cool_package" in out
        # the template must be readable back in
        assert mkp.Manifest.parse_python_string(out).name == PackageName("cool_package")

    def test_find(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path_config.agents_dir.joinpath("some_agent").write_text("hello\n")

        assert main(path_config, site_context, argv=["find"]) == 0

        out = capsys.readouterr().out
        assert "File" in out and "Package" in out
        assert "some_agent" in out

    def test_find_json(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path_config.agents_dir.joinpath("some_agent").write_text("hello\n")

        assert main(path_config, site_context, argv=["find", "--json"]) == 0

        assert [Path(f["file"]).name for f in json.loads(capsys.readouterr().out)] == ["some_agent"]

    def test_inspect(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mkp_path = _mkp_file(tmp_path)

        assert main(path_config, site_context, argv=["inspect", str(mkp_path)]) == 0

        assert "cool_package" in capsys.readouterr().out

    def test_inspect_json(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mkp_path = _mkp_file(tmp_path)

        assert main(path_config, site_context, argv=["inspect", "--json", str(mkp_path)]) == 0

        assert json.loads(capsys.readouterr().out)["name"] == "cool_package"

    def test_list_without_packages(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["list"]) == 0

        # the table header is rendered even without any packages
        assert "Name" in capsys.readouterr().out

    def test_show_all_without_packages(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["show-all"]) == 0

        out = capsys.readouterr().out
        assert "Local extension packages" in out
        assert "Shipped extension packages" in out


class TestPackageLifecycle:
    def test_add_reports_name_and_version(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mkp_path = _mkp_file(tmp_path)

        assert main(path_config, site_context, argv=["add", str(mkp_path)]) == 0

        # these are exactly the arguments `mkp enable` expects
        assert capsys.readouterr().out == "cool_package 1.0.0\n"

    def test_added_package_is_listed_as_disabled(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["list"]) == 0

        out = capsys.readouterr().out
        assert "cool_package" in out
        assert "Disabled" in out

    def test_show_added_package(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["show", "cool_package"]) == 0

        assert "cool_package" in capsys.readouterr().out

    def test_show_unknown_package_is_reported(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["show", "no_such_package"]) == 1

        assert "no_such_package" in capsys.readouterr().err

    def test_debug_flag_reraises(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
    ) -> None:
        with pytest.raises(PackageError):
            main(path_config, site_context, argv=["--debug", "show", "no_such_package"])

    def test_enable_then_list_shows_active(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])

        assert main(path_config, site_context, argv=["enable", "cool_package"]) == 0
        capsys.readouterr()
        assert main(path_config, site_context, argv=["list"]) == 0

        assert "Enabled (active on this site)" in capsys.readouterr().out

    def test_disable_after_enable(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        main(path_config, site_context, argv=["enable", "cool_package"])

        assert main(path_config, site_context, argv=["disable", "cool_package"]) == 0
        capsys.readouterr()
        main(path_config, site_context, argv=["list"])

        assert "Disabled" in capsys.readouterr().out

    def test_files_of_an_added_package(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["files", "cool_package"]) == 0

        # our minimal package holds no files at all
        assert capsys.readouterr().out == ""

    def test_remove_added_package(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["remove", "cool_package"]) == 0
        capsys.readouterr()
        main(path_config, site_context, argv=["list"])

        assert "cool_package" not in capsys.readouterr().out

    def test_remove_unknown_package_is_reported(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["remove", "no_such_package"]) == 1

        assert "no_such_package" in capsys.readouterr().err

    def test_release_of_an_enabled_package(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        main(path_config, site_context, argv=["enable", "cool_package"])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["release", "cool_package"]) == 0

    def test_release_of_an_unknown_package_is_reported(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(path_config, site_context, argv=["release", "no_such_package"]) == 1

        assert "no_such_package" in capsys.readouterr().err

    def test_disable_outdated(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        main(path_config, site_context, argv=["enable", "cool_package"])
        capsys.readouterr()

        # the package is usable until forever, so it stays enabled
        assert main(path_config, site_context, argv=["disable-outdated"]) == 0
        capsys.readouterr()
        main(path_config, site_context, argv=["list"])

        assert "Enabled (active on this site)" in capsys.readouterr().out

    def test_update_active(
        self,
        site_context: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(path_config, site_context, argv=["add", str(_mkp_file(tmp_path))])
        main(path_config, site_context, argv=["enable", "cool_package"])
        capsys.readouterr()

        assert main(path_config, site_context, argv=["update-active"]) == 0


def _mkp_file_with_plugin(
    tmp_path: Path,
    name: str,
    version: str,
    *,
    min_required: str = "2.4.0",
    usable_until: str | None = None,
) -> Path:
    (source_dir := tmp_path / "source" / f"{name}-{version}").mkdir(parents=True)
    (source_dir / f"{name}.py").write_text(version)
    manifest = mkp.manifest_template(
        name=PackageName(name),
        version_packaged="2.4.0",
        version_required=min_required,
        version=PackageVersion(version),
        files={mkp.PackagePart.AGENT_BASED: [Path(f"{name}.py")]},
    ).model_copy(update={"version_usable_until": usable_until})
    (path := tmp_path / f"{name}-{version}.mkp").write_bytes(
        mkp.create_mkp(manifest, lambda _part: source_dir, "2.4.0")
    )
    return path


def _active(site_context: SiteContext) -> set[tuple[str, str]]:
    return {
        (manifest.name, manifest.version)
        for manifest in Installer(site_context.installed_packages_dir).get_installed_manifests()
    }


class TestRestoreActive:
    @pytest.fixture(name="old_site")
    def fixture_old_site(self, site_context: SiteContext) -> SiteContext:
        return replace(site_context, version="2.4.0")

    @pytest.fixture(name="new_site")
    def fixture_new_site(self, site_context: SiteContext) -> SiteContext:
        return replace(site_context, version="2.5.0")

    def test_swapped_out_version_is_active_again(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        old_mkp = _mkp_file_with_plugin(tmp_path, "swapped", "1.0.0", usable_until="2.5.0")
        new_mkp = _mkp_file_with_plugin(tmp_path, "swapped", "2.0.0", min_required="2.5.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(old_mkp)])
        main(path_config, old_site, argv=["add", str(new_mkp)])
        main(path_config, old_site, argv=["enable", "swapped", "1.0.0"])
        main(path_config, old_site, argv=["enable", "swapped", "2.0.0"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        assert main(path_config, new_site, argv=["restore-active", str(record)]) == 0

        assert _active(new_site) == {("swapped", "1.0.0")}
        assert (path_config.agent_based_plugins_dir / "swapped.py").read_text() == "1.0.0"

    def test_package_removed_by_the_update_is_active_again(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        mkp_file = _mkp_file_with_plugin(tmp_path, "outdated", "1.0.0", usable_until="2.5.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(mkp_file)])
        main(path_config, old_site, argv=["enable", "outdated"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert _active(new_site) == {("outdated", "1.0.0")}
        assert (path_config.agent_based_plugins_dir / "outdated.py").exists()

    def test_package_activated_by_the_update_is_inactive_again(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        mkp_file = _mkp_file_with_plugin(tmp_path, "upcoming", "1.0.0", min_required="2.5.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(mkp_file)])
        main(path_config, old_site, argv=["enable", "upcoming"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert _active(new_site) == set()
        assert not (path_config.agent_based_plugins_dir / "upcoming.py").exists()

    def test_force_installed_package_is_active_again(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        mkp_file = _mkp_file_with_plugin(tmp_path, "forced", "1.0.0", usable_until="2.4.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(mkp_file)])
        main(path_config, old_site, argv=["enable", "--force-install", "forced"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert _active(new_site) == {("forced", "1.0.0")}

    def test_package_untouched_by_the_update_stays_active(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        mkp_file = _mkp_file_with_plugin(tmp_path, "timeless", "1.0.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(mkp_file)])
        main(path_config, old_site, argv=["enable", "timeless"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert _active(new_site) == {("timeless", "1.0.0")}

    def test_enabled_packages_stay_enabled(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        old_mkp = _mkp_file_with_plugin(tmp_path, "swapped", "1.0.0", usable_until="2.5.0")
        new_mkp = _mkp_file_with_plugin(tmp_path, "swapped", "2.0.0", min_required="2.5.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(old_mkp)])
        main(path_config, old_site, argv=["add", str(new_mkp)])
        main(path_config, old_site, argv=["enable", "swapped", "1.0.0"])
        main(path_config, old_site, argv=["enable", "swapped", "2.0.0"])
        main(path_config, new_site, argv=["update-active", "--save-active", str(record)])

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert {
            (id_.name, id_.version) for id_ in new_site.package_store.get_enabled_manifests()
        } == {("swapped", "1.0.0"), ("swapped", "2.0.0")}

    def test_failing_package_does_not_stop_the_restore(
        self,
        old_site: SiteContext,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
    ) -> None:
        mkp_file = _mkp_file_with_plugin(tmp_path, "outdated", "1.0.0", usable_until="2.5.0")
        record = tmp_path / "record"
        main(path_config, old_site, argv=["add", str(mkp_file)])
        main(path_config, old_site, argv=["enable", "outdated"])
        main(path_config, new_site, argv=["update-active"])
        record.write_text(
            json.dumps(
                [{"name": "vanished", "version": "1.0.0"}, {"name": "outdated", "version": "1.0.0"}]
            )
        )

        main(path_config, new_site, argv=["restore-active", str(record)])

        assert _active(new_site) == {("outdated", "1.0.0")}

    def test_failing_package_is_reported(
        self,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        record = tmp_path / "record"
        record.write_text(json.dumps([{"name": "vanished", "version": "1.0.0"}]))

        assert main(path_config, new_site, argv=["restore-active", str(record)]) == 1

        assert "vanished 1.0.0" in capsys.readouterr().err

    def test_missing_record_is_reported(
        self,
        new_site: SiteContext,
        path_config: PathConfig,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        record = tmp_path / "record"

        assert main(path_config, new_site, argv=["restore-active", str(record)]) == 1

        assert str(record) in capsys.readouterr().err
