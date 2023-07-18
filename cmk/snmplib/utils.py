#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable

from cmk.utils.regex import regex

from ._typedefs import OID, SNMPDetectAtom, SNMPDetectBaseType

SNMPRowInfoForStoredWalk = list[tuple[OID, str]]


def evaluate_snmp_detection(
    *,
    detect_spec: SNMPDetectBaseType,
    oid_value_getter: Callable[[str], str | None],
) -> bool:
    """Evaluate a SNMP detection specification

    Return True if and and only if at least all conditions in one "line" are True
    """
    return any(
        all(_evaluate_snmp_detection_atom(atom, oid_value_getter) for atom in alternative)
        for alternative in detect_spec
    )


def _evaluate_snmp_detection_atom(
    atom: SNMPDetectAtom,
    oid_value_getter: Callable[[str], str | None],
) -> bool:
    oid, pattern, flag = atom
    value = oid_value_getter(oid)
    if value is None:
        # check for "not_exists"
        return pattern == ".*" and not flag
    # ignore case!
    return bool(regex(pattern, re.IGNORECASE | re.DOTALL).fullmatch(value)) is flag
