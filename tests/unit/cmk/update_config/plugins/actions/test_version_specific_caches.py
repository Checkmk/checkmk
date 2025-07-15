#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.utils import paths as paths_utils

from cmk.update_config.plugins.actions.version_specific_caches import VersionSpecificCachesCleaner


@pytest.fixture(name="plugin", scope="module")
def fixture_plugin() -> VersionSpecificCachesCleaner:
    return VersionSpecificCachesCleaner(
        name="version_specific_caches",
        title="Cleanup version specific caches",
        sort_index=30,
    )


def test_cleanup_missing_directory(plugin: VersionSpecificCachesCleaner) -> None:
    plugin(logging.getLogger())


def test_cleanup(plugin: VersionSpecificCachesCleaner) -> None:
    paths = [
        paths_utils.include_cache_dir / "builtin",
        paths_utils.include_cache_dir / "local",
        paths_utils.precompiled_checks_dir / "builtin",
        paths_utils.precompiled_checks_dir / "local",
    ]
    for base_dir in paths:
        base_dir.mkdir(parents=True, exist_ok=True)
        cached_file = base_dir / "if"
        with cached_file.open("w", encoding="utf-8") as f:
            f.write("\n")
        plugin(logging.getLogger())
        assert not cached_file.exists()
        assert base_dir.exists()
