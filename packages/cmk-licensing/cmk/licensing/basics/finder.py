#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterable, Sequence
from importlib.machinery import ModuleSpec
from importlib.metadata import Distribution, distributions
from pathlib import Path
from types import ModuleType
from typing import Protocol

from cmk.ccc.version import edition

from .options import get_license_options

_GROUP_PREFIX = "cmk.features."
_DISTRIBUTION_PREFIX = "cmk-"


class FinderP(Protocol):
    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None: ...


def apply_feature_filter(omd_root: Path, meta_path_finders: Iterable[FinderP]) -> Sequence[FinderP]:
    license_options = get_license_options(omd_root, edition(omd_root))
    blocked = files_for_disabled_features(license_options.disabled())
    return [_FeatureFilterFinder(mpf, blocked) for mpf in meta_path_finders]


class _FeatureFilterFinder:
    """Meta path finder that wraps another one and filters out modules based on their origin."""

    def __init__(self, wrapped: FinderP, blocked: set[str]) -> None:
        self._wrapped = wrapped
        self._blocked = blocked
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
        if spec.origin in self._blocked:
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


def blocked_feature_files(omd_root: Path) -> frozenset[str]:
    """Realpath-normalized files belonging to features disabled by the current license.

    Convenience wrapper around `files_for_disabled_features` for callers (e.g. the man-page
    catalog) that need to exclude license-gated files by path — consistent with the import
    filter above.
    """
    disabled = get_license_options(omd_root, edition(omd_root)).disabled()
    return frozenset(os.path.realpath(p) for p in files_for_disabled_features(disabled))


def _tags_of(dist: Distribution) -> set[str]:
    return {
        ep.group.removeprefix(_GROUP_PREFIX)
        for ep in dist.entry_points
        if ep.group.startswith(_GROUP_PREFIX)
    }
