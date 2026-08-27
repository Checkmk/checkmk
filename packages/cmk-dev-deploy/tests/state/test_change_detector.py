# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.change_detector (git diff, file categorization)."""

import subprocess
from pathlib import Path

import pytest

from cmk.dev_deploy.errors import ChangeDetectionError, DeployError
from cmk.dev_deploy.state.change_detector import (
    _STRUCTURAL_RULES,
    categorize_file,
    detect_changes,
    filter_stale_dirty,
)
from cmk.dev_deploy.state.deploy_state import compute_file_hash, DeployerState, DeployState
from cmk.dev_deploy.types import CategorizationRule, ChangeCategory, ChangeSet, DiffBaseSource


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

    def test_has_11_members(self) -> None:
        """ChangeCategory has exactly 11 members."""
        assert len(ChangeCategory) == 11

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
            "IGNORED",
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
        """has_python_only True when only TEST/OTHER/BUILD/IGNORED categories (no deployable)."""
        cs = ChangeSet(
            build_commit="a" * 40,
            files=("tests/test_x.py", "README.md", "werks/12345"),
            categories={
                ChangeCategory.TEST: ("tests/test_x.py",),
                ChangeCategory.OTHER: ("README.md",),
                ChangeCategory.IGNORED: ("werks/12345",),
            },
        )
        assert cs.has_python_only is True


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
            ("packages/cmk-frontend/src/js/modules/popup_menu.ts", ChangeCategory.FRONTEND),
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
            # The deploy tool itself is never deployed to a site
            ("packages/cmk-dev-deploy/cmk/dev_deploy/site/sudoers.py", ChangeCategory.IGNORED),
            ("packages/cmk-dev-deploy/tests/site/test_sudoers.py", ChangeCategory.IGNORED),
            ("packages/cmk-dev-deploy/README.md", ChangeCategory.IGNORED),
            # Build (prefix-based)
            ("MODULE.bazel", ChangeCategory.BUILD),
            ("bazel/deps.bzl", ChangeCategory.BUILD),
            # Build (basename-based, anywhere in the tree)
            ("packages/cmk-foo/BUILD", ChangeCategory.BUILD),
            ("omd/packages/Python/BUILD", ChangeCategory.BUILD),
            ("omd/packages/Python/BUILD.Python.bazel", ChangeCategory.BUILD),
            ("omd/packages/freetds/patches/0001-foo.patch", ChangeCategory.BUILD),
            ("omd/packages/heirloom-pkgtools/patches/0012-fix.dif", ChangeCategory.BUILD),
            ("agents/Makefile", ChangeCategory.BUILD),
            ("agents/check-mk-agent.spec", ChangeCategory.BUILD),
            ("agents/wnx/install/Product.wxs", ChangeCategory.BUILD),
            ("omd/packages/perl-modules/perl-modules_http.bzl", ChangeCategory.BUILD),
            # Ignored (explicitly non-deployable structural prefixes)
            ("werks/12345", ChangeCategory.IGNORED),
            (".werks/12345", ChangeCategory.IGNORED),
            (".github/workflows/ci.yml", ChangeCategory.IGNORED),
            (".devcontainer/devcontainer.json", ChangeCategory.IGNORED),
            (".aspect/cli/config.yaml", ChangeCategory.IGNORED),
            (".claude/agents/architect.agent.md", ChangeCategory.IGNORED),
            (".ide/vscode/package.json", ChangeCategory.IGNORED),
            (".pre-commit-scripts/check-licence", ChangeCategory.IGNORED),
            ("docs/architecture.md", ChangeCategory.IGNORED),
            ("buildscripts/scripts/test-gerrit.groovy", ChangeCategory.IGNORED),
            ("component_owners/saas_dev/OWNERS_DEFINITION", ChangeCategory.IGNORED),
            ("docker_image/Dockerfile", ChangeCategory.IGNORED),
            ("doc/treasures/migration_helpers/legacy_checks/to_v2.py", ChangeCategory.IGNORED),
            ("omd/dependency_management/generate_bom_csv.py", ChangeCategory.IGNORED),
            ("scripts/find-python-files", ChangeCategory.IGNORED),
            # Python packages (.py under packages/ and non-free/packages/)
            ("packages/cmk-ccc/cmk/ccc/version.py", ChangeCategory.PYTHON),
            ("non-free/packages/cmk-bakery/cmk/bakery/foo.py", ChangeCategory.PYTHON),
            # OTHER (no prefix match).
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

    def test_missing_site_build_commit_message(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A missing site build commit suggests fetching; --full cannot skip it."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_mock_run(returncode=128, stderr="fatal: bad object"),
        )

        with pytest.raises(ChangeDetectionError) as excinfo:
            detect_changes("d" * 40, tmp_path)

        assert "Site build commit" in excinfo.value.message
        assert excinfo.value.recovery is not None
        assert "git fetch origin" in excinfo.value.recovery
        assert "even with --full" in excinfo.value.recovery

    def test_missing_state_commit_message(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A missing deploy state commit names the state and suggests --full."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_mock_run(returncode=128, stderr="fatal: bad object"),
        )

        with pytest.raises(ChangeDetectionError) as excinfo:
            detect_changes("d" * 40, tmp_path, diff_base_source=DiffBaseSource.STATE)

        assert "Deploy state commit" in excinfo.value.message
        assert excinfo.value.recovery is not None
        assert "cmk-dev-deploy --full" in excinfo.value.recovery

    def test_missing_target_commit_names_ref(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A missing --commit ref is reported as such, not as the site build commit."""
        build_commit = "a" * 40

        def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if cmd[-1] == build_commit:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="commit\n", stderr=""
                )
            return subprocess.CompletedProcess(
                args=cmd, returncode=128, stdout="", stderr="fatal: bad object"
            )

        monkeypatch.setattr("cmk.dev_deploy.state.change_detector.subprocess.run", _mock_run)

        with pytest.raises(ChangeDetectionError) as excinfo:
            detect_changes(build_commit, tmp_path, target_commit="no-such-branch")

        assert "--commit ref 'no-such-branch'" in excinfo.value.message

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
        # 1 TEST + 2 BUILD + 16 IGNORED
        assert len(_STRUCTURAL_RULES) == 19

    def test_each_structural_rule_is_categorization_rule(self) -> None:
        """Each structural rule is a CategorizationRule dataclass."""
        for rule in _STRUCTURAL_RULES:
            assert isinstance(rule, CategorizationRule)
            assert isinstance(rule.prefix, str)
            assert rule.extensions is None or isinstance(rule.extensions, frozenset)
            assert isinstance(rule.category, ChangeCategory)

    def test_structural_rules_cover_tests_build_and_ignored(self) -> None:
        """Structural rules cover TEST, BUILD, and IGNORED categories."""
        categories = {rule.category for rule in _STRUCTURAL_RULES}
        assert ChangeCategory.TEST in categories
        assert ChangeCategory.BUILD in categories
        assert ChangeCategory.IGNORED in categories


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
            ("packages/cmk-frontend/src/js/modules/popup_menu.ts", ChangeCategory.FRONTEND),
            # Python packages (specific and catch-all)
            ("packages/cmk-ccc/cmk/ccc/version.py", ChangeCategory.PYTHON),
            ("non-free/packages/cmk-bakery/cmk/bakery/foo.py", ChangeCategory.PYTHON),
            # Catch-all packages/ for packages without their own wheel spec
            ("packages/cmk-dev-deploy/cmk/dev_deploy/foo.py", ChangeCategory.IGNORED),
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


# ---------------------------------------------------------------------------
# Untracked file handling
# ---------------------------------------------------------------------------


_UNTRACKED = "cmk.dev_deploy.state.change_detector.get_untracked_files"
_NEW_FILE = "packages/cmk-frontend-vue/src/check-ai/CheckAiApp.vue"


def _make_diff_mock(diff_stdout: str) -> object:
    """Mock git: resolve any commit, return *diff_stdout* for the file diff."""

    def _mock_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "cat-file" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="commit\n", stderr="")
        stdout = "" if "--diff-filter=D" in cmd else diff_stdout
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout, stderr="")

    return _mock_run


class TestUntrackedChanges:
    """detect_changes() must see files that were never ``git add``-ed.

    Regression: untracked files are invisible to every form of ``git diff``,
    so a new feature directory produced no changeset entry, no Bazel target,
    and no deploy -- while Bazel itself globbed and built those same files
    whenever an unrelated tracked file happened to change.
    """

    def test_untracked_file_enters_changeset(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A new file shows up in files and is recorded as untracked."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_diff_mock("cmk/gui/existing.py\n"),
        )
        monkeypatch.setattr(_UNTRACKED, lambda _repo: [_NEW_FILE])

        result = detect_changes("a" * 40, tmp_path)

        assert result is not None
        assert result.files == ("cmk/gui/existing.py", _NEW_FILE)
        assert result.untracked == (_NEW_FILE,)

    def test_untracked_file_is_categorized(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The new file lands in a category, so Bazel target resolution sees it."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run", _make_diff_mock("")
        )
        monkeypatch.setattr(_UNTRACKED, lambda _repo: [_NEW_FILE])

        result = detect_changes("a" * 40, tmp_path)

        assert result is not None
        assert any(_NEW_FILE in paths for paths in result.categories.values())

    def test_untracked_only_still_yields_changes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """New files alone are enough to make the changeset non-empty."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run", _make_diff_mock("")
        )
        monkeypatch.setattr(_UNTRACKED, lambda _repo: [_NEW_FILE])

        result = detect_changes("a" * 40, tmp_path)

        assert result is not None
        assert result.is_empty is False

    def test_commit_to_commit_diff_excludes_untracked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """--commit <ref> compares two commits; the working tree is not involved."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_diff_mock("cmk/gui/existing.py\n"),
        )
        monkeypatch.setattr(
            _UNTRACKED,
            lambda _repo: pytest.fail("untracked files must not leak into a commit-to-commit diff"),
        )

        result = detect_changes("a" * 40, tmp_path, target_commit="b" * 40)

        assert result is not None
        assert result.files == ("cmk/gui/existing.py",)
        assert result.untracked == ()

    def test_no_duplicate_when_git_reports_path_twice(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A path in both the diff and the untracked list appears once."""
        monkeypatch.setattr(
            "cmk.dev_deploy.state.change_detector.subprocess.run",
            _make_diff_mock(f"{_NEW_FILE}\n"),
        )
        monkeypatch.setattr(_UNTRACKED, lambda _repo: [_NEW_FILE])

        result = detect_changes("a" * 40, tmp_path)

        assert result is not None
        assert result.files == (_NEW_FILE,)


