#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ParametersTypeAlias = Mapping[str, Any]  # Modification may result in an incompatible API change.


def worst_service_state(*states: int, default: int) -> int:
    """Return the 'worst' aggregation of all states

    Integers encode service states like this:

        0 -> OK
        1 -> WARN
        2 -> CRIT
        3 -> UNKNOWN

    Unfortunately this does not reflect the order of severity, or "badness", where

        OK -> WARN -> UNKNOWN -> CRIT

    That's why this function is just not quite `max`.

    Examples:

    >>> worst_service_state(0, 0, default=0)  # OK
    0
    >>> worst_service_state(0, 1, default=0)  # WARN
    1
    >>> worst_service_state(0, 1, 2, 3, default=0)  # CRIT
    2
    >>> worst_service_state(0, 1, 3, default=0)  # UNKNOWN
    3
    >>> worst_service_state(default=0)
    0
    >>> worst_service_state(default=1)
    1
    >>> worst_service_state(default=2)
    2
    >>> worst_service_state(default=3)
    3

    """
    return 2 if 2 in states else max(states, default=default)


def section_name_of(check_plugin_name: str) -> str:
    return check_plugin_name.split(".")[0]


def maincheckify(subcheck_name: str) -> str:
    """Get new plug-in name

    The new API does not know about "subchecks", so drop the dot notation.
    The validation step will prevent us from having colliding plugins.
    """
    return subcheck_name.replace(".", "_").replace(  # subchecks don't exist anymore
        "-", "_"
    )  # "sap.value-groups"
