# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for the config deployer (_copy_dir, _install_files, deploy_config)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cmk.dev_deploy.deployers import config_deployer
from cmk.dev_deploy.deployers.config_deployer import (
    _compile_and_deploy_locale,
    _copy_dir,
    _install_files,
    deploy_config,
)
from cmk.dev_deploy.types import (
    ConfigDeploySpec,
    ConfigFileEntry,
    DeployMethod,
    Edition,
    SiteInfo,
)


def _spec(
    *,
    source_prefix: str,
    site_dest: str,
    files: tuple[ConfigFileEntry, ...],
    method: DeployMethod = DeployMethod.COPY_DIR,
    delete_extra: bool = False,
) -> ConfigDeploySpec:
    return ConfigDeploySpec(
        source_prefix=source_prefix,
        site_dest=site_dest,
        method=method,
        mode=None,
        includes=(),
        files=files,
        delete_extra=delete_extra,
        file_chmod=None,
    )


class TestCopyDirRenames:
    """Destinations must follow entry.dest, which carries pkg_files renames."""

    def test_renamed_file_deploys_under_packaged_name(self, tmp_path: Path) -> None:
        """bin/check_mk.py is packaged as bin/check_mk — never as check_mk.py."""
        repo = tmp_path / "repo"
        (repo / "bin").mkdir(parents=True)
        (repo / "bin" / "check_mk.py").write_text("#!/usr/bin/env python3\n")
        site_bin = tmp_path / "site" / "bin"

        spec = _spec(
            source_prefix="bin/",
            site_dest="bin/",
            files=(ConfigFileEntry(src="bin/check_mk.py", dest="bin/check_mk", mode="0755"),),
        )
        _copy_dir(repo / "bin", site_bin, spec, repo)

        assert (site_bin / "check_mk").read_text() == "#!/usr/bin/env python3\n"
        assert os.stat(site_bin / "check_mk").st_mode & 0o777 == 0o755
        assert not (site_bin / "check_mk.py").exists()

    def test_src_outside_source_prefix_deploys_to_dest(self, tmp_path: Path) -> None:
        """A file whose src lives outside source_prefix still lands at its dest."""
        repo = tmp_path / "repo"
        (repo / "cmk" / "utils" / "password_store").mkdir(parents=True)
        (repo / "cmk" / "utils" / "password_store" / "cli.py").write_text("cli")
        site_bin = tmp_path / "site" / "bin"

        spec = _spec(
            source_prefix="cmk/utils/password_store/",
            site_dest="bin/",
            files=(
                ConfigFileEntry(
                    src="cmk/utils/password_store/cli.py", dest="bin/cmk-pwstore", mode="0755"
                ),
            ),
        )
        _copy_dir(repo / "cmk" / "utils" / "password_store", site_bin, spec, repo)

        assert (site_bin / "cmk-pwstore").read_text() == "cli"
        assert not (site_bin / "cli.py").exists()

    def test_dest_subdirectories_are_preserved(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "agents" / "plugins").mkdir(parents=True)
        (repo / "agents" / "plugins" / "mk_docker.py").write_text("plugin")
        dest = tmp_path / "site" / "share" / "agents"

        spec = _spec(
            source_prefix="agents/",
            site_dest="share/check_mk/agents/",
            files=(
                ConfigFileEntry(
                    src="agents/plugins/mk_docker.py",
                    dest="share/check_mk/agents/plugins/mk_docker.py",
                    mode="0755",
                ),
            ),
        )
        _copy_dir(repo / "agents", dest, spec, repo)

        assert (dest / "plugins" / "mk_docker.py").read_text() == "plugin"

    def test_delete_extra_keeps_renamed_file_and_removes_stray(self, tmp_path: Path) -> None:
        """delete_extra compares against dest names, so renamed files survive."""
        repo = tmp_path / "repo"
        (repo / "bin").mkdir(parents=True)
        (repo / "bin" / "check_mk.py").write_text("new")
        site_bin = tmp_path / "site" / "bin"
        site_bin.mkdir(parents=True)
        (site_bin / "check_mk.py").write_text("stray from earlier deploy")

        spec = _spec(
            source_prefix="bin/",
            site_dest="bin/",
            files=(ConfigFileEntry(src="bin/check_mk.py", dest="bin/check_mk", mode="0755"),),
            delete_extra=True,
        )
        _copy_dir(repo / "bin", site_bin, spec, repo)

        assert (site_bin / "check_mk").read_text() == "new"
        assert not (site_bin / "check_mk.py").exists()


