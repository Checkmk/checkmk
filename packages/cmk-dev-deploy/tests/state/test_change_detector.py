# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.change_detector (git diff, file categorization)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cmk.dev_deploy.errors import ChangeDetectionError, DeployError
from cmk.dev_deploy.state.change_detector import (
    _STRUCTURAL_RULES,
    categorize_file,
    detect_changes,
)
from cmk.dev_deploy.types import CategorizationRule, ChangeCategory, ChangeSet


@pytest.fixture(autouse=True)
def _inject_computed_rules() -> None:
    """Inject categorization rules computed from checked-in data.

    Uses the real _compute_categorization_rules() pipeline with:
    - Install specs from deploy_specs.toml (checked in)
    - Supplementary rules from deploy_specs.toml (checked in)
    - Representative wheel/config specs for tested paths
    - _TEST_INSTALL_SPEC_EXTENSIONS from conftest (the only test constant)

    This does NOT depend on deploy_manifest.json (gitignored).
    """
    import cmk.dev_deploy.state.change_detector as _cd
    from cmk.dev_deploy.manifest.reader import get_categorization_rules

    # get_categorization_rules reads from the manifest cache, which is either
    # the real manifest (local dev) or the seed manifest (CI).  Both have
    # categorization_rules computed by the real pipeline (see conftest.py).
    manifest_rules = get_categorization_rules()
    _cd._cached_rules = _cd._STRUCTURAL_RULES + manifest_rules  # noqa: SLF001


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_run(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> object:
    """Create a callable that returns a mock CompletedProcess."""

    def _mock_run(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return _mock_run


# ---------------------------------------------------------------------------
# ChangeCategory enum tests
# ---------------------------------------------------------------------------


class TestChangeCategory:
    """Tests for the ChangeCategory enum."""

    def test_has_10_members(self) -> None:
        """ChangeCategory has exactly 10 members."""
        assert len(ChangeCategory) == 10

    def test_all_members_present(self) -> None:
        """All expected members exist."""
        expected = {
            "PYTHON",
            "CPP",
            "RUST",
            "VUE",
            "FRONTEND",
            "CONFIG",
            "DATA",
            "BUILD",
            "TEST",
            "OTHER",
        }
        assert {m.name for m in ChangeCategory} == expected

    def test_string_values(self) -> None:
        """ChangeCategory values are lowercase strings matching Edition pattern."""
        assert ChangeCategory.PYTHON.value == "python"
        assert ChangeCategory.CPP.value == "cpp"
        assert ChangeCategory.OTHER.value == "other"


# ---------------------------------------------------------------------------
# ChangeSet dataclass tests
# ---------------------------------------------------------------------------


class TestChangeSet:
    """Tests for the ChangeSet dataclass."""

    def test_is_empty_true_for_no_files(self) -> None:
        """is_empty returns True when files tuple is empty."""
        cs = ChangeSet(build_commit="a" * 40, files=(), categories={})
        assert cs.is_empty is True

    def test_is_empty_false_for_files(self) -> None:
        """is_empty returns False when files tuple is non-empty."""
        cs = ChangeSet(
            build_commit="a" * 40,
            files=("cmk/foo.py",),
            categories={ChangeCategory.PYTHON: ("cmk/foo.py",)},
        )
        assert cs.is_empty is False

    def test_has_python_only_true_when_only_python(self) -> None:
        """has_python_only True when only deployable category is PYTHON."""
        cs = ChangeSet(
            build_commit="a" * 40,
            files=("cmk/foo.py", "tests/test_x.py"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.TEST: ("tests/test_x.py",),
            },
        )
        assert cs.has_python_only is True

    def test_has_python_only_false_when_cpp_present(self) -> None:
        """has_python_only False when CPP category is present."""
        cs = ChangeSet(
            build_commit="a" * 40,
            files=("cmk/foo.py", "packages/livestatus/src/Query.cc"),
            categories={
                ChangeCategory.PYTHON: ("cmk/foo.py",),
                ChangeCategory.CPP: ("packages/livestatus/src/Query.cc",),
            },
        )
        assert cs.has_python_only is False

    def test_has_python_only_true_when_only_non_deployable(self) -> None:
        """has_python_only True when only TEST/OTHER/BUILD categories (no deployable)."""
        cs = ChangeSet(
            build_commit="a" * 40,
            files=("tests/test_x.py", "README.md"),
            categories={
                ChangeCategory.TEST: ("tests/test_x.py",),
                ChangeCategory.OTHER: ("README.md",),
            },
        )
        assert cs.has_python_only is True

    def test_frozen(self) -> None:
        """ChangeSet is frozen (immutable)."""
        cs = ChangeSet(build_commit="a" * 40, files=(), categories={})
        with pytest.raises(AttributeError):
            cs.build_commit = "b" * 40  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ChangeDetectionError tests
# ---------------------------------------------------------------------------


class TestChangeDetectionError:
    """Tests for the ChangeDetectionError exception."""

    def test_is_subclass_of_deploy_error(self) -> None:
        """ChangeDetectionError is a subclass of DeployError."""
        assert issubclass(ChangeDetectionError, DeployError)

    def test_has_recovery_attribute(self) -> None:
        """ChangeDetectionError carries recovery attribute from DeployError."""
        err = ChangeDetectionError("bad commit", recovery="try git fetch")
        assert err.message == "bad commit"
        assert err.recovery == "try git fetch"

    def test_str_includes_recovery(self) -> None:
        """str(error) includes both message and recovery."""
        err = ChangeDetectionError("bad commit", recovery="try git fetch")
        assert "bad commit" in str(err)
        assert "try git fetch" in str(err)


# ---------------------------------------------------------------------------
# categorize_file tests
# ---------------------------------------------------------------------------


class TestCategorizeFile:
    """Tests for the categorize_file function."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            # Python fast path
            ("cmk/gui/views.py", ChangeCategory.PYTHON),
            ("cmk/gui/__init__.py", ChangeCategory.PYTHON),
            ("cmk/gui/bi/_compiler.py", ChangeCategory.PYTHON),
            # cmk/ non-py files -> OTHER
            ("cmk/utils/README.md", ChangeCategory.OTHER),
            # C++
            ("packages/livestatus/src/Query.cc", ChangeCategory.CPP),
            ("packages/neb/src/module.cc", ChangeCategory.CPP),
            ("packages/unixcat/src/unixcat.cc", ChangeCategory.CPP),
            # Rust
            ("packages/check-cert/src/main.rs", ChangeCategory.RUST),
            ("packages/check-http/src/main.rs", ChangeCategory.RUST),
            ("packages/cmk-agent-ctl/src/main.rs", ChangeCategory.RUST),
            ("packages/mk-oracle/src/main.rs", ChangeCategory.RUST),
            ("packages/mk-sql/src/main.rs", ChangeCategory.RUST),
            # Vue
            ("packages/cmk-frontend-vue/src/App.vue", ChangeCategory.VUE),
            ("packages/cmk-frontend-vue/src/main.ts", ChangeCategory.VUE),
            ("packages/cmk-shared-typing/src/types.ts", ChangeCategory.VUE),
            # Frontend (legacy)
            ("packages/cmk-frontend/scss/main.scss", ChangeCategory.FRONTEND),
            ("packages/cmk-frontend/src/main.js", ChangeCategory.FRONTEND),
            ("packages/cmk-frontend/src/js/modules/graphs.ts", ChangeCategory.FRONTEND),
            # Config
            ("agents/plugins/my_agent", ChangeCategory.CONFIG),
            ("notifications/slack", ChangeCategory.CONFIG),
            ("active_checks/check_http", ChangeCategory.CONFIG),
            ("omd/packages/redis/redis.make", ChangeCategory.CONFIG),
            # Data
            ("locale/de/LC_MESSAGES/multisite.mo", ChangeCategory.DATA),
            ("doc/plugin-api/index.html", ChangeCategory.DATA),
            # Tests (NOT Python, despite .py extension)
            ("tests/unit/test_foo.py", ChangeCategory.TEST),
            ("tests/integration/test_bar.py", ChangeCategory.TEST),
            # Build
            ("MODULE.bazel", ChangeCategory.BUILD),
            ("bazel/deps.bzl", ChangeCategory.BUILD),
            # Python packages (.py under packages/ and non-free/packages/)
            ("packages/cmk-ccc/cmk/ccc/version.py", ChangeCategory.PYTHON),
            ("non-free/packages/cmk-bakery/cmk/bakery/foo.py", ChangeCategory.PYTHON),
            # OTHER (no prefix match)
            ("README.md", ChangeCategory.OTHER),
        ],
    )
    def test_categorize_file(self, path: str, expected: ChangeCategory) -> None:
        """categorize_file correctly classifies various path patterns."""
        assert categorize_file(path) == expected

    def test_tests_prefix_takes_priority_over_py_extension(self) -> None:
        """tests/ prefix matches before .py extension would trigger PYTHON."""
        result = categorize_file("tests/unit/cmk/gui/test_views.py")
        assert result == ChangeCategory.TEST


# ---------------------------------------------------------------------------
# detect_changes tests
# ---------------------------------------------------------------------------


class TestDetectChanges:
    """Tests for the detect_changes function."""

    def test_returns_none_for_none_build_commit(self, tmp_path: Path) -> None:
        """detect_changes returns None when build_commit is None."""
        result = detect_changes(None, tmp_path)
        assert result is None

    def test_raises_for_invalid_commit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """detect_changes raises ChangeDetectionError for invalid commit hash."""
        # Mock git cat-file to return failure (invalid commit)
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_mock_run(returncode=128, stderr="fatal: bad object deadbeef"),
        )

        with pytest.raises(ChangeDetectionError, match="not found"):
            detect_changes("deadbeef" * 5, tmp_path)

    def test_returns_empty_changeset_for_no_changes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """detect_changes returns empty ChangeSet when git diff produces no output."""
        call_count = {"n": 0}

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            call_count["n"] += 1
            if "cat-file" in cmd:
                # Validate commit succeeds
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            # git diff returns empty output
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        commit = "a" * 40
        result = detect_changes(commit, tmp_path)

        assert result is not None
        assert result.is_empty is True
        assert result.files == ()
        assert result.categories == {}
        assert result.build_commit == commit

    def test_returns_categorized_changeset(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """detect_changes returns ChangeSet with categorized files when changes exist."""

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if "cat-file" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            # git diff returns two files
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="cmk/gui/views.py\ntests/unit/test_foo.py\n",
                stderr="",
            )

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        commit = "a" * 40
        result = detect_changes(commit, tmp_path)

        assert result is not None
        assert result.is_empty is False
        assert len(result.files) == 2
        assert "cmk/gui/views.py" in result.files
        assert "tests/unit/test_foo.py" in result.files
        assert ChangeCategory.PYTHON in result.categories
        assert ChangeCategory.TEST in result.categories
        assert result.categories[ChangeCategory.PYTHON] == ("cmk/gui/views.py",)
        assert result.categories[ChangeCategory.TEST] == ("tests/unit/test_foo.py",)

    def test_git_diff_failure_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """detect_changes raises ChangeDetectionError when git diff fails."""

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if "cat-file" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            # git diff fails
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stderr="fatal: error", stdout=""
            )

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        with pytest.raises(ChangeDetectionError, match="git diff failed"):
            detect_changes("a" * 40, tmp_path)

    def test_cat_file_returns_non_commit_type(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """detect_changes raises when git cat-file returns a non-commit type (e.g. 'blob')."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_mock_run(returncode=0, stdout="blob\n"),
        )

        with pytest.raises(ChangeDetectionError, match="not found"):
            detect_changes("a" * 40, tmp_path)

    def test_files_are_sorted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """detect_changes returns files in sorted order."""

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if "cat-file" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="cmk/z.py\ncmk/a.py\ncmk/m.py\n",
                stderr="",
            )

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        result = detect_changes("a" * 40, tmp_path)
        assert result is not None
        assert result.files == ("cmk/a.py", "cmk/m.py", "cmk/z.py")

    def test_empty_lines_in_diff_output_filtered(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Empty lines in git diff output are filtered out."""

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if "cat-file" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="\ncmk/foo.py\n\n\n",
                stderr="",
            )

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        result = detect_changes("a" * 40, tmp_path)
        assert result is not None
        assert result.files == ("cmk/foo.py",)


# ---------------------------------------------------------------------------
# CATEGORIZATION_RULES tests
# ---------------------------------------------------------------------------


class TestCategorizationRules:
    """Tests for the structural categorization rules."""

    def test_structural_rules_is_tuple(self) -> None:
        """_STRUCTURAL_RULES is a tuple of CategorizationRule instances."""
        assert isinstance(_STRUCTURAL_RULES, tuple)
        assert len(_STRUCTURAL_RULES) == 3  # TEST, BUILD (MODULE.bazel), BUILD (bazel/)

    def test_each_structural_rule_is_categorization_rule(self) -> None:
        """Each structural rule is a CategorizationRule dataclass."""
        for rule in _STRUCTURAL_RULES:
            assert isinstance(rule, CategorizationRule)
            assert isinstance(rule.prefix, str)
            assert rule.extensions is None or isinstance(rule.extensions, frozenset)
            assert isinstance(rule.category, ChangeCategory)

    def test_structural_rules_cover_tests_and_build(self) -> None:
        """Structural rules cover TEST and BUILD categories."""
        categories = {rule.category for rule in _STRUCTURAL_RULES}
        assert ChangeCategory.TEST in categories
        assert ChangeCategory.BUILD in categories


class TestCategorizationRegression:
    """Regression tests ensuring manifest-derived rules match prior hardcoded behavior.

    These test paths represent every package that was in the original
    _CATEGORIZATION_RULES constant. If any rule is accidentally dropped
    (e.g., a supplementary rule removed), these tests catch it.
    """

    @pytest.mark.parametrize(
        "path,expected",
        [
            # Python fast path
            ("cmk/gui/views.py", ChangeCategory.PYTHON),
            ("cmk/base/config.py", ChangeCategory.PYTHON),
            # C++
            ("packages/livestatus/src/Query.cc", ChangeCategory.CPP),
            ("packages/neb/src/module.cc", ChangeCategory.CPP),
            ("packages/unixcat/src/unixcat.cc", ChangeCategory.CPP),
            ("non-free/packages/cmc/src/cmc.cc", ChangeCategory.CPP),
            ("non-free/packages/cmc/src/config.proto", ChangeCategory.CPP),
            # Rust (including supplementary packages)
            ("packages/check-cert/src/main.rs", ChangeCategory.RUST),
            ("packages/check-http/src/main.rs", ChangeCategory.RUST),
            ("packages/cmk-agent-ctl/src/main.rs", ChangeCategory.RUST),
            ("packages/mk-oracle/src/main.rs", ChangeCategory.RUST),
            ("packages/mk-sql/src/main.rs", ChangeCategory.RUST),
            # Vue
            ("packages/cmk-frontend-vue/src/App.vue", ChangeCategory.VUE),
            ("packages/cmk-frontend-vue/src/main.ts", ChangeCategory.VUE),
            ("packages/cmk-shared-typing/src/types.ts", ChangeCategory.VUE),
            # Frontend (includes .ts -- the motivating bug fix)
            ("packages/cmk-frontend/scss/main.scss", ChangeCategory.FRONTEND),
            ("packages/cmk-frontend/src/main.js", ChangeCategory.FRONTEND),
            ("packages/cmk-frontend/src/js/modules/graphs.ts", ChangeCategory.FRONTEND),
            # Python packages (specific and catch-all)
            ("packages/cmk-ccc/cmk/ccc/version.py", ChangeCategory.PYTHON),
            ("non-free/packages/cmk-bakery/cmk/bakery/foo.py", ChangeCategory.PYTHON),
            # Catch-all packages/ for packages without their own wheel spec
            ("packages/cmk-dev-deploy/cmk/dev_deploy/foo.py", ChangeCategory.PYTHON),
            ("non-free/packages/some-unknown/lib.py", ChangeCategory.PYTHON),
            # Config
            ("agents/plugins/my_agent", ChangeCategory.CONFIG),
            ("notifications/slack", ChangeCategory.CONFIG),
            ("active_checks/check_http", ChangeCategory.CONFIG),
            ("omd/packages/redis/redis.make", ChangeCategory.CONFIG),
            # Data
            ("locale/de/LC_MESSAGES/multisite.mo", ChangeCategory.DATA),
            ("doc/plugin-api/index.html", ChangeCategory.DATA),
            # Tests
            ("tests/unit/test_foo.py", ChangeCategory.TEST),
            # Build
            ("MODULE.bazel", ChangeCategory.BUILD),
            ("bazel/deps.bzl", ChangeCategory.BUILD),
            # OTHER
            ("README.md", ChangeCategory.OTHER),
        ],
    )
    def test_regression(self, path: str, expected: ChangeCategory) -> None:
        """Ensure categorize_file produces the same result as the old hardcoded rules."""
        assert categorize_file(path) == expected
