#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

from ._typedefs import RangeLimit, SNMPSectionName


def parse_oid_range_config(
    rule_values: Sequence[object],
) -> Mapping[SNMPSectionName, Sequence[RangeLimit]]:
    """Parse the OID range limits from the given config values."""
    # Validation code below is a typical result when typing is bad or absent
    return {
        SNMPSectionName(v[0]): [_parse_range_limit(l) for l in v[1]]
        for v in reversed(rule_values)
        if isinstance(v, tuple) and v[1] is not None  # the rule can be OPTIONAL!
    }


def _parse_range_limit(raw: object) -> RangeLimit:
    match raw:
        case ("first" | "last" as position, int(limit)):
            return position, limit
        case ("mid", tuple((int(), int())) as oid_range):
            return "mid", oid_range
        case _:
            raise ValueError(raw)
