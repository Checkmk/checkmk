#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Mapping
from typing import Any

from cmk.plugins.ibm_mq.lib import is_ibm_mq_service_vanished

__all__ = ["is_ibm_mq_service_vanished", "ibm_mq_check_version"]


def ibm_mq_check_version(
    actual_version: str | None, params: Mapping[str, Any], label: str
) -> tuple[int, str]:
    """
    >>> ibm_mq_check_version(
    ...    "2.0.0b4",
    ...     {"version": (("at_least", "2.0.0p2"), 2)},
    ...     "Doc test",
    ... )
    (2, 'Doc test: 2.0.0b4 (should be at least 2.0.0p2)')

    """

    def tokenize(version: str) -> list[int]:
        _map_chars = {"p": 2, "b": 1, "i": 0}
        if not set("0123456789.pbi").issuperset(version):
            raise ValueError(version)
        return [
            _map_chars[g] if g in _map_chars else int(g)
            for g in re.findall(r"(\d+|[pbi]+)", version)
        ]

    info = f"{label}: {actual_version}"
    if actual_version is None:
        return 3, info + " (no agent info)"
    if "version" not in params:
        return 0, info
    (comp_type, expected_version), state = params["version"]
    try:
        parts_actual = tokenize(actual_version)
        parts_expected = tokenize(expected_version)
    except ValueError:
        return 3, (
            f"Cannot compare {actual_version} and {expected_version}."
            " Only numbers separated by characters 'b', 'i', 'p', or '.' are allowed for a version."
        )

    if comp_type == "at_least" and parts_actual < parts_expected:
        return state, info + " (should be at least %s)" % expected_version
    if comp_type == "specific" and parts_actual != parts_expected:
        return state, info + " (should be %s)" % expected_version
    return 0, info
