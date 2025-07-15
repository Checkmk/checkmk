#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
from logging import Logger
from typing import override

from cmk.utils import paths as paths_utils

from cmk.gui.visuals._store import _CombinedVisualsCache

from cmk.update_config.registry import update_action_registry, UpdateAction


class VersionSpecificCachesCleaner(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        paths = [
            paths_utils.include_cache_dir / "builtin",
            paths_utils.include_cache_dir / "local",
            paths_utils.precompiled_checks_dir / "builtin",
            paths_utils.precompiled_checks_dir / "local",
        ]

        walk_cache_dir = paths_utils.var_dir / "snmp_cache"
        if walk_cache_dir.exists():
            paths.extend(walk_cache_dir.iterdir())

        for base_dir in paths:
            try:
                for f in base_dir.iterdir():
                    f.unlink()
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise  # Do not fail on missing directories / files

        # The caches might contain visuals in a deprecated format. For example, in 2.2, painters in
        # visuals are represented by a dedicated type, which was not the case the before. The caches
        # from 2.1 will still contain the old data structures.
        _CombinedVisualsCache.invalidate_all_caches()


update_action_registry.register(
    VersionSpecificCachesCleaner(
        name="version_specific_caches",
        title="Cleanup version specific caches",
        sort_index=50,
    )
)
