#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.hyperv_checkpoints import check_hyperv_checkpoints


def test_check_hyperv_checkpoints_negative_age_due_to_clock_skew() -> None:
    # Agent reported checkpoint age of -6 seconds (clock skew).
    # Negative ages must produce a WARN result instead of crashing.
    section = [["28f01c67-bc04-4a60-b6bd-e7561386e0b9", "-6"]]
    results = list(check_hyperv_checkpoints(None, {}, section))
    warn_results = [r for r in results if isinstance(r, tuple) and r[0] == 1]
    assert len(warn_results) == 2
    assert all("clock skew" in r[1] for r in warn_results)
