#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

SNMPDetectAtom = tuple[str, str, bool]  # (oid, regex_pattern, expected_match)

# This def is used to keep the API-exposed object in sync with our
# implementation.
SNMPDetectBaseType = list[list[tuple[str, str, bool]]]


class SNMPDetectSpec(SNMPDetectBaseType):
    """A specification for SNMP device detection"""

    @classmethod
    def from_json(cls, serialized: Mapping[str, Any]) -> SNMPDetectSpec:
        try:
            # The cast is necessary as mypy does not infer types in a list comprehension.
            # See https://github.com/python/mypy/issues/5068
            return cls(
                [
                    [cast(SNMPDetectAtom, tuple(inner)) for inner in outer]
                    for outer in serialized["snmp_detect_spec"]
                ]
            )
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def to_json(self) -> Mapping[str, Any]:
        return {"snmp_detect_spec": self}
