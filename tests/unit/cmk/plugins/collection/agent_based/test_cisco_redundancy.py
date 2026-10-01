#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.agent_based.cisco_redundancy import (
    check_cisco_redundancy,
    parse_cisco_redundancy,
)


@pytest.mark.xfail(
    strict=True,
    raises=IndexError,
    reason="Crash report 2b390da8-5580-11f0-8d75-005056b33584: IndexError in check_cisco_redundancy",
)
def test_check_cisco_redundancy_without_data() -> None:
    # The device answers the redundancy table with no rows after the service was discovered.
    list(
        check_cisco_redundancy(
            {"init_states": ["0", "14", "0", "9", "1"]},
            parse_cisco_redundancy([]),
        )
    )
