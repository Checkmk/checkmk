#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""License-based import filter installed by ``omd/packages/Python/sitecustomize.py``.

See ``doc/documentation/arch-comp-licensing-feature-filter.rst`` for the rationale
and the wheel tagging convention (``cmk.license_options.<option>`` entry-point groups).
"""

import os
import sys
from collections.abc import Collection, Iterable, Sequence
from functools import cached_property
from importlib.machinery import ModuleSpec
from importlib.metadata import Distribution, distributions
from types import ModuleType
from typing import Final, Protocol

_GROUP_PREFIX = "cmk.license_options."
_DISTRIBUTION_PREFIX = "cmk-"


class FinderP(Protocol):
    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None: ...


def install(meta_path: Iterable[FinderP], blocked: Collection[str]) -> list[FinderP]:
    """Wrap every finder so that it does not find modules located in ``blocked``.

    Use it as ``sys.meta_path[:] = install(sys.meta_path, ...)``.
    """
    block_list = _BlockList(frozenset(blocked))
    return [_FeatureFilterFinder(finder, block_list) for finder in meta_path]


def blocked_files() -> frozenset[str]:
    """Realpath-normalized files hidden by the filter installed in ``sys.meta_path``.

    For code that discovers files on disk instead of importing them (e.g. man pages).
    Empty if no filter is installed, consistent with what is importable.
    """
    for finder in sys.meta_path:
        if isinstance(finder, _FeatureFilterFinder):
            return finder.block_list.real_paths
    return frozenset()


class _BlockList:
    def __init__(self, origins: frozenset[str]) -> None:
        self.origins: Final = origins

    @cached_property
    def real_paths(self) -> frozenset[str]:
        return frozenset(os.path.realpath(p) for p in self.origins)


class _FeatureFilterFinder:
    """Meta path finder that wraps another one and filters out modules based on their origin."""

    def __init__(self, wrapped: FinderP, block_list: _BlockList) -> None:
        self._wrapped = wrapped
        self.block_list: Final = block_list
        # It is not enough to implement `find_spec`.
        # While that is the documented interface,
        # implementing just that will break `importlib.metadata.version` (for instance).
        if hasattr(wrapped, "find_distributions"):
            self.find_distributions = wrapped.find_distributions

    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None:
        if (spec := self._wrapped.find_spec(fullname, path, target)) is None:
            return None
        if spec.origin is None:
            # We don't block namespace packages. Namespaces can originate from more
            # than one package (e.g. `cmk.plugins`), and they don't contain actual
            # functionality. Only block once we're down to loading an actual file.
            return spec
        if spec.origin in self.block_list.origins:
            return None  # note: raising here would fail during plugin discovery.
        return spec


def files_for_disabled_features(disabled_features: set[str]) -> set[str]:
    """Given a set of *disabled* features, this function returns the set of files
    belonging to packages whose tags are all in the disabled set.

    Example: Files of a package that is tagged with 'a' and 'b' will be included
    if both the features 'a' and 'b' are disabled (because we may block the file).
    """
    our_distributions = (d for d in distributions() if d.name.startswith(_DISTRIBUTION_PREFIX))
    return {
        str(file.locate())
        for dist in our_distributions
        if (tags := _tags_of(dist)) and tags.issubset(disabled_features)
        for file in (dist.files or ())
    }


def _tags_of(dist: Distribution) -> set[str]:
    return {
        ep.group.removeprefix(_GROUP_PREFIX)
        for ep in dist.entry_points
        if ep.group.startswith(_GROUP_PREFIX)
    }
