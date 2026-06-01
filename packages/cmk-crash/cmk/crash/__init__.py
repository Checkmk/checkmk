#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Minimal crash-reporting library: dataclasses, on-disk store, and fingerprint helpers.

Code is migrated here from ``cmk.ccc.crash_reporting`` later. Write-time
deduplication behavior is preserved. the fingerprint helpers and the
``CrashReportStore.save()`` merge-into-existing logic land in this library
alongside the store.
"""
