# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.wheel_deployer (dist-info,
clean, skip logic, specs_for_changed_files, generated-source, parallel deploy)."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cmk.dev_deploy.core import output
from cmk.dev_deploy.deployers._distribution_info import (
    build_package_info_from_spec as _build_package_info_from_spec,
)
from cmk.dev_deploy.deployers._distribution_info import (
    derive_top_level_packages as _derive_top_level_packages,
)
from cmk.dev_deploy.deployers.wheel_deployer import (
    _build_and_extract_wheel,
    _clean_package,
    _compute_protected_children,
    _expand_co_dependents,
    _generate_dist_info,
    _selective_rmtree,
    _subdirs_overlap,
    deploy_wheels,
    specs_for_changed_files,
)
from cmk.dev_deploy.types import (
    Edition,
    SiteInfo,
    SkipResult,
    WheelDeployMode,
    WheelDeploySpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wheel_spec(
    package: str = "packages/cmk-ccc",
    wheel_targets: tuple[str, ...] = (":wheel",),
    edition_constraint: frozenset[str] | None = None,
    deploy_mode: WheelDeployMode = WheelDeployMode.DIRECT,
    source_subdirs: tuple[str, ...] = ("cmk/ccc/",),
    distribution_name: str = "",
) -> WheelDeploySpec:
    """Create a WheelDeploySpec with sensible defaults for testing."""
    return WheelDeploySpec(
        package=package,
        wheel_targets=wheel_targets,
        edition_constraint=edition_constraint,
        deploy_mode=deploy_mode,
        source_subdirs=source_subdirs,
        distribution_name=distribution_name,
    )


def _make_site(tmp_path: Path, edition: Edition = Edition.PRO) -> SiteInfo:
    """Create a SiteInfo pointing at tmp_path as the site root."""
    return SiteInfo(
        name="test",
        root=tmp_path / "site",
        edition=edition,
        version_string="2.6.0-2026.02.13.pro",
        build_commit="b" * 40,
    )


def _make_skip_result(
    should_skip: bool = True,
    reason: str = "no changes",
    deployer: str = "wheel:packages/cmk-test",
    paths_checked: tuple[str, ...] = ("packages/cmk-test/",),
    changed_files: tuple[str, ...] = (),
) -> SkipResult:
    """Create a SkipResult with sensible defaults for testing."""
    return SkipResult(
        should_skip=should_skip,
        reason=reason,
        deployer=deployer,
        paths_checked=paths_checked,
        changed_files=changed_files,
    )


# ---------------------------------------------------------------------------
# 1. Package Info Builder Tests
# ---------------------------------------------------------------------------


class TestDeriveTopLevelPackages:
    """Tests for _derive_top_level_packages helper."""

    def test_namespace_subpackage(self) -> None:
        assert _derive_top_level_packages(("cmk/ccc/",)) == ("cmk",)

    def test_multiple_under_same_namespace(self) -> None:
        """Multiple subdirs under cmk/ yield single 'cmk' top-level."""
        result = _derive_top_level_packages(("cmk/fetchers/", "cmk/snmplib/"))
        assert result == ("cmk",)

    def test_standalone_package(self) -> None:
        assert _derive_top_level_packages(("livestatus/",)) == ("livestatus",)

    def test_flat_py_file(self) -> None:
        assert _derive_top_level_packages(("cmk_update_agent.py",)) == ("cmk_update_agent",)

    def test_mixed_namespaces(self) -> None:
        """cmk/livestatus_client/ + livestatus/ yields both top-levels."""
        result = _derive_top_level_packages(("cmk/livestatus_client/", "livestatus/"))
        assert result == ("cmk", "livestatus")


class TestBuildPackageInfoFromSpec:
    """Tests for _build_package_info_from_spec using WheelDeploySpec metadata."""

    def test_direct_with_source_subdirs(self, tmp_path: Path) -> None:
        """Rsync package uses Bazel-derived source_subdirs from spec."""
        pkg_dir = tmp_path / "packages" / "cmk-ccc"
        (pkg_dir / "cmk" / "ccc").mkdir(parents=True)
        (pkg_dir / "cmk" / "ccc" / "__init__.py").write_text("# init")

        spec = _make_wheel_spec(
            package="packages/cmk-ccc",
            deploy_mode=WheelDeployMode.DIRECT,
            source_subdirs=("cmk/ccc/",),
            distribution_name="cmk-ccc",
        )
        info = _build_package_info_from_spec(spec, tmp_path)

        assert info is not None
        assert len(info.distributions) == 1
        dist = info.distributions[0]
        assert dist.distribution_name == "cmk-ccc"
        assert dist.source_subdirs == ("cmk/ccc/",)
        assert dist.top_level_packages == ("cmk",)

    def test_generated_mode(self, tmp_path: Path) -> None:
        """Generated-source packages get deploy_mode=generated with bazel_target."""
        spec = _make_wheel_spec(
            package="packages/cmk-shared-typing",
            deploy_mode=WheelDeployMode.GENERATED,
            wheel_targets=(":wheel",),
            source_subdirs=(),
            distribution_name="cmk-shared-typing",
        )
        info = _build_package_info_from_spec(spec, tmp_path)

        assert info is not None
        assert len(info.distributions) == 1
        dist = info.distributions[0]
        assert dist.deploy_mode == WheelDeployMode.GENERATED
        assert dist.bazel_target == ":wheel"
        assert dist.source_subdirs == ()

    def test_flat_file_from_spec(self, tmp_path: Path) -> None:
        """Flat file package uses source_subdirs from spec."""
        pkg_dir = tmp_path / "non-free" / "packages" / "cmk-update-agent"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cmk_update_agent.py").write_text("# agent")

        spec = _make_wheel_spec(
            package="non-free/packages/cmk-update-agent",
            deploy_mode=WheelDeployMode.DIRECT,
            source_subdirs=("cmk_update_agent.py",),
            distribution_name="cmk-update-agent",
        )
        info = _build_package_info_from_spec(spec, tmp_path)
        assert info is not None
        assert len(info.distributions) == 1
        dist = info.distributions[0]
        assert dist.distribution_name == "cmk-update-agent"
        assert dist.source_subdirs == ("cmk_update_agent.py",)
        assert dist.top_level_packages == ("cmk_update_agent",)
        assert dist.deploy_mode == WheelDeployMode.FLAT

    def test_empty_source_subdirs_returns_none(self, tmp_path: Path) -> None:
        """Rsync package with no source_subdirs returns None."""
        pkg_dir = tmp_path / "packages" / "cmk-empty"
        pkg_dir.mkdir(parents=True)

        spec = _make_wheel_spec(
            package="packages/cmk-empty",
            deploy_mode=WheelDeployMode.DIRECT,
            source_subdirs=(),
        )
        info = _build_package_info_from_spec(spec, tmp_path)
        assert info is None


# ---------------------------------------------------------------------------
# 2. .dist-info Generation Tests
# ---------------------------------------------------------------------------


class TestDistInfoGeneration:
    """Tests for PEP 376/427 compliant .dist-info generation."""

    def test_dist_info_creates_required_files(self, tmp_path: Path) -> None:
        """_generate_dist_info creates METADATA, WHEEL, RECORD, top_level.txt."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        # Create a fake deployed file
        (site_packages / "cmk").mkdir()
        test_file = site_packages / "cmk" / "foo.py"
        test_file.write_text("# test")

        _generate_dist_info(site_packages, "cmk-ccc", "1.0.0", ["cmk"], [test_file])

        dist_info_dir = site_packages / "cmk_ccc-1.0.0.dist-info"
        assert dist_info_dir.is_dir()
        assert (dist_info_dir / "METADATA").is_file()
        assert (dist_info_dir / "WHEEL").is_file()
        assert (dist_info_dir / "RECORD").is_file()
        assert (dist_info_dir / "top_level.txt").is_file()

    def test_dist_info_metadata_content(self, tmp_path: Path) -> None:
        """METADATA contains Metadata-Version, Name, and Version fields."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()

        _generate_dist_info(site_packages, "cmk-ccc", "1.0.0", ["cmk"], [])

        metadata = (site_packages / "cmk_ccc-1.0.0.dist-info" / "METADATA").read_text()
        assert "Metadata-Version: 2.1" in metadata
        assert "Name: cmk-ccc" in metadata
        assert "Version: 1.0.0" in metadata

    def test_dist_info_wheel_content(self, tmp_path: Path) -> None:
        """WHEEL file contains Generator and Root-Is-Purelib fields."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()

        _generate_dist_info(site_packages, "cmk-ccc", "1.0.0", ["cmk"], [])

        wheel_content = (site_packages / "cmk_ccc-1.0.0.dist-info" / "WHEEL").read_text()
        assert "Generator: cmk-dev-deploy" in wheel_content
        assert "Root-Is-Purelib: true" in wheel_content

    def test_dist_info_record_format(self, tmp_path: Path) -> None:
        """RECORD uses CSV with sha256=urlsafe_b64_nopadding hash and correct size."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        # Create a known-content file
        (site_packages / "cmk").mkdir()
        test_file = site_packages / "cmk" / "test_mod.py"
        content = b"print('hello')\n"
        test_file.write_bytes(content)

        _generate_dist_info(site_packages, "cmk-ccc", "1.0.0", ["cmk"], [test_file])

        record_path = site_packages / "cmk_ccc-1.0.0.dist-info" / "RECORD"
        record_text = record_path.read_text()

        # Parse CSV
        reader = csv.reader(io.StringIO(record_text))
        rows = list(reader)

        # Find the test_mod.py entry
        test_rows = [r for r in rows if "cmk/test_mod.py" in r[0]]
        assert len(test_rows) == 1
        path_field, hash_field, size_field = test_rows[0]
        assert path_field == "cmk/test_mod.py"

        # Verify hash format: sha256=<urlsafe_base64_nopadding>
        assert hash_field.startswith("sha256=")
        digest = hashlib.sha256(content).digest()
        expected_hash = "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert hash_field == expected_hash

        # Verify size
        assert size_field == str(len(content))

        # RECORD's own entry has empty hash and size
        record_rows = [r for r in rows if "RECORD" in r[0]]
        assert len(record_rows) == 1
        assert record_rows[0][1] == ""
        assert record_rows[0][2] == ""

    def test_dist_info_directory_naming(self, tmp_path: Path) -> None:
        """Distribution name dashes normalize to underscores in dir name."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()

        _generate_dist_info(site_packages, "cmk-ccc", "1.0.0", ["cmk"], [])

        # cmk-ccc -> cmk_ccc-1.0.0.dist-info
        assert (site_packages / "cmk_ccc-1.0.0.dist-info").is_dir()
        # The dashed version should NOT exist
        assert not (site_packages / "cmk-ccc-1.0.0.dist-info").exists()


# ---------------------------------------------------------------------------
# 3. Clean-Then-Deploy Tests
# ---------------------------------------------------------------------------


class TestCleanPackage:
    """Tests for _clean_package removal of dirs, files, and stale .dist-info."""

    def test_clean_removes_package_dir(self, tmp_path: Path) -> None:
        """Cleaning removes the target subdirectory tree."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        pkg_dir = site_packages / "cmk" / "ccc"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")
        (pkg_dir / "core.py").write_text("# core")

        _clean_package(site_packages, ["cmk/ccc/"], "cmk_ccc-*.dist-info")

        assert not pkg_dir.exists()

    def test_clean_removes_stale_dist_info(self, tmp_path: Path) -> None:
        """Cleaning removes both old pip-created and current .dist-info dirs."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        # Old pip-created dist-info
        old_di = site_packages / "cmk_ccc-0.5.0.dist-info"
        old_di.mkdir()
        (old_di / "METADATA").write_text("old")
        # Current dist-info
        cur_di = site_packages / "cmk_ccc-1.0.0.dist-info"
        cur_di.mkdir()
        (cur_di / "METADATA").write_text("current")

        _clean_package(site_packages, [], "cmk_ccc-*.dist-info")

        assert not old_di.exists()
        assert not cur_di.exists()

    def test_clean_handles_flat_file(self, tmp_path: Path) -> None:
        """Cleaning removes a single .py file (Category E flat file case)."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        flat_file = site_packages / "cmk_update_agent.py"
        flat_file.write_text("# update agent")

        _clean_package(site_packages, ["cmk_update_agent.py"], "cmk_update_agent-*.dist-info")

        assert not flat_file.exists()


