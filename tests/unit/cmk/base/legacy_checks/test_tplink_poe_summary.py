#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.base.legacy_checks.tplink_poe_summary import (
    check_tplink_poe_summary,
    parse_tplink_poe_summary,
)


@pytest.mark.xfail(
    strict=True, reason="Crash report edbd90ca-39bd-11f1-89a9-00155d64710a: IndexError"
)
def test_check_tplink_poe_summary_without_data() -> None:
    # Crash group 4704: the switch answered the PoE power query with an empty
    # table. The check yields nothing, so the service reports that its item was
    # not found in the monitoring data.
    assert check_tplink_poe_summary(None, {"levels": None}, parse_tplink_poe_summary([])) is None
