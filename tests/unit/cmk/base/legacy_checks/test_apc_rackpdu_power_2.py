#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.apc_rackpdu_power import discover_apc_rackpdu_power
from cmk.plugins.collection.agent_based.apc_rackpdu_power import parse_apc_rackpdu_power


def parsed() -> Mapping[str, Any]:
    """Return parsed data from actual parse function."""
    section = parse_apc_rackpdu_power(
        [
            [["pb-n15-115", "420"]],
            [["1"]],
            [["20", "1", "1", "0"], ["10", "1", "0", "1"], ["9", "1", "0", "2"]],
        ]
    )
    assert section
    return section


def test_apc_rackpdu_power_discovery() -> None:
    """Test discovery function."""
    section = parsed()

    discoveries = list(discover_apc_rackpdu_power(section))

    # Should discover device and two banks
    assert len(discoveries) == 3

    # Extract items from discovery tuples
    items = [item for item, params in discoveries]
    assert "Device pb-n15-115" in items
    assert "Bank 1" in items
    assert "Bank 2" in items
