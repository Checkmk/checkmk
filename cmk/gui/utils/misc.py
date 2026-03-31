#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from typing import Any


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def savefloat(f: Any) -> float:
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def saveint(x: Any) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def gen_id() -> str:
    """Generates a unique id"""
    return str(uuid.uuid4())
