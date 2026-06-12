# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.version_clone.

The module is pure file/symlink manipulation plus ``omd stop/start``
through the sudoers rule.  The tests run it against a fake OMD layout in
a tmp dir: ``run_as_site_user`` executes commands locally, and a fake
``omd`` on ``$PATH`` records the stop/start sequence.
"""

from __future__ import annotations

import dataclasses
import os
import stat
import subprocess
from pathlib import Path

import pytest

from cmk.dev_deploy.errors import CloneError
from cmk.dev_deploy.site import sudoers, version_clone
from cmk.dev_deploy.site.version_clone import ensure_clone, is_clone_active, teardown_clone

_VERSION = "2.6.0-2026.06.01.pro"


@dataclasses.dataclass(frozen=True)
class FakeOmd:
    """Fake OMD layout: pristine version tree, site dir, clone base."""

    pristine: Path
    site_root: Path
    dev_versions: Path
    omd_log: Path
    shim_bin: Path

    @property
    def version_link(self) -> Path:
        return self.site_root / "version"

    @property
    def clone(self) -> Path:
        return self.dev_versions / self.site_root.name / _VERSION

    def omd_calls(self) -> list[str]:
        return self.omd_log.read_text().splitlines() if self.omd_log.is_file() else []


def _local_run_as_site_user(
    site_name: str,  # noqa: ARG001
    command: str,
    *,
    timeout: int = 30,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        input=input_text,
    )


@pytest.fixture
def omd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeOmd:
    pristine = tmp_path / "versions" / _VERSION
    (pristine / "bin").mkdir(parents=True)
    (pristine / "bin" / "cmc").write_text("binary")
    (pristine / "lib").mkdir()
    (pristine / "lib" / "module.py").write_text("code")

    site_root = tmp_path / "sites" / "v260"
    site_root.mkdir(parents=True)
    (site_root / "version").symlink_to(f"../../versions/{_VERSION}")

    dev_versions = tmp_path / "dev-versions"
    dev_versions.mkdir()

    shim_bin = tmp_path / "shim-bin"
    shim_bin.mkdir()
    omd_log = tmp_path / "omd.log"
    _write_shim(shim_bin, "omd", '#!/bin/sh\necho "$1" >> "$OMD_LOG"\n')
    _write_shim(shim_bin, "getcap", "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("PATH", f"{shim_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("OMD_LOG", str(omd_log))

    monkeypatch.setattr(version_clone, "PRISTINE_VERSIONS_DIR", tmp_path / "versions")
    monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)
    monkeypatch.setattr(sudoers, "run_as_site_user", _local_run_as_site_user)

    return FakeOmd(
        pristine=pristine,
        site_root=site_root,
        dev_versions=dev_versions,
        omd_log=omd_log,
        shim_bin=shim_bin,
    )


def _write_shim(bin_dir: Path, name: str, script: str) -> None:
    shim = bin_dir / name
    shim.write_text(script)
    shim.chmod(0o755)


# ---------------------------------------------------------------------------
# is_clone_active
# ---------------------------------------------------------------------------


class TestIsCloneActive:
    def test_false_on_pristine_symlink(self, omd: FakeOmd) -> None:
        assert is_clone_active(omd.site_root) is False

    def test_true_on_existing_clone(self, omd: FakeOmd) -> None:
        omd.clone.mkdir(parents=True)
        omd.version_link.unlink()
        omd.version_link.symlink_to(omd.clone)
        assert is_clone_active(omd.site_root) is True

    def test_false_on_dangling_clone_symlink(self, omd: FakeOmd) -> None:
        omd.version_link.unlink()
        omd.version_link.symlink_to(omd.clone)  # clone dir does not exist
        assert is_clone_active(omd.site_root) is False

    def test_false_without_symlink(self, tmp_path: Path) -> None:
        assert is_clone_active(tmp_path) is False


# ---------------------------------------------------------------------------
# ensure_clone
# ---------------------------------------------------------------------------


class TestEnsureClone:
    def test_first_run_builds_and_activates(self, omd: FakeOmd) -> None:
        ensure_clone(omd.site_root)

        assert (omd.clone / "bin" / "cmc").read_text() == "binary"
        assert (omd.clone / "lib" / "module.py").read_text() == "code"
        assert os.readlink(omd.version_link) == str(omd.clone)
        assert omd.omd_calls() == ["stop", "start"]

    def test_active_clone_is_noop(self, omd: FakeOmd) -> None:
        ensure_clone(omd.site_root)
        sentinel = omd.clone / "deployed.txt"
        sentinel.write_text("keep me")

        ensure_clone(omd.site_root)

        assert sentinel.read_text() == "keep me"
        assert omd.omd_calls() == ["stop", "start"]  # no second restart

    def test_reuses_existing_clone_with_matching_version(self, omd: FakeOmd) -> None:
        omd.clone.mkdir(parents=True)
        sentinel = omd.clone / "deployed.txt"
        sentinel.write_text("keep me")

        ensure_clone(omd.site_root)

        assert os.readlink(omd.version_link) == str(omd.clone)
        assert sentinel.read_text() == "keep me"

    def test_rebuilds_dangling_clone_symlink(self, omd: FakeOmd) -> None:
        omd.version_link.unlink()
        omd.version_link.symlink_to(omd.clone)  # clone dir does not exist

        ensure_clone(omd.site_root)

        assert (omd.clone / "bin" / "cmc").read_text() == "binary"
        assert omd.omd_calls() == ["stop", "start"]

    def test_stale_clone_after_version_change_fails_loudly(self, omd: FakeOmd) -> None:
        stale = omd.dev_versions / "v260" / "2.5.0-old"
        stale.mkdir(parents=True)

        with pytest.raises(CloneError, match="stale clone") as excinfo:
            ensure_clone(omd.site_root)
        assert "--purge" in str(excinfo.value)
        assert os.readlink(omd.version_link) == f"../../versions/{_VERSION}"  # untouched

    def test_unexpected_symlink_target_fails(self, omd: FakeOmd, tmp_path: Path) -> None:
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        omd.version_link.unlink()
        omd.version_link.symlink_to(elsewhere)

        with pytest.raises(CloneError, match="Unexpected 'version' symlink"):
            ensure_clone(omd.site_root)

    def test_missing_pristine_version_fails(self, omd: FakeOmd) -> None:
        omd.version_link.unlink()
        omd.version_link.symlink_to("../../versions/9.9.9-ghost")

        with pytest.raises(CloneError, match="does not exist"):
            ensure_clone(omd.site_root)

    def test_missing_version_symlink_fails(self, tmp_path: Path) -> None:
        with pytest.raises(CloneError, match="no readable 'version' symlink"):
            ensure_clone(tmp_path)

    def test_interrupted_build_leftovers_are_dropped(self, omd: FakeOmd) -> None:
        partial = omd.dev_versions / "v260" / f".partial-{_VERSION}"
        partial.mkdir(parents=True)
        (partial / "junk").write_text("incomplete")

        ensure_clone(omd.site_root)

        assert not partial.exists()
        assert (omd.clone / "bin" / "cmc").read_text() == "binary"


# ---------------------------------------------------------------------------
# Capability binaries
# ---------------------------------------------------------------------------


class TestCapabilityLinks:
    def test_capability_binaries_symlink_to_pristine(self, omd: FakeOmd) -> None:
        icmp = omd.pristine / "bin" / "icmpsender"
        icmp.write_text("icmp binary")
        _write_shim(
            omd.shim_bin,
            "getcap",
            f'#!/bin/sh\necho "{icmp} cap_net_raw=ep"\n',
        )

        ensure_clone(omd.site_root)

        clone_icmp = omd.clone / "bin" / "icmpsender"
        assert clone_icmp.is_symlink()
        assert os.readlink(clone_icmp) == str(icmp)
        assert (omd.clone / "bin" / "cmc").is_symlink() is False

    def test_missing_getcap_returns_no_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/nonexistent")
        assert version_clone._capability_files(Path("/x")) == []  # noqa: SLF001


# ---------------------------------------------------------------------------
# Read-only directories (pristine trees ship e.g. mode 0555 dirs)
# ---------------------------------------------------------------------------


class TestReadOnlyDirectories:
    def test_read_only_pristine_dirs_become_writable(self, omd: FakeOmd) -> None:
        ro_dir = omd.pristine / "share" / "openapi"
        ro_dir.mkdir(parents=True)
        (ro_dir / "spec.json").write_text("{}")
        ro_dir.chmod(0o555)
        try:
            ensure_clone(omd.site_root)
        finally:
            ro_dir.chmod(0o755)  # let pytest clean tmp_path

        clone_dir = omd.clone / "share" / "openapi"
        assert clone_dir.stat().st_mode & stat.S_IWUSR
        assert (clone_dir / "spec.json").read_text() == "{}"
        teardown_clone(omd.site_root)
        assert not omd.clone.exists()

    def test_teardown_removes_read_only_dirs_of_old_clones(self, omd: FakeOmd) -> None:
        ro_dir = omd.clone / "share" / "locked"
        ro_dir.mkdir(parents=True)
        (ro_dir / "file").write_text("x")
        ro_dir.chmod(0o555)
        omd.version_link.unlink()
        omd.version_link.symlink_to(omd.clone)

        teardown_clone(omd.site_root)

        assert not (omd.dev_versions / "v260").exists()


# ---------------------------------------------------------------------------
# teardown_clone
# ---------------------------------------------------------------------------


class TestTeardownClone:
    def test_reverts_symlink_and_removes_clone(self, omd: FakeOmd) -> None:
        ensure_clone(omd.site_root)
        omd.omd_log.unlink()

        teardown_clone(omd.site_root)

        assert os.readlink(omd.version_link) == f"../../versions/{_VERSION}"
        assert not (omd.dev_versions / "v260").exists()
        assert omd.omd_calls() == ["stop"]  # left stopped

    def test_pristine_site_only_cleans_leftovers(self, omd: FakeOmd) -> None:
        leftover = omd.dev_versions / "v260" / "2.5.0-old"
        leftover.mkdir(parents=True)

        teardown_clone(omd.site_root)

        assert os.readlink(omd.version_link) == f"../../versions/{_VERSION}"
        assert not leftover.exists()
        assert omd.omd_calls() == []  # site untouched

    def test_deleted_site_only_removes_clone_data(self, omd: FakeOmd, tmp_path: Path) -> None:
        clone = omd.dev_versions / "gone" / _VERSION
        clone.mkdir(parents=True)

        teardown_clone(tmp_path / "sites" / "gone")

        assert not (omd.dev_versions / "gone").exists()
