# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for cmk.dev_deploy.edition_filter -- edition hierarchy and directory removal."""

from pathlib import Path

import pytest

from cmk.dev_deploy.site.edition_filter import (
    ALL_EDITION_DIRS,
    EDITION_CONFIG,
    editions_to_remove,
    filter_edition_files,
    filter_editions,
)
from cmk.dev_deploy.types import Edition

# ---------------------------------------------------------------------------
# Data integrity tests
# ---------------------------------------------------------------------------


class TestEditionIncludes:
    def test_covers_all_editions(self) -> None:
        """EDITION_CONFIG.includes must have an entry for every Edition member."""
        assert set(EDITION_CONFIG.includes.keys()) == set(Edition)

    def test_all_edition_dirs_exact(self) -> None:
        """ALL_EDITION_DIRS must match the expected set exactly."""
        assert ALL_EDITION_DIRS == frozenset({"pro", "ultimate", "ultimatemt", "cloud"})

    def test_all_edition_dirs_no_cee(self) -> None:
        """Regression guard: 'cee' is a legacy directory name, NOT an edition dir."""
        assert "cee" not in ALL_EDITION_DIRS


# ---------------------------------------------------------------------------
# editions_to_remove -- parametrized over all 5 editions
# ---------------------------------------------------------------------------


class TestEditionsToRemove:
    @pytest.mark.parametrize(
        "edition, expected_removed",
        [
            pytest.param(
                Edition.COMMUNITY,
                frozenset({"pro", "ultimate", "ultimatemt", "cloud"}),
                id="community-removes-all",
            ),
            pytest.param(
                Edition.PRO,
                frozenset({"ultimate", "ultimatemt", "cloud"}),
                id="pro-removes-three",
            ),
            pytest.param(
                Edition.ULTIMATE,
                frozenset({"ultimatemt", "cloud"}),
                id="ultimate-removes-two",
            ),
            pytest.param(
                Edition.ULTIMATEMT,
                frozenset({"cloud"}),
                id="ultimatemt-removes-cloud-only",
            ),
            pytest.param(
                Edition.CLOUD,
                frozenset({"ultimatemt"}),
                id="cloud-removes-ultimatemt-only",
            ),
        ],
    )
    def test_editions_to_remove(
        self, edition: Edition, expected_removed: frozenset[str]
    ) -> None:
        assert editions_to_remove(edition) == expected_removed


# ---------------------------------------------------------------------------
# filter_editions -- filesystem tests using tmp_path
# ---------------------------------------------------------------------------


def _create_edition_tree(root: Path) -> None:
    """Create a directory tree mimicking nonfree edition dirs with dummy files."""
    for subdir in (
        "nonfree/pro",
        "nonfree/ultimate",
        "nonfree/cloud",
        "nonfree/ultimatemt",
    ):
        d = root / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / "plugin.py").write_text("# dummy")


class TestFilterEditions:
    def test_cloud_keeps_pro_ultimate_cloud_removes_ultimatemt(
        self, tmp_path: Path
    ) -> None:
        _create_edition_tree(tmp_path)

        removed = filter_editions(tmp_path, Edition.CLOUD)

        assert (tmp_path / "nonfree" / "pro").is_dir()
        assert (tmp_path / "nonfree" / "ultimate").is_dir()
        assert (tmp_path / "nonfree" / "cloud").is_dir()
        assert not (tmp_path / "nonfree" / "ultimatemt").exists()
        assert len(removed) == 1
        assert tmp_path / "nonfree" / "ultimatemt" in removed

    def test_community_removes_all_four(self, tmp_path: Path) -> None:
        _create_edition_tree(tmp_path)

        removed = filter_editions(tmp_path, Edition.COMMUNITY)

        for name in ("pro", "ultimate", "cloud", "ultimatemt"):
            assert not (tmp_path / "nonfree" / name).exists(), (
                f"{name} should be removed"
            )
        assert len(removed) == 4

    def test_nested_structure(self, tmp_path: Path) -> None:
        """Edition dirs at arbitrary depth should be found and removed."""
        for path in (
            "gui/nonfree/pro",
            "gui/nonfree/ultimate",
            "base/nonfree/ultimate",
            "base/nonfree/cloud",
        ):
            d = tmp_path / path
            d.mkdir(parents=True, exist_ok=True)
            (d / "module.py").write_text("# dummy")

        removed = filter_editions(tmp_path, Edition.ULTIMATE)

        # ultimate keeps: pro, ultimate
        assert (tmp_path / "gui" / "nonfree" / "pro").is_dir()
        assert (tmp_path / "gui" / "nonfree" / "ultimate").is_dir()
        assert (tmp_path / "base" / "nonfree" / "ultimate").is_dir()
        # cloud should be removed
        assert not (tmp_path / "base" / "nonfree" / "cloud").exists()
        assert len(removed) == 1

    def test_empty_deploy_root(self, tmp_path: Path) -> None:
        """Empty directory should return empty list without errors."""
        removed = filter_editions(tmp_path, Edition.PRO)

        assert removed == []

    def test_non_edition_dirs_preserved(self, tmp_path: Path) -> None:
        """Directories not matching edition names must not be touched."""
        for name in ("utils", "helpers", "cee", "nonfree"):
            d = tmp_path / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "data.py").write_text("# dummy")

        removed = filter_editions(tmp_path, Edition.COMMUNITY)

        for name in ("utils", "helpers", "cee", "nonfree"):
            assert (tmp_path / name).is_dir(), f"{name} should be preserved"
        assert removed == []

    def test_returned_paths_are_absolute(self, tmp_path: Path) -> None:
        """Returned paths must be usable absolute paths."""
        _create_edition_tree(tmp_path)

        removed = filter_editions(tmp_path, Edition.PRO)

        for p in removed:
            assert p.is_absolute()