# ---------------------------------------------------------------------------
# 4. Path-Aware Skip Logic Integration Tests (check_skip in deploy_wheels)
# ---------------------------------------------------------------------------


class TestPathAwareSkipIntegration:
    """Tests for path-aware skip logic via check_skip() in deploy_wheels."""

    def test_path_skip_unchanged_package(self, tmp_path: Path) -> None:
        """When check_skip returns should_skip=True, the package is skipped with path-context output."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        pkg_dir = repo_root / "packages" / "cmk-ccc" / "cmk" / "ccc"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")

        specs = (_make_wheel_spec(package="packages/cmk-ccc"),)

        skip_result = _make_skip_result(
            should_skip=True,
            reason="no changes in packages/cmk-ccc/cmk/ccc",
            deployer="wheel:packages/cmk-ccc",
            paths_checked=("packages/cmk-ccc/cmk/ccc/",),
        )

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                return_value=skip_result,
            ),
        ):
            result = deploy_wheels(changes=None, repo_root=repo_root, site=site)

        assert result.wheels_deployed == 0
        assert result.wheels_skipped == 1

    def test_path_skip_changed_package(self, tmp_path: Path) -> None:
        """When check_skip returns should_skip=False, the package is deployed."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        pkg_dir = repo_root / "packages" / "cmk-ccc" / "cmk" / "ccc"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")

        specs = (_make_wheel_spec(package="packages/cmk-ccc"),)

        skip_result = _make_skip_result(
            should_skip=False,
            reason="3 file(s) changed",
            deployer="wheel:packages/cmk-ccc",
            paths_checked=("packages/cmk-ccc/cmk/ccc/",),
            changed_files=("packages/cmk-ccc/cmk/ccc/foo.py",),
        )

        def fake_deploy_and_report(
            _spec: Any,
            _pkg_info: Any,
            _rr: Any,
            _sp: Any,
            _site: Any,
            _shared: Any = frozenset(),
            _file_root: Any = None,
            _dist_info_root: Any = None,
            _protected_children: Any = frozenset(),
        ) -> tuple[list[Path], float]:
            return [], 0.0

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                return_value=skip_result,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.compute_dirty_hashes",
                return_value={},
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer._deploy_and_report",
                side_effect=fake_deploy_and_report,
            ),
        ):
            result = deploy_wheels(changes=None, repo_root=repo_root, site=site)

        assert result.wheels_deployed == 1
        assert result.wheels_skipped == 0

    def test_path_skip_separate_dist_unchanged(self, tmp_path: Path) -> None:
        """Each deploy_wheel is now a single dist; skip when unchanged."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        pkg_dir = repo_root / "packages" / "cmk-livestatus-client"
        pkg_dir.mkdir(parents=True)

        specs = (
            _make_wheel_spec(
                package="packages/cmk-livestatus-client",
                source_subdirs=("cmk/livestatus_client/",),
                distribution_name="cmk-livestatus-client",
            ),
        )

        skip_results = {
            "wheel:packages/cmk-livestatus-client": _make_skip_result(
                should_skip=True,
                reason="no changes in packages/cmk-livestatus-client/cmk/livestatus_client",
                deployer="wheel:packages/cmk-livestatus-client",
                paths_checked=("packages/cmk-livestatus-client/cmk/livestatus_client/",),
            ),
        }

        def mock_check_skip(
            deployer_name: str,
            _repo_root: Any,
            _site_root: Any,
            _state: Any,
            _head: str,
        ) -> SkipResult:
            return skip_results[deployer_name]

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                side_effect=mock_check_skip,
            ),
        ):
            result = deploy_wheels(changes=None, repo_root=repo_root, site=site)

        assert result.wheels_deployed == 0
        assert result.wheels_skipped == 1

    def test_path_skip_head_fallback_note(self, tmp_path: Path, capsys: Any) -> None:
        """Fallback deployer prints 'using global check' note when skipped via HEAD fallback."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        pkg_dir = repo_root / "packages" / "cmk-ccc" / "cmk" / "ccc"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")

        specs = (_make_wheel_spec(package="packages/cmk-ccc"),)

        # HEAD fallback: paths_checked is empty, reason contains "HEAD fallback"
        skip_result = _make_skip_result(
            should_skip=True,
            reason="no changes (HEAD fallback)",
            deployer="wheel:packages/cmk-ccc",
            paths_checked=(),
        )

        # Skip messages are now verbose-level, so set verbosity to see them
        old_verbosity = output.get_verbosity()
        output.set_verbosity(1)
        try:
            with (
                patch(
                    "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                    return_value=specs,
                ),
                patch(
                    "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                    return_value=site_packages,
                ),
                patch(
                    "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                    return_value="a" * 40,
                ),
                patch(
                    "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                    return_value=skip_result,
                ),
            ):
                result = deploy_wheels(changes=None, repo_root=repo_root, site=site)
        finally:
            output.set_verbosity(old_verbosity)

        assert result.wheels_skipped == 1
        captured = capsys.readouterr()
        assert "using global check (no source paths)" in captured.out
        assert "skipped (no changes (HEAD fallback))" in captured.out


