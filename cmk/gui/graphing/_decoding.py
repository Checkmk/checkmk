#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.type_defs import VisualContext


def ensure_type[T](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return value


def context_from_json(data: object) -> VisualContext:
    if not isinstance(data, dict):
        raise TypeError(f"expected a mapping, got {type(data).__name__}")
    return {
        ensure_type(filter_name, str): {
            ensure_type(key, str): ensure_type(value, str)
            for key, value in ensure_type(variables, dict).items()
        }
        for filter_name, variables in data.items()
    }
