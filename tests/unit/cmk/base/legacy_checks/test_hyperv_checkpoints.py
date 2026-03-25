#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.hyperv_checkpoints import check_hyperv_checkpoints


@pytest.mark.xfail(
    strict=True,
    reason="Crash report 4db49690: ValueError in render.timespan for negative checkpoint age",
)
def test_check_hyperv_checkpoints_negative_age_due_to_clock_skew() -> None:
    # Agent reported checkpoint age of -6 seconds (clock skew).
    # render.timespan() raises ValueError for negative values.
    section = [["28f01c67-bc04-4a60-b6bd-e7561386e0b9", "-6"]]
    list(check_hyperv_checkpoints(None, {}, section))
