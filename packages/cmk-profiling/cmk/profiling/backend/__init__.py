#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Profiling backend: on-disk profile store and flamegraph extraction."""

from ._flamegraph import (
    build_flamegraph_tree,
    get_function_paths,
    get_stats_dict,
    get_summary_stats,
    get_top_hotspots,
)
from ._profile import enable, enabled, output_profile
from ._store import (
    DEFAULT_MAX_PROFILES,
    delete_all_profiles,
    delete_profile,
    enforce_retention,
    get_metadata,
    get_profile_path,
    list_metadata,
    new_profile_id,
    PROFILE_ID_RE,
    PROFILE_SUFFIXES,
    ProfileMetadata,
    ProfilingOptions,
    SourceType,
    write_profile,
)

__all__ = [
    "enable",
    "enabled",
    "output_profile",
    "DEFAULT_MAX_PROFILES",
    "PROFILE_ID_RE",
    "PROFILE_SUFFIXES",
    "ProfileMetadata",
    "ProfilingOptions",
    "SourceType",
    "build_flamegraph_tree",
    "delete_all_profiles",
    "delete_profile",
    "enforce_retention",
    "get_function_paths",
    "get_metadata",
    "get_profile_path",
    "get_stats_dict",
    "get_summary_stats",
    "get_top_hotspots",
    "list_metadata",
    "new_profile_id",
    "write_profile",
]
