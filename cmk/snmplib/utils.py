#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Callable, List, Optional, Tuple

from cmk.utils.regex import regex
from cmk.utils.type_defs import SNMPDetectBaseType

from .type_defs import OID, SNMPDetectAtom

SNMPRowInfoForStoredWalk = List[Tuple[OID, str]]


def evaluate_snmp_detection(
    *,
    detect_spec: SNMPDetectBaseType,
    oid_value_getter: Callable[[str], Optional[str]],
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
    oid_value_getter: Callable[[str], Optional[str]],
) -> bool:
    oid, pattern, flag = atom
    value = oid_value_getter(oid)
    if value is None:
        # check for "not_exists"
        return pattern == ".*" and not flag
    # ignore case!
    return bool(regex(pattern, re.IGNORECASE | re.DOTALL).fullmatch(value)) is flag
