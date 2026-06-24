#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Minimal crash-reporting library: dataclasses, on-disk store, and fingerprint helpers.

Ported verbatim from ``cmk.ccc.crash_reporting``. Write-time deduplication
behavior is preserved: the fingerprint helpers and the
``CrashReportStore.save()`` merge-into-existing logic live in this library
alongside the store. The public API surface is unchanged from the old module —
only the import path moves (``cmk.ccc.crash_reporting`` → ``cmk.crash``).
"""

from cmk.ccc.version_info import VersionInfo

from ._crash import (
    ABCCrashReport,
    BaseDetails,
    ContactDetails,
    CRASH_INFO_VERSION,
    CrashInfo,
    CrashOccurrences,
    format_var_for_export,
    make_crash_report_base_path,
    REDACTED_STRING,
    RobustJSONEncoder,
    SENSITIVE_KEYWORDS,
    SerializedCrashReport,
    TDetails,
)
from ._fingerprint import (
    crash_fingerprint,
    fingerprint_hash,
    normalize_crash_time,
)
from ._store import (
    cleanup_crash_reports,
    CrashReportStore,
    DEFAULT_MAX_CRASH_AGE,
    DEFAULT_MAX_CRASHES_TOTAL_SIZE,
)

__all__ = [
    "ABCCrashReport",
    "BaseDetails",
    "cleanup_crash_reports",
    "ContactDetails",
    "CRASH_INFO_VERSION",
    "CrashInfo",
    "CrashOccurrences",
    "CrashReportStore",
    "DEFAULT_MAX_CRASH_AGE",
    "DEFAULT_MAX_CRASHES_TOTAL_SIZE",
    "REDACTED_STRING",
    "RobustJSONEncoder",
    "SENSITIVE_KEYWORDS",
    "SerializedCrashReport",
    "TDetails",
    "VersionInfo",
    "crash_fingerprint",
    "fingerprint_hash",
    "format_var_for_export",
    "make_crash_report_base_path",
    "normalize_crash_time",
]
