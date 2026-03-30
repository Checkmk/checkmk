# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.manifest.deps (dependency expansion and dir extraction)."""

from __future__ import annotations

from unittest.mock import patch

from cmk.dev_deploy.manifest.deps import expand_dependencies, extract_changed_dirs

_GET_DEPLOY_DEPS = "cmk.dev_deploy.manifest.reader.get_deploy_deps"


# ---------------------------------------------------------------------------
# expand_dependencies
# ---------------------------------------------------------------------------


class TestExpandDependencies:
    """Tests for expand_dependencies()."""

    def test_empty_input_returns_empty(self) -> None:
        """Empty changed_dirs produces empty result."""
        with patch(_GET_DEPLOY_DEPS, return_value={}):
            assert expand_dependencies(set()) == set()

    def test_no_deps_for_dir_returns_original(self) -> None:
        """Dir present in deploy_deps but with no dependencies returns just that dir."""
        with patch(_GET_DEPLOY_DEPS, return_value={"packages/a/": []}):
            result = expand_dependencies({"packages/a/"})
        assert result == {"packages/a/"}

    def test_single_dependency(self) -> None:
        """A -> B: expanding A returns {A, B}."""
        deps: dict[str, list[str]] = {
            "packages/a/": ["packages/b/"],
            "packages/b/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/a/"})
        assert result == {"packages/a/", "packages/b/"}

    def test_transitive_chain(self) -> None:
        """A -> B -> C: expanding A returns {A, B, C}."""
        deps: dict[str, list[str]] = {
            "packages/a/": ["packages/b/"],
            "packages/b/": ["packages/c/"],
            "packages/c/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/a/"})
        assert result == {"packages/a/", "packages/b/", "packages/c/"}

    def test_cycle_handling(self) -> None:
        """A -> B -> A: visited set prevents infinite loop."""
        deps: dict[str, list[str]] = {
            "packages/a/": ["packages/b/"],
            "packages/b/": ["packages/a/"],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/a/"})
        assert result == {"packages/a/", "packages/b/"}

    def test_multiple_input_dirs_with_shared_deps(self) -> None:
        """Multiple inputs sharing a dep: result is the union."""
        deps: dict[str, list[str]] = {
            "packages/a/": ["packages/shared/"],
            "packages/b/": ["packages/shared/"],
            "packages/shared/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/a/", "packages/b/"})
        assert result == {"packages/a/", "packages/b/", "packages/shared/"}

    def test_dir_not_in_deploy_deps_silently_ignored(self) -> None:
        """Dir not present as a key in deploy_deps is kept but not expanded."""
        deps: dict[str, list[str]] = {
            "packages/known/": ["packages/dep/"],
            "packages/dep/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/unknown/"})
        # The unknown dir is in the result (it was in changed_dirs) but no expansion
        assert result == {"packages/unknown/"}

    def test_diamond_dependency(self) -> None:
        """A -> B, A -> C, B -> D, C -> D: D appears once."""
        deps: dict[str, list[str]] = {
            "packages/a/": ["packages/b/", "packages/c/"],
            "packages/b/": ["packages/d/"],
            "packages/c/": ["packages/d/"],
            "packages/d/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = expand_dependencies({"packages/a/"})
        assert result == {"packages/a/", "packages/b/", "packages/c/", "packages/d/"}


# ---------------------------------------------------------------------------
# extract_changed_dirs
# ---------------------------------------------------------------------------


class TestExtractChangedDirs:
    """Tests for extract_changed_dirs()."""

    def test_empty_files_returns_empty(self) -> None:
        """No files produces empty result."""
        with patch(_GET_DEPLOY_DEPS, return_value={"packages/a/": []}):
            assert extract_changed_dirs(()) == set()

    def test_file_matches_no_key_returns_empty(self) -> None:
        """File that does not start with any deploy_deps key is ignored."""
        deps: dict[str, list[str]] = {"packages/a/": []}
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(("unrelated/foo.py",))
        assert result == set()

    def test_file_matches_a_key(self) -> None:
        """File starting with a deploy_deps key returns that key."""
        deps: dict[str, list[str]] = {"packages/a/": []}
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(("packages/a/src/main.py",))
        assert result == {"packages/a/"}

    def test_longest_prefix_wins(self) -> None:
        """When multiple keys match, the longest prefix is selected."""
        deps: dict[str, list[str]] = {
            "packages/": [],
            "packages/a/": [],
            "packages/a/sub/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(("packages/a/sub/file.py",))
        assert result == {"packages/a/sub/"}

    def test_multiple_files_same_dir_returns_dir_once(self) -> None:
        """Multiple files under the same key produce a single entry."""
        deps: dict[str, list[str]] = {"cmk/gui/": []}
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(
                ("cmk/gui/views.py", "cmk/gui/models.py", "cmk/gui/utils.py")
            )
        assert result == {"cmk/gui/"}

    def test_multiple_files_different_dirs(self) -> None:
        """Files in different dirs produce all matching dirs."""
        deps: dict[str, list[str]] = {
            "cmk/gui/": [],
            "cmk/base/": [],
        }
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(("cmk/gui/views.py", "cmk/base/core.py"))
        assert result == {"cmk/gui/", "cmk/base/"}

    def test_mixed_matching_and_unmatched(self) -> None:
        """Only files matching a key are included; others silently ignored."""
        deps: dict[str, list[str]] = {"cmk/gui/": []}
        with patch(_GET_DEPLOY_DEPS, return_value=deps):
            result = extract_changed_dirs(("cmk/gui/views.py", "README.md", "tests/conftest.py"))
        assert result == {"cmk/gui/"}
