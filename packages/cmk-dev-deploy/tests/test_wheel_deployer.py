# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for the pip-based wheel deployer."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from cmk.dev_deploy.deployers import wheel_deployer
from cmk.dev_deploy.errors import WheelDeployError
from cmk.dev_deploy.types import ChangeSet, Edition, SiteInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PREFIXES = ("cmk/", "packages/cmk-ccc/", "packages/cmk-shared-typing/")


def _changes(
    files: tuple[str, ...] = (),
    deleted: tuple[str, ...] = (),
) -> ChangeSet:
    return ChangeSet(
        build_commit="abc123",
        files=files,
        categories={},
        deleted_files=deleted,
    )


def _site(tmp_path: Path, edition: Edition = Edition.ULTIMATE) -> SiteInfo:
    root = tmp_path / "site"
    root.mkdir(parents=True, exist_ok=True)
    return SiteInfo(
        name="test",
        root=root,
        edition=edition,
        version_string=f"2026.06.09.{edition.value}",
        build_commit="abc123",
    )


# ---------------------------------------------------------------------------
# wheel_prefixes
# ---------------------------------------------------------------------------


def test_wheel_prefixes_come_from_manifest() -> None:
    with patch.object(wheel_deployer, "get_wheel_prefixes", return_value=("packages/cmk-ccc/",)):
        assert wheel_deployer.wheel_prefixes() == ("packages/cmk-ccc/",)


# ---------------------------------------------------------------------------
# has_wheel_changes
# ---------------------------------------------------------------------------


class TestHasWheelChanges:
    def test_no_baseline_deploys(self) -> None:
        assert wheel_deployer.has_wheel_changes(None)

    @pytest.mark.parametrize(
        "filepath",
        [
            "cmk/gui/main.py",
            "packages/cmk-ccc/cmk/ccc/site.py",
            "packages/cmk-shared-typing/source/vue_formspec.json",
        ],
    )
    def test_changed_file_in_wheel(self, filepath: str) -> None:
        with patch.object(wheel_deployer, "wheel_prefixes", return_value=_PREFIXES):
            assert wheel_deployer.has_wheel_changes(_changes(files=(filepath,)))

    def test_deleted_file_in_wheel(self) -> None:
        with patch.object(wheel_deployer, "wheel_prefixes", return_value=_PREFIXES):
            assert wheel_deployer.has_wheel_changes(_changes(deleted=("cmk/gui/obsolete.py",)))

    @pytest.mark.parametrize(
        "filepath",
        [
            "agents/check_mk_agent.linux",
            "packages/cmk-ccc-sibling/foo.py",  # prefix match needs the slash
            "omd/BUILD",
        ],
    )
    def test_unrelated_file(self, filepath: str) -> None:
        with patch.object(wheel_deployer, "wheel_prefixes", return_value=_PREFIXES):
            assert not wheel_deployer.has_wheel_changes(_changes(files=(filepath,)))


# ---------------------------------------------------------------------------
# deploy_wheels
# ---------------------------------------------------------------------------


class TestDeployWheels:
    def test_invokes_deploy_python_for_site_edition(self, tmp_path: Path) -> None:
        site = _site(tmp_path, Edition.ULTIMATE)
        completed = CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr=(
                "Bytecode compiled 6556 files in 967ms\n + cmk-ccc==1.0.0\n ~ checkmk==1+ultimate\n"
            ),
        )
        with patch.object(wheel_deployer, "run_checked", return_value=completed) as run:
            result = wheel_deployer.deploy_wheels(Path("/repo"), site)

        cmd = run.call_args.args[0]
        assert cmd[:3] == ["bazel", "run", "--noshow_progress"]
        assert wheel_deployer.DEPLOY_PYTHON_TARGET in cmd
        assert "--cmk_edition=ultimate" in cmd
        assert cmd[-2:] == ["--", str(site.root)]
        assert run.call_args.kwargs["cwd"] == Path("/repo")
        assert result.wheels_installed == 2

    def test_legacy_site_layout_rejected(self, tmp_path: Path) -> None:
        site = _site(tmp_path)
        (site.root / "lib" / "python3").mkdir(parents=True)
        with pytest.raises(WheelDeployError, match="legacy"):
            wheel_deployer.deploy_wheels(Path("/repo"), site)

    def test_symlinked_lib_python3_accepted(self, tmp_path: Path) -> None:
        site = _site(tmp_path)
        site_packages = site.root / "lib" / "python3.13" / "site-packages"
        site_packages.mkdir(parents=True)
        (site.root / "lib" / "python3").symlink_to(site_packages)
        completed = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(wheel_deployer, "run_checked", return_value=completed):
            result = wheel_deployer.deploy_wheels(Path("/repo"), site)
        assert result.wheels_installed == 0