# ---------------------------------------------------------------------------
# filter_edition_files -- per-file edition filtering (no filesystem access)
# ---------------------------------------------------------------------------


class TestFilterEditionFiles:
    def test_no_filtering_for_cloud(self) -> None:
        """Cloud edition keeps all files -- editions_to_remove returns {ultimatemt} only,
        but cloud INCLUDES pro/ultimate/cloud. So only ultimatemt is excluded."""
        files = [
            "cmk/gui/views.py",
            "cmk/gui/nonfree/pro/license.py",
            "cmk/gui/nonfree/ultimate/ha.py",
            "cmk/gui/nonfree/cloud/dashboard.py",
        ]
        result = filter_edition_files(files, Edition.CLOUD)
        # Cloud removes ultimatemt only, so all these files pass
        assert result == files

    def test_community_filters_all_editions(self) -> None:
        """Community edition filters out files containing pro/ultimate/ultimatemt/cloud path components."""
        files = [
            "cmk/gui/views.py",
            "cmk/gui/nonfree/pro/license.py",
            "cmk/gui/nonfree/ultimate/ha.py",
            "cmk/gui/nonfree/ultimatemt/tenant.py",
            "cmk/gui/nonfree/cloud/dashboard.py",
        ]
        result = filter_edition_files(files, Edition.COMMUNITY)
        assert result == ["cmk/gui/views.py"]

    def test_pro_edition_keeps_pro_files(self) -> None:
        """Pro edition keeps files with 'pro' component, filters ultimate/ultimatemt/cloud."""
        files = [
            "cmk/gui/views.py",
            "cmk/gui/nonfree/pro/license.py",
            "cmk/gui/nonfree/ultimate/ha.py",
            "cmk/gui/nonfree/cloud/dashboard.py",
        ]
        result = filter_edition_files(files, Edition.PRO)
        assert result == ["cmk/gui/views.py", "cmk/gui/nonfree/pro/license.py"]

    def test_nested_edition_path(self) -> None:
        """Files like cmk/gui/nonfree/cloud/dashboard.py are correctly filtered."""
        files = [
            "cmk/gui/nonfree/cloud/sub/deep/module.py",
        ]
        result = filter_edition_files(files, Edition.COMMUNITY)
        assert result == []

    def test_no_false_positives(self) -> None:
        """Files like cmk/gui/production.py (contains 'pro' substring) are NOT filtered."""
        files = [
            "cmk/gui/production.py",
            "cmk/gui/cloud_utils.py",
            "cmk/gui/ultimate_test.py",
        ]
        # Community removes pro/ultimate/ultimatemt/cloud as path components
        # But "production", "cloud_utils", "ultimate_test" are NOT exact path components
        result = filter_edition_files(files, Edition.COMMUNITY)
        assert result == files

    def test_empty_input(self) -> None:
        """Empty file list returns empty list."""
        result = filter_edition_files([], Edition.COMMUNITY)
        assert result == []
