#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Public surface of the legacy livestatus-backed quicksearch machinery.

The sidebar quicksearch snapin is the only consumer outside of this package, so this
module re-exports exactly what it needs from the private `_engines._livestatus` module.
"""

from ._engines._livestatus import (
    ABCLivestatusMatchPlugin,
    ABCQuicksearchConductor,
    BasicPluginQuicksearchConductor,
    FilterBehaviour,
    get_url_builder,
    IncorrectLabelInputError,
    legacy_view_urls,
    LivestatusQuicksearchConductor,
    sanitize_and_validate_regex,
    UrlBuilder,
    UsedFilters,
)

__all__ = [
    "ABCLivestatusMatchPlugin",
    "ABCQuicksearchConductor",
    "BasicPluginQuicksearchConductor",
    "FilterBehaviour",
    "IncorrectLabelInputError",
    "LivestatusQuicksearchConductor",
    "UrlBuilder",
    "UsedFilters",
    "get_url_builder",
    "legacy_view_urls",
    "sanitize_and_validate_regex",
]
