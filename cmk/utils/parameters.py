#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Iterable

from cmk.utils.type_defs import LegacyCheckParameters


def boil_down_parameters(
    parameters: Iterable[LegacyCheckParameters],
    default: LegacyCheckParameters,
) -> LegacyCheckParameters:
    """
    first occurrance wins:
    >>> boil_down_parameters([{'a': 1},{'a': 2, 'b': 3}], {})
    {'a': 1, 'b': 3}

    first non-Mapping wins:
    >>> boil_down_parameters([{'a': 1}, (23, 42), {'a': 2, 'b': 3}, (0, 42)], {})
    (23, 42)

    """
    merged: Dict[str, Any] = {}
    for par in parameters:
        if not isinstance(par, dict):
            return par
        merged.update((item for item in par.items() if item[0] not in merged))

    try:
        return {**default, **merged}  # type: ignore[list-item]
    except TypeError:
        return merged or default
