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


def validate_uuid_str(raw: str | None) -> str | None:
    """Return *raw* if it is a valid UUID string in the canonical lowercase form
    produced by :func:`gen_id`, otherwise ``None``.

    Parses *raw* via ``uuid.UUID`` and re-serializes it. If the result differs
    from *raw* (e.g. uppercase input) or parsing raises ``ValueError`` (malformed
    input), ``None`` is returned.
    """
    if not raw:
        return None
    try:
        return raw if str(uuid.UUID(raw)) == raw else None
    except ValueError:
        return None
