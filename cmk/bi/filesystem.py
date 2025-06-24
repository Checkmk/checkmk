#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import functools
from pathlib import Path
from typing import Self

from cmk.utils.paths import default_config_dir, tmp_dir, var_dir

BI_SITE_CACHE_PREFIX = "bi_site_cache"


@dataclasses.dataclass
class BIFileSystemCache:
    _root: Path
    compiled_aggregations: Path
    site_structure_data: Path

    @classmethod
    def build(cls, root: Path) -> Self:
        _root = root / "bi_cache"
        (compilations := _root / "compiled_aggregations").mkdir(parents=True, exist_ok=True)
        (site_structure_data := _root / "site_structure_data").mkdir(parents=True, exist_ok=True)
        return cls(_root, compilations, site_structure_data)

    @functools.cached_property
    def compilation_lock(self) -> Path:
        return self._root / "compilation.LOCK"

    @functools.cached_property
    def last_compilation(self) -> Path:
        return self._root / "last_compilation"

    def get_site_structure_data_path(self, site_id: str, timestamp: str) -> Path:
        return self.site_structure_data / f"{BI_SITE_CACHE_PREFIX}.{site_id}.{timestamp}"

    def clear_compilation_cache(self) -> None:
        self.compilation_lock.unlink(missing_ok=True)
        self.last_compilation.unlink(missing_ok=True)

        for compilation_path in self.compiled_aggregations.iterdir():
            compilation_path.unlink(missing_ok=True)

    @staticmethod
    def is_site_cache(fpath: Path) -> bool:
        return fpath.name.startswith(BI_SITE_CACHE_PREFIX)


@dataclasses.dataclass
class BIFileSystemVar:
    _root: Path
    frozen_aggregations: Path

    @classmethod
    def build(cls, root: Path) -> Self:
        (frozen_aggregations := root / "frozen_aggregations").mkdir(parents=True, exist_ok=True)
        return cls(root, frozen_aggregations)


@dataclasses.dataclass
class BIFileSystemEtc:
    _root: Path
    config: Path

    @classmethod
    def build(cls, root: Path) -> Self:
        (config := root / "multisite.d/wato/bi_config.bi").parent.mkdir(parents=True, exist_ok=True)
        return cls(root, config)

    @property
    def multisite(self) -> Path:
        return self._root / "multisite.d"


@dataclasses.dataclass
class BIFileSystem:
    cache: BIFileSystemCache
    var: BIFileSystemVar
    etc: BIFileSystemEtc

    @classmethod
    def build(cls, tmp: Path, var: Path, etc: Path) -> Self:
        return cls(
            cache=BIFileSystemCache.build(tmp),
            var=BIFileSystemVar.build(var),
            etc=BIFileSystemEtc.build(etc),
        )


def get_default_site_filesystem() -> BIFileSystem:
    return BIFileSystem.build(tmp_dir, var_dir, default_config_dir)
