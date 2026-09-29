#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.pvecm_status import check_pvecm_status, parse_pvecm_status


@pytest.mark.xfail(
    strict=True,
    reason="Crash report e2e37676-d54d-11f0-bfa5-960000901c25: KeyError in check_pvecm_status",
)
def test_check_pvecm_status_reports_missing_cluster_data() -> None:
    # The section only holds a message without "key: value" pairs.
    section = parse_pvecm_status([["Cannot initialize CMAP service"]])
    assert list(check_pvecm_status(None, None, section)) == [
        (
            3,
            "Cannot evaluate cluster state, missing in agent output: "
            "nodes, quorum, expected votes, total votes",
        )
    ]