# ---------------------------------------------------------------------------
# 5. specs_for_changed_files Tests
# ---------------------------------------------------------------------------


class TestSpecsForChangedFiles:
    """Tests for specs_for_changed_files prefix matching with trailing slash protection."""

    def test_specs_for_changed_files_matching(self) -> None:
        """A changed file in packages/cmk-ccc/ matches the cmk-ccc spec."""
        specs = (
            _make_wheel_spec(package="packages/cmk-ccc", source_subdirs=("cmk/ccc/",)),
            _make_wheel_spec(package="packages/cmk-ec", source_subdirs=("cmk/ec/",)),
        )
        changed = ("packages/cmk-ccc/cmk/ccc/foo.py",)

        result = specs_for_changed_files(changed, all_specs=specs)
        assert len(result) == 1
        assert result[0].package == "packages/cmk-ccc"

    def test_specs_for_changed_files_no_match(self) -> None:
        """A file outside any spec prefix matches no specs."""
        specs = (
            _make_wheel_spec(package="packages/cmk-ccc", source_subdirs=("cmk/ccc/",)),
            _make_wheel_spec(package="packages/cmk-ec", source_subdirs=("cmk/ec/",)),
        )
        changed = ("tests/unit/foo.py",)

        result = specs_for_changed_files(changed, all_specs=specs)
        assert len(result) == 0

    def test_specs_for_changed_files_no_false_prefix(self) -> None:
        """packages/cmk-ec-stuff/ does NOT match packages/cmk-ec (trailing slash)."""
        specs = (
            _make_wheel_spec(package="packages/cmk-ec", source_subdirs=("cmk/ec/",)),
            _make_wheel_spec(package="packages/cmk-events", source_subdirs=("cmk/events/",)),
        )
        # This file is in a hypothetical cmk-ec-stuff package, NOT cmk-ec
        changed = ("packages/cmk-ec-stuff/foo.py",)

        result = specs_for_changed_files(changed, all_specs=specs)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# 6. Generated-Source (Category D) Tests
