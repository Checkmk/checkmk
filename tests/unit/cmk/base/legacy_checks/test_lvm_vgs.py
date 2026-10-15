#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.check_legacy_includes.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.base.legacy_checks.lvm_vgs import check_lvm_vgs, parse_lvm_vgs


@pytest.mark.usefixtures("initialised_item_state")
def test_check_lvm_vgs_ignores_foreign_line() -> None:
    section = parse_lvm_vgs(
        [
            ['{"level":"info","msg":"runner started","time":"2025-10-01T07:41:17+02:00"}'],
            ["vg1", "1", "6", "0", "wz--n-", "268431261696", "32195477504"],
        ]
    )

    list(check_lvm_vgs("vg1", FILESYSTEM_DEFAULT_PARAMS, section))
