#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Reversible
from typing import TypeVar

_T = TypeVar("_T")


def merge_parameters(
    parameters: Reversible[Mapping[str, _T]], default: Mapping[str, _T]
) -> Mapping[str, _T]:
    """
    Merge dictionary based parameters.

    The keys in the result are the union of the keys of the elements of `parameters`.
    First occurrance wins:

        >>> merge_parameters([{'a': 1},{'a': 2, 'b': 3}], {})
        {'a': 1, 'b': 3}

    """
    merged = {**default}
    for par in reversed(parameters):
        merged.update(par)
    return merged