class TestReadOnlyDestination:
    """Pristine version trees ship read-only files (e.g. 0555 wrappers).

    The clone only guarantees writable parent directories, so deployers
    must replace files via rename instead of opening them for writing.
    """

    def test_copy_dir_replaces_read_only_file(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "bin").mkdir(parents=True)
        (repo / "bin" / "check_mk.py").write_text("new")
        site_bin = tmp_path / "site" / "bin"
        site_bin.mkdir(parents=True)
        (site_bin / "check_mk").write_text("pristine wrapper")
        os.chmod(site_bin / "check_mk", 0o555)

        spec = _spec(
            source_prefix="bin/",
            site_dest="bin/",
            files=(ConfigFileEntry(src="bin/check_mk.py", dest="bin/check_mk", mode="0755"),),
        )
        _copy_dir(repo / "bin", site_bin, spec, repo)

        assert (site_bin / "check_mk").read_text() == "new"
        assert os.stat(site_bin / "check_mk").st_mode & 0o777 == 0o755

    def test_install_files_replaces_read_only_file(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "active_checks").mkdir(parents=True)
        (repo / "active_checks" / "check_foo.py").write_text("new")
        dest = tmp_path / "site" / "lib" / "nagios" / "plugins"
        dest.mkdir(parents=True)
        (dest / "check_foo").write_text("pristine")
        os.chmod(dest / "check_foo", 0o555)

        spec = _spec(
            source_prefix="active_checks/",
            site_dest="lib/nagios/plugins/",
            method=DeployMethod.INSTALL_FILES,
            files=(
                ConfigFileEntry(
                    src="active_checks/check_foo.py",
                    dest="lib/nagios/plugins/check_foo",
                    mode="0755",
                ),
            ),
        )
        assert _install_files(repo / "active_checks", dest, spec, repo) == 1

        assert (dest / "check_foo").read_text() == "new"
        assert os.stat(dest / "check_foo").st_mode & 0o777 == 0o755

    def test_locale_deploy_replaces_read_only_files(self, tmp_path: Path) -> None:
        source = tmp_path / "locale"
        (source / "de" / "LC_MESSAGES").mkdir(parents=True)
        (source / "de" / "alias").write_text("Deutsch")
        (source / "de" / "LC_MESSAGES" / "multisite.mo").write_bytes(b"new mo")
        dest = tmp_path / "site" / "locale"
        (dest / "de" / "LC_MESSAGES").mkdir(parents=True)
        (dest / "de" / "alias").write_text("old")
        os.chmod(dest / "de" / "alias", 0o444)
        (dest / "de" / "LC_MESSAGES" / "multisite.mo").write_bytes(b"old mo")
        os.chmod(dest / "de" / "LC_MESSAGES" / "multisite.mo", 0o444)

        spec = _spec(
            source_prefix="locale/",
            site_dest="share/check_mk/locale/",
            method=DeployMethod.LOCALE_COMPILE,
            files=(),
        )
        installed, _compiled = _compile_and_deploy_locale(source, dest, spec)

        assert installed == 1
        assert (dest / "de" / "alias").read_text() == "Deutsch"
        assert (dest / "de" / "LC_MESSAGES" / "multisite.mo").read_bytes() == b"new mo"


def _make_site(tmp_path: Path) -> tuple[SiteInfo, Path]:
    """Simulate an OMD site home next to a writable version clone.

    Mirrors ``omd create``: the site home symlinks only ``version`` plus
    bin/include/lib/share into the version tree; everything else in the
    home (etc, var, local -- and notably NOT skel) is site-user territory.
    """
    clone = tmp_path / "clone"
    clone.mkdir()
    site_root = tmp_path / "sites" / "unit"
    site_root.mkdir(parents=True)
    (site_root / "version").symlink_to(clone)
    for d in ("bin", "include", "lib", "share"):
        (clone / d).mkdir()
        (site_root / d).symlink_to(Path("version") / d)
    site = SiteInfo(
        name="unit",
        root=site_root,
        edition=Edition.ULTIMATE,
        version_string="3.0.0",
        build_commit=None,
    )
    return site, clone