# ---------------------------------------------------------------------------


class TestGeneratedSourceCategoryD:
    """Tests for generated-source packages (cmk-shared-typing, cmc-protocols)."""

    def test_generated_source_via_build_package_info(self) -> None:
        """Category D packages produce deploy_mode='generated' with bazel_target set."""
        for pkg_path in (
            "packages/cmk-shared-typing",
            "non-free/packages/cmc-protocols",
        ):
            spec = _make_wheel_spec(
                package=pkg_path,
                deploy_mode=WheelDeployMode.GENERATED,
                wheel_targets=(":wheel",),
                source_subdirs=(),
            )
            pkg_info = _build_package_info_from_spec(spec, Path("/nonexistent"))
            assert pkg_info is not None, f"{pkg_path} returned None"
            for dist in pkg_info.distributions:
                assert dist.deploy_mode == WheelDeployMode.GENERATED, (
                    f"{pkg_path} dist {dist.distribution_name} has "
                    f"deploy_mode={dist.deploy_mode!r}, expected GENERATED"
                )
                assert dist.bazel_target != "", (
                    f"{pkg_path} dist {dist.distribution_name} has empty bazel_target"
                )
                # Generated packages have no source subdirs
                assert dist.source_subdirs == ()

    def test_build_and_extract_wheel_mocked(self, tmp_path: Path) -> None:
        """_build_and_extract_wheel calls bazel build, cquery, info, and extracts files."""
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create a fake wheel zip file
        import zipfile as zf

        wheel_path = tmp_path / "fake.whl"
        with zf.ZipFile(wheel_path, "w") as whl:
            whl.writestr("cmk/shared_typing/__init__.py", "# generated init\n")
            whl.writestr("cmk/shared_typing/models.py", "# generated models\n")
            # .dist-info entries should be SKIPPED during extraction
            whl.writestr("cmk_shared_typing-1.0.0.dist-info/METADATA", "ignored")
            whl.writestr("cmk_shared_typing-1.0.0.dist-info/RECORD", "ignored")

        call_log: list[list[str]] = []

        def mock_subprocess_run(
            cmd: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            call_log.append(cmd)
            if cmd[0] == "bazel" and cmd[1] == "build":
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if cmd[0] == "bazel" and cmd[1] == "cquery":
                return subprocess.CompletedProcess(cmd, 0, "bazel-out/fake.whl\n", "")
            if cmd[0] == "bazel" and cmd[1] == "info":
                # execution_root points to parent of wheel
                return subprocess.CompletedProcess(cmd, 0, str(tmp_path) + "\n", "")
            return subprocess.CompletedProcess(cmd, 1, "", "unknown command")

        # Rename actual wheel to match cquery output
        execution_root = tmp_path
        expected_wheel = execution_root / "bazel-out" / "fake.whl"
        expected_wheel.parent.mkdir(parents=True, exist_ok=True)
        wheel_path.rename(expected_wheel)

        with patch(
            "cmk.dev_deploy.deployers.wheel_deployer.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            extracted = _build_and_extract_wheel(
                "packages/cmk-shared-typing",
                ":wheel",
                repo_root,
                site_packages,
            )

        # Verify bazel build was called
        build_calls = [c for c in call_log if c[1] == "build"]
        assert len(build_calls) == 1
        assert "//packages/cmk-shared-typing:wheel" in build_calls[0]

        # Verify Python source files were extracted (NOT .dist-info)
        assert len(extracted) == 2
        extracted_names = {p.name for p in extracted}
        assert extracted_names == {"__init__.py", "models.py"}

        # Verify .dist-info was NOT extracted
        assert not (site_packages / "cmk_shared_typing-1.0.0.dist-info").exists()

        # Verify files actually exist on disk
        for f in extracted:
            assert f.is_file()


# ---------------------------------------------------------------------------
# 7. Parallel Deployment Tests
# ---------------------------------------------------------------------------


class TestParallelDeployment:
    """Tests for deploy_wheels ThreadPoolExecutor usage."""

    def test_deploy_wheels_uses_threadpool(self, tmp_path: Path) -> None:
        """deploy_wheels submits packages to ThreadPoolExecutor with max_workers capped at 4."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        # Create 3 package directories on disk with actual Python sources
        pkgs_and_subdirs = [
            ("packages/cmk-ccc", ("cmk/ccc/",)),
            ("packages/cmk-ec", ("cmk/ec/",)),
            ("packages/cmk-crypto", ("cmk/crypto/",)),
        ]
        for pkg, subdirs in pkgs_and_subdirs:
            subdir = subdirs[0].rstrip("/")
            pkg_dir = repo_root / pkg / subdir
            pkg_dir.mkdir(parents=True)
            (pkg_dir / "__init__.py").write_text("# init")

        specs = tuple(
            _make_wheel_spec(package=pkg, source_subdirs=subdirs)
            for pkg, subdirs in pkgs_and_subdirs
        )

        submitted_specs: list[str] = []

        def fake_deploy_and_report(
            spec: Any,
            _pkg_info: Any,
            _rr: Any,
            _sp: Any,
            _site: Any,
            _shared: Any = frozenset(),
            _file_root: Any = None,
            _dist_info_root: Any = None,
            _protected_children: Any = frozenset(),
        ) -> tuple[list[Path], float]:
            submitted_specs.append(spec.package)
            return [], 0.0

        # check_skip returns should_skip=False (deploy all)
        deploy_result = _make_skip_result(should_skip=False, reason="first deploy (no baseline)")

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                return_value=deploy_result,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.compute_dirty_hashes",
                return_value={},
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer._deploy_and_report",
                side_effect=fake_deploy_and_report,
            ),
        ):
            result = deploy_wheels(
                changes=None,
                repo_root=repo_root,
                site=site,
            )

        # All 3 packages should have been submitted
        assert len(submitted_specs) == 3
        assert set(submitted_specs) == {pkg for pkg, _ in pkgs_and_subdirs}
        assert result.wheels_deployed == 3

    def test_deploy_wheels_single_package(self, tmp_path: Path) -> None:
        """deploy_wheels works correctly with a single package."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        site = _make_site(tmp_path)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        pkg_dir = repo_root / "packages" / "cmk-ccc" / "cmk" / "ccc"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")

        specs = (_make_wheel_spec(package="packages/cmk-ccc"),)

        def fake_deploy_and_report(
            _spec: Any,
            _pkg_info: Any,
            _rr: Any,
            _sp: Any,
            _site: Any,
            _shared: Any = frozenset(),
            _file_root: Any = None,
            _dist_info_root: Any = None,
            _protected_children: Any = frozenset(),
        ) -> tuple[list[Path], float]:
            return [], 0.0

        # check_skip returns should_skip=False (deploy)
        deploy_result = _make_skip_result(should_skip=False, reason="first deploy (no baseline)")

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                return_value=deploy_result,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.compute_dirty_hashes",
                return_value={},
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer._deploy_and_report",
                side_effect=fake_deploy_and_report,
            ),
        ):
            result = deploy_wheels(
                changes=None,
                repo_root=repo_root,
                site=site,
            )

        assert result.wheels_deployed == 1
        assert result.wheels_skipped == 0

    def test_deploy_wheels_edition_filtering(self, tmp_path: Path) -> None:
        """deploy_wheels skips packages whose edition_constraint excludes site edition."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        # Use COMMUNITY edition
        site = _make_site(tmp_path, edition=Edition.COMMUNITY)
        site_packages = tmp_path / "sp"
        site_packages.mkdir()

        # cmk-ccc has no constraint (all editions), cmk-mknotifyd is pro-only
        ccc_dir = repo_root / "packages" / "cmk-ccc" / "cmk" / "ccc"
        ccc_dir.mkdir(parents=True)
        (ccc_dir / "__init__.py").write_text("# init")
        mknotifyd_dir = repo_root / "non-free" / "packages" / "cmk-mknotifyd" / "cmk" / "mknotifyd"
        mknotifyd_dir.mkdir(parents=True)
        (mknotifyd_dir / "__init__.py").write_text("# init")

        specs = (
            _make_wheel_spec(
                package="packages/cmk-ccc",
                edition_constraint=None,
                source_subdirs=("cmk/ccc/",),
            ),
            _make_wheel_spec(
                package="non-free/packages/cmk-mknotifyd",
                edition_constraint=frozenset({"pro", "ultimate", "ultimatemt", "cloud"}),
                source_subdirs=("cmk/mknotifyd/",),
            ),
        )

        def fake_deploy_and_report(
            _spec: Any,
            _pkg_info: Any,
            _rr: Any,
            _sp: Any,
            _site: Any,
            _shared: Any = frozenset(),
            _file_root: Any = None,
            _dist_info_root: Any = None,
            _protected_children: Any = frozenset(),
        ) -> tuple[list[Path], float]:
            return [], 0.0

        # check_skip returns should_skip=False (deploy)
        deploy_result = _make_skip_result(should_skip=False, reason="first deploy (no baseline)")

        with (
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_wheel_specs",
                return_value=specs,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_site_packages",
                return_value=site_packages,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.get_head_commit",
                return_value="a" * 40,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.check_skip",
                return_value=deploy_result,
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer.compute_dirty_hashes",
                return_value={},
            ),
            patch(
                "cmk.dev_deploy.deployers.wheel_deployer._deploy_and_report",
                side_effect=fake_deploy_and_report,
            ),
        ):
            result = deploy_wheels(
                changes=None,
                repo_root=repo_root,
                site=site,
            )

        assert result.wheels_deployed == 1
        assert result.wheels_skipped_edition == 1


# ---------------------------------------------------------------------------
# 9. Parent-Child Subdir Helpers
# ---------------------------------------------------------------------------


class TestSubdirsOverlap:
    """Tests for _subdirs_overlap parent-child detection."""

    def test_exact_match(self) -> None:
        assert _subdirs_overlap(["cmk/ccc/"], ["cmk/ccc/"])

    def test_parent_child(self) -> None:
        assert _subdirs_overlap(["cmk/licensing/"], ["cmk/licensing/nonfree/"])

    def test_child_parent(self) -> None:
        assert _subdirs_overlap(["cmk/licensing/nonfree/"], ["cmk/licensing/"])

    def test_disjoint(self) -> None:
        assert not _subdirs_overlap(["cmk/ccc/"], ["cmk/ec/"])

    def test_partial_name_no_match(self) -> None:
        """cmk/ec/ must not match cmk/ec-stuff/ (not a true parent)."""
        assert not _subdirs_overlap(["cmk/ec/"], ["cmk/ec-stuff/"])

    def test_empty(self) -> None:
        assert not _subdirs_overlap([], ["cmk/ccc/"])
        assert not _subdirs_overlap(["cmk/ccc/"], [])


class TestComputeProtectedChildren:
    """Tests for _compute_protected_children mapping."""

    def test_licensing_pair(self) -> None:
        community = _make_wheel_spec(
            package="packages/cmk-licensing",
            source_subdirs=("cmk/licensing/",),
        )
        nonfree = _make_wheel_spec(
            package="non-free/packages/cmk-licensing-nonfree",
            source_subdirs=("cmk/licensing/nonfree/",),
        )
        result = _compute_protected_children([community, nonfree])
        # The community package should protect the nonfree subdir
        assert result["packages/cmk-licensing"] == frozenset({"cmk/licensing/nonfree/"})
        # The nonfree package has no children to protect
        assert "non-free/packages/cmk-licensing-nonfree" not in result

    def test_no_overlap(self) -> None:
        a = _make_wheel_spec(package="packages/cmk-ccc", source_subdirs=("cmk/ccc/",))
        b = _make_wheel_spec(package="packages/cmk-ec", source_subdirs=("cmk/ec/",))
        result = _compute_protected_children([a, b])
        assert result == {}


class TestExpandCoDependentsParentChild:
    """Tests for _expand_co_dependents with parent-child subdir relationships."""

    def test_parent_triggers_child(self) -> None:
        """Redeploying cmk-licensing must also include cmk-licensing-nonfree."""
        community = _make_wheel_spec(
            package="packages/cmk-licensing",
            source_subdirs=("cmk/licensing/",),
        )
        nonfree = _make_wheel_spec(
            package="non-free/packages/cmk-licensing-nonfree",
            source_subdirs=("cmk/licensing/nonfree/",),
        )
        all_specs = (community, nonfree)
        candidates = (community,)

        result = _expand_co_dependents(candidates, all_specs)
        packages = {s.package for s in result}
        assert packages == {community.package, nonfree.package}

    def test_child_triggers_parent(self) -> None:
        """Redeploying cmk-licensing-nonfree must also include cmk-licensing."""
        community = _make_wheel_spec(
            package="packages/cmk-licensing",
            source_subdirs=("cmk/licensing/",),
        )
        nonfree = _make_wheel_spec(
            package="non-free/packages/cmk-licensing-nonfree",
            source_subdirs=("cmk/licensing/nonfree/",),
        )
        all_specs = (community, nonfree)
        candidates = (nonfree,)

        result = _expand_co_dependents(candidates, all_specs)
        packages = {s.package for s in result}
        assert packages == {community.package, nonfree.package}

    def test_disjoint_no_expansion(self) -> None:
        """Packages with disjoint subdirs are not expanded."""
        a = _make_wheel_spec(package="packages/cmk-ccc", source_subdirs=("cmk/ccc/",))
        b = _make_wheel_spec(package="packages/cmk-ec", source_subdirs=("cmk/ec/",))
        all_specs = (a, b)
        candidates = (a,)

        result = _expand_co_dependents(candidates, all_specs)
        assert len(result) == 1
        assert result[0].package == "packages/cmk-ccc"


class TestSelectiveRmtree:
    """Tests for _selective_rmtree preserving protected subtrees."""

    def test_preserves_protected_subtree(self, tmp_path: Path) -> None:
        """Files in protected subtrees survive, others are removed."""
        root = tmp_path / "cmk" / "licensing"
        root.mkdir(parents=True)
        (root / "__init__.py").write_text("# init")
        (root / "handler.py").write_text("# handler")
        nonfree = root / "nonfree"
        nonfree.mkdir()
        (nonfree / "__init__.py").write_text("# nf init")
        (nonfree / "settings.py").write_text("# settings")

        _selective_rmtree(root, {nonfree})

        # Protected subtree survives
        assert nonfree.exists()
        assert (nonfree / "__init__.py").exists()
        assert (nonfree / "settings.py").exists()
        # Non-protected files are removed
        assert not (root / "__init__.py").exists()
        assert not (root / "handler.py").exists()

    def test_removes_everything_without_protection(self, tmp_path: Path) -> None:
        root = tmp_path / "pkg"
        root.mkdir()
        (root / "a.py").write_text("a")
        sub = root / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("b")

        _selective_rmtree(root, set())

        assert root.exists()  # root itself is not removed
        assert list(root.iterdir()) == []


class TestCleanPackageProtectedChildren:
    """Tests for _clean_package with protected_children parameter."""

    def test_clean_preserves_nonfree_subdir(self, tmp_path: Path) -> None:
        """rmtree on cmk/licensing/ preserves cmk/licensing/nonfree/."""
        site_packages = tmp_path / "site-packages"
        licensing = site_packages / "cmk" / "licensing"
        licensing.mkdir(parents=True)
        (licensing / "__init__.py").write_text("# init")
        nonfree = licensing / "nonfree"
        nonfree.mkdir()
        (nonfree / "__init__.py").write_text("# nf init")
        (nonfree / "settings.py").write_text("# settings")

        _clean_package(
            site_packages,
            ["cmk/licensing/"],
            "cmk_licensing-*.dist-info",
            protected_children=frozenset({"cmk/licensing/nonfree/"}),
        )

        # Protected child survives
        assert nonfree.exists()
        assert (nonfree / "settings.py").exists()
        # Parent's own files are removed
        assert not (licensing / "__init__.py").exists()

    def test_clean_without_protection_removes_all(self, tmp_path: Path) -> None:
        """Without protected_children, rmtree removes everything as before."""
        site_packages = tmp_path / "site-packages"
        licensing = site_packages / "cmk" / "licensing"
        licensing.mkdir(parents=True)
        (licensing / "__init__.py").write_text("# init")
        nonfree = licensing / "nonfree"
        nonfree.mkdir()
        (nonfree / "settings.py").write_text("# settings")

        _clean_package(
            site_packages,
            ["cmk/licensing/"],
            "cmk_licensing-*.dist-info",
        )

        assert not licensing.exists()
