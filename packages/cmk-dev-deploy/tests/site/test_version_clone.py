# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.version_clone.

The module is pure file/symlink manipulation plus ``omd stop/start``
through the sudoers rule.  The tests run it against a fake OMD layout in
a tmp dir: ``run_as_site_user`` executes commands locally, a fake
``omd`` on ``$PATH`` records the stop/start sequence, and
``delete_state`` is replaced by a recorder (``FakeOmd.state_resets``).
"""

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
    state_resets: list[Path]

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

    state_resets: list[Path] = []
    monkeypatch.setattr(version_clone, "PRISTINE_VERSIONS_DIR", tmp_path / "versions")
    monkeypatch.setattr(version_clone, "delete_state", state_resets.append)
    monkeypatch.setattr(sudoers, "DEV_VERSIONS_DIR", dev_versions)
    monkeypatch.setattr(sudoers, "run_as_site_user", _local_run_as_site_user)

    return FakeOmd(
        pristine=pristine,
        site_root=site_root,
        dev_versions=dev_versions,
        omd_log=omd_log,
        shim_bin=shim_bin,
        state_resets=state_resets,
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

    def test_hidden_dirs_are_not_stale_clones(self, omd: FakeOmd) -> None:
        (omd.dev_versions / "v260" / ".some-tool-data").mkdir(parents=True)

        ensure_clone(omd.site_root)  # must not raise a stale-clone error

        assert (omd.clone / "bin" / "cmc").read_text() == "binary"

    def test_stale_clone_after_version_change_is_discarded(self, omd: FakeOmd) -> None:
        stale = omd.dev_versions / "v260" / "2.5.0-old"
        (stale / "lib").mkdir(parents=True)
        (stale / "lib" / "deployed.py").write_text("old dev code")

        ensure_clone(omd.site_root)

        assert not stale.exists()
        assert (omd.clone / "bin" / "cmc").read_text() == "binary"
        assert os.readlink(omd.version_link) == str(omd.clone)

    def test_stale_clone_is_discarded_even_when_current_clone_exists(self, omd: FakeOmd) -> None:
        stale = omd.dev_versions / "v260" / "2.5.0-old"
        stale.mkdir(parents=True)
        omd.clone.mkdir(parents=True)

        ensure_clone(omd.site_root)

        assert not stale.exists()
        assert os.readlink(omd.version_link) == str(omd.clone)
        assert omd.state_resets == [omd.site_root]  # state may describe the discarded clone

    def test_stale_clone_with_read_only_dirs_is_discarded(self, omd: FakeOmd) -> None:
        ro_dir = omd.dev_versions / "v260" / "2.5.0-old" / "locked"
        ro_dir.mkdir(parents=True)
        (ro_dir / "file").write_text("x")
        ro_dir.chmod(0o555)

        ensure_clone(omd.site_root)

        assert not (omd.dev_versions / "v260" / "2.5.0-old").exists()

    def test_unremovable_stale_clone_fails_before_activation(
        self, omd: FakeOmd, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stale = omd.dev_versions / "v260" / "2.5.0-old"
        stale.mkdir(parents=True)
        real_rmtree = version_clone._rmtree  # noqa: SLF001

        def failing_rmtree(path: Path, *, ignore_errors: bool = False) -> None:
            if path == stale:
                raise OSError("Device or resource busy")
            real_rmtree(path, ignore_errors=ignore_errors)

        monkeypatch.setattr(version_clone, "_rmtree", failing_rmtree)

        with pytest.raises(CloneError, match="stale clone"):
            ensure_clone(omd.site_root)
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
# Parent directory permissions
# ---------------------------------------------------------------------------


class TestParentDirPermissions:
    """The site user resolves its ``version`` symlink through the clone's
    parent directories, so they must stay group/other-traversable no
    matter which umask they were created under."""

    def test_restrictive_umask_yields_traversable_parent_dirs(self, omd: FakeOmd) -> None:
        old_umask = os.umask(0o077)
        try:
            ensure_clone(omd.site_root)
        finally:
            os.umask(old_umask)

        for parent in (omd.dev_versions, omd.clone.parent):
            assert parent.stat().st_mode & 0o055 == 0o055

    def test_heals_restrictive_parent_dirs_of_active_clone(self, omd: FakeOmd) -> None:
        """Dirs created by earlier tool versions under umask 027/077 are
        repaired on the next run, even when the clone itself is a no-op."""
        ensure_clone(omd.site_root)
        omd.dev_versions.chmod(0o700)
        omd.clone.parent.chmod(0o700)

        ensure_clone(omd.site_root)

        for parent in (omd.dev_versions, omd.clone.parent):
            assert parent.stat().st_mode & 0o055 == 0o055


# ---------------------------------------------------------------------------
# Incremental deploy state resets
# ---------------------------------------------------------------------------


class TestDeployStateReset:
    """The state must not outlive the tree the recorded deploys went into."""

    def test_fresh_build_resets_state(self, omd: FakeOmd) -> None:
        ensure_clone(omd.site_root)

        assert omd.state_resets == [omd.site_root]

    def test_active_clone_keeps_state(self, omd: FakeOmd) -> None:
        ensure_clone(omd.site_root)
        omd.state_resets.clear()

        ensure_clone(omd.site_root)

        assert omd.state_resets == []

    def test_reused_clone_keeps_state(self, omd: FakeOmd) -> None:
        omd.clone.mkdir(parents=True)

        ensure_clone(omd.site_root)

        assert omd.state_resets == []

    def test_dangling_symlink_rebuild_resets_state(self, omd: FakeOmd) -> None:
        omd.version_link.unlink()
        omd.version_link.symlink_to(omd.clone)  # clone dir does not exist

        ensure_clone(omd.site_root)

        assert omd.state_resets == [omd.site_root]


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
# Unreadable binaries (root:omd 0750 capability/setuid helpers)
# ---------------------------------------------------------------------------


class TestUnreadableBinaries:
    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-0 files; cp would not fail")
    def test_unreadable_binaries_symlink_to_pristine(self, omd: FakeOmd) -> None:
        restricted = omd.pristine / "bin" / "mkeventd_open514"
        restricted.write_text("root:omd only")
        restricted.chmod(0)

        ensure_clone(omd.site_root)

        clone_path = omd.clone / "bin" / "mkeventd_open514"
        assert clone_path.is_symlink()
        assert os.readlink(clone_path) == str(restricted)
        assert (omd.clone / "bin" / "cmc").read_text() == "binary"  # rest is copied
        assert os.readlink(omd.version_link) == str(omd.clone)  # clone activated

    def test_other_cp_errors_stay_fatal(self, omd: FakeOmd) -> None:
        _write_shim(
            omd.shim_bin,
            "cp",
            "#!/bin/sh\necho \"cp: error writing '/x': No space left on device\" >&2\nexit 1\n",
        )

        with pytest.raises(CloneError, match="Failed to clone"):
            ensure_clone(omd.site_root)

        assert os.readlink(omd.version_link) == f"../../versions/{_VERSION}"  # untouched


class TestUnreadablePristineFiles:
    @staticmethod
    def _parse(pristine: Path, stderr: str) -> list[Path] | None:
        return version_clone._unreadable_pristine_files(pristine, stderr)  # noqa: SLF001

    @staticmethod
    def _denied(path: Path) -> str:
        return f"cp: cannot open '{path}' for reading: Permission denied"

    def test_unreadable_regular_files_are_tolerated(self, tmp_path: Path) -> None:
        icmp = tmp_path / "lib" / "check_icmp"
        icmp.parent.mkdir()
        icmp.write_text("x")
        stderr = f"{self._denied(icmp)}\n{self._denied(icmp)}\n"

        assert self._parse(tmp_path, stderr) == [icmp, icmp]

    def test_any_other_error_line_is_fatal(self, tmp_path: Path) -> None:
        icmp = tmp_path / "check_icmp"
        icmp.write_text("x")
        stderr = f"{self._denied(icmp)}\ncp: error writing '/x': No space left on device\n"

        assert self._parse(tmp_path, stderr) is None

    def test_unreadable_directory_is_fatal(self, tmp_path: Path) -> None:
        private = tmp_path / "private"
        private.mkdir()

        assert self._parse(tmp_path, self._denied(private)) is None

    def test_path_outside_pristine_is_fatal(self, tmp_path: Path) -> None:
        outside = tmp_path / "elsewhere" / "file"
        outside.parent.mkdir()
        outside.write_text("x")

        assert self._parse(tmp_path / "pristine", self._denied(outside)) is None

    def test_missing_file_is_fatal(self, tmp_path: Path) -> None:
        assert self._parse(tmp_path, self._denied(tmp_path / "ghost")) is None

    def test_empty_stderr_is_fatal(self, tmp_path: Path) -> None:
        assert self._parse(tmp_path, "") is None


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
