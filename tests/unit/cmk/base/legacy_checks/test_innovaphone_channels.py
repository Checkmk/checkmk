#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.innovaphone_channels import check_innovaphone_channels


def test_check_innovaphone_channels_zero_total_is_ok() -> None:
    info = [["A", "Up", "Up", "0", "0"]]

    assert list(check_innovaphone_channels("A", {"levels": (75.0, 80.0)}, info)) == [
        (0, "No channels available (total: 0)"),
    ]
