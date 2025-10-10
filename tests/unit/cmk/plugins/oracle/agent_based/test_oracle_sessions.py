#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


from cmk.plugins.oracle.agent_based.oracle_sessions import (
    inventory_oracle_sessions,
    parse_oracle_sessions,
)


def test_inventory_oracle_sessions_fail():
    assert not list(
        inventory_oracle_sessions(parse_oracle_sessions([["foo", "FAILURE"], ["bar", "FAILURE"]]))
    )