class TestDeployConfigVersionAnchor:
    """deploy_config must write through the ``version`` symlink into the clone."""

    def _deploy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        repo: Path,
        site: SiteInfo,
        spec: ConfigDeploySpec,
    ) -> int:
        monkeypatch.setattr(config_deployer, "get_config_specs", lambda: (spec,))
        return deploy_config(None, repo, site).specs_deployed

    def test_skel_dest_lands_in_version_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """skel/ has no site-home symlink -- only the version anchor works."""
        site, clone = _make_site(tmp_path)
        repo = tmp_path / "repo"
        src = repo / "omd" / "packages" / "stunnel" / "skel" / "etc" / "stunnel"
        src.mkdir(parents=True)
        (src / "server.conf").write_text("cert = site\n")

        deployed = self._deploy(
            monkeypatch,
            repo,
            site,
            _spec(
                source_prefix="omd/packages/stunnel/skel/",
                site_dest="skel/etc/stunnel/",
                files=(
                    ConfigFileEntry(
                        src="omd/packages/stunnel/skel/etc/stunnel/server.conf",
                        dest="skel/etc/stunnel/server.conf",
                        mode="0644",
                    ),
                ),
            ),
        )

        assert deployed == 1
        assert (clone / "skel" / "etc" / "stunnel" / "server.conf").read_text() == "cert = site\n"
        # The site home itself must stay untouched -- creating skel/ there
        # is exactly the EACCES failure on a real site.
        assert not (site.root / "skel").exists()

    def test_share_dest_matches_the_site_home_symlink(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The version anchor reaches the same tree the share symlink exposes."""
        site, clone = _make_site(tmp_path)
        repo = tmp_path / "repo"
        src = repo / "agents" / "plugins"
        src.mkdir(parents=True)
        (src / "mk_docker.py").write_text("plugin")

        deployed = self._deploy(
            monkeypatch,
            repo,
            site,
            _spec(
                source_prefix="agents/",
                site_dest="share/check_mk/agents/plugins/",
                files=(
                    ConfigFileEntry(
                        src="agents/plugins/mk_docker.py",
                        dest="share/check_mk/agents/plugins/mk_docker.py",
                        mode="0755",
                    ),
                ),
            ),
        )

        assert deployed == 1
        assert (clone / "share" / "check_mk" / "agents" / "plugins" / "mk_docker.py").is_file()
        # Reachable exactly where the site serves it from.
        assert (site.root / "share" / "check_mk" / "agents" / "plugins" / "mk_docker.py").is_file()

    def test_spec_without_copyable_files_creates_no_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A prefix-matched spec whose listed sources are absent is a no-op."""
        site, clone = _make_site(tmp_path)
        repo = tmp_path / "repo"
        (repo / "agents" / "windows").mkdir(parents=True)

        deployed = self._deploy(
            monkeypatch,
            repo,
            site,
            _spec(
                source_prefix="agents/windows/",
                site_dest="share/check_mk/agents/windows/",
                files=(
                    ConfigFileEntry(
                        src="agents/windows/not_checked_in.exe",
                        dest="share/check_mk/agents/windows/not_checked_in.exe",
                        mode="0755",
                    ),
                ),
                delete_extra=True,
            ),
        )

        assert deployed == 1
        assert not (clone / "share" / "check_mk").exists()


class TestInstallFilesRenames:
    def test_installs_under_packaged_basename(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        (repo / "active_checks").mkdir(parents=True)
        (repo / "active_checks" / "check_foo.py").write_text("check")
        dest = tmp_path / "site" / "lib" / "nagios" / "plugins"

        spec = _spec(
            source_prefix="active_checks/",
            site_dest="lib/nagios/plugins/",
            method=DeployMethod.INSTALL_FILES,
            files=(
                ConfigFileEntry(
                    src="active_checks/check_foo.py",
                    dest="lib/nagios/plugins/check_foo",
                    mode="0755",
                ),
            ),
        )
        count = _install_files(repo / "active_checks", dest, spec, repo)

        assert count == 1
        assert (dest / "check_foo").read_text() == "check"
        assert not (dest / "check_foo.py").exists()
