# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.manifest.deps (dependency expansion and dir extraction)."""

from __future__ import annotations

from unittest.mock import patch

from cmk.dev_deploy.manifest.deps import expand_dependencies

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