class TestFilterStaleDirty:
    """filter_stale_dirty() drops already-deployed dirty files."""

    def _state(self, dirty: dict[str, str]) -> DeployState:
        return DeployState(
            deployers={
                "install_spec": DeployerState(
                    deployer="install_spec",
                    git_commit="a" * 40,
                    dirty_file_hashes=dirty,
                    deployed_at=1.0,
                )
            }
        )

    def test_unchanged_untracked_file_is_filtered(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An untracked file already deployed at this content is not new work.

        Without this the file would stay in the changeset forever, forcing a
        Bazel build on every single run.
        """
        (tmp_path / "new.vue").write_text("content")
        known_hash = compute_file_hash(tmp_path / "new.vue")
        monkeypatch.setattr(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files", lambda _repo: ["new.vue"]
        )

        changes = ChangeSet(
            build_commit="a" * 40,
            files=("new.vue",),
            categories={ChangeCategory.VUE: ("new.vue",)},
            untracked=("new.vue",),
        )
        result = filter_stale_dirty(changes, self._state({"new.vue": known_hash}), tmp_path)

        assert result.files == ()
        assert result.untracked == ()

    def test_edited_untracked_file_is_kept(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Re-editing an already-deployed new file makes it work again."""
        (tmp_path / "new.vue").write_text("edited")
        monkeypatch.setattr(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files", lambda _repo: ["new.vue"]
        )

        changes = ChangeSet(
            build_commit="a" * 40,
            files=("new.vue",),
            categories={ChangeCategory.VUE: ("new.vue",)},
            untracked=("new.vue",),
        )
        result = filter_stale_dirty(changes, self._state({"new.vue": "stale" * 12}), tmp_path)

        assert result.files == ("new.vue",)
        assert result.untracked == ("new.vue",)

    def test_deleted_files_survive_filtering(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Deletions are not dirty-file candidates and must be carried through.

        Dropping them made the changeset look empty, so the caller reported
        "nothing to deploy" and the files stayed on the site.
        """
        (tmp_path / "kept.py").write_text("content")
        known_hash = compute_file_hash(tmp_path / "kept.py")
        monkeypatch.setattr(
            "cmk.dev_deploy.state.deploy_state.get_dirty_files", lambda _repo: ["kept.py"]
        )

        changes = ChangeSet(
            build_commit="a" * 40,
            files=("kept.py",),
            categories={ChangeCategory.PYTHON: ("kept.py",)},
            deleted_files=("cmk/gui/gone.py",),
        )
        result = filter_stale_dirty(changes, self._state({"kept.py": known_hash}), tmp_path)

        assert result.files == ()
        assert result.deleted_files == ("cmk/gui/gone.py",)
        assert result.is_empty is False
