#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Multi-profile storage for performance profiles (GUI requests, CLI runs, uploads).

Wraps ``cmk.profiling.backend`` with GUI-only concerns: pstats marshalling,
the ``profiling_options`` global-setting dict, and the kwargs flow used by
uploads / WSGI auto-save. The raw on-disk format lives in the shared backend so
``cmk/base`` and ``cmk/gui`` cannot drift.
"""

import logging
import marshal
import pstats
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from cmk.profiling.backend import (
    DEFAULT_MAX_PROFILES,
    enforce_retention,
    get_profile_path,
    get_stats_dict,
    list_metadata,
    PROFILE_ID_RE,
    ProfileMetadata,
    SourceType,
    write_profile,
)
from cmk.profiling.backend import (
    delete_all_profiles as _delete_all_profiles,
)
from cmk.profiling.backend import (
    delete_profile as _delete_profile,
)
from cmk.profiling.backend import (
    get_metadata as _get_metadata,
)

__all__ = [
    "DEFAULT_MAX_PROFILES",
    "PROFILE_ID_RE",
    "ProfileMetadata",
    "ProfileStore",
    "RetentionKwargs",
    "SourceType",
    "retention_kwargs",
]

logger = logging.getLogger(__name__)


class RetentionKwargs(TypedDict):
    max_count: int
    max_age_days: int | None


def retention_kwargs(profiling_options: Mapping[str, object]) -> RetentionKwargs:
    """Extract housekeeping kwargs from the `profiling_options` global setting."""
    raw_count = profiling_options.get("max_count")
    raw_age = profiling_options.get("max_age_days")
    return {
        "max_count": raw_count
        if isinstance(raw_count, int) and raw_count > 0
        else DEFAULT_MAX_PROFILES,
        "max_age_days": raw_age if isinstance(raw_age, int) and raw_age > 0 else None,
    }


class ProfileStore:
    """GUI-facing wrapper around the shared ``profiling_store`` on-disk format."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir

    def save_gui_request(
        self,
        stats: pstats.Stats,
        request_url: str,
        duration_ms: float,
    ) -> str:
        return write_profile(
            self._dir,
            profile_bytes=marshal.dumps(get_stats_dict(stats)),
            source_type="gui_request",
            source_info=request_url,
            duration_ms=round(duration_ms, 2),
        )

    def save_uploaded(self, file_content: bytes, file_name: str) -> str:
        return write_profile(
            self._dir,
            profile_bytes=file_content,
            source_type="file_upload",
            source_info=file_name,
            duration_ms=None,
        )

    def list_profiles(self) -> list[ProfileMetadata]:
        return list_metadata(self._dir)

    def get_metadata(self, profile_id: str) -> ProfileMetadata | None:
        return _get_metadata(self._dir, profile_id)

    def get_profile(self, profile_id: str) -> Path | None:
        return get_profile_path(self._dir, profile_id)

    def delete_profile(self, profile_id: str) -> bool:
        return _delete_profile(self._dir, profile_id)

    def delete_all_profiles(self) -> int:
        return _delete_all_profiles(self._dir)

    def housekeeping(
        self,
        *,
        max_count: int = DEFAULT_MAX_PROFILES,
        max_age_days: int | None = None,
    ) -> int:
        return enforce_retention(self._dir, max_count=max_count, max_age_days=max_age_days)
