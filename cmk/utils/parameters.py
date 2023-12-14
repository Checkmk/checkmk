#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterable, Mapping, Reversible
from typing import TypeVar

__all__ = ["boil_down_parameters"]


T = TypeVar("T")


def boil_down_parameters(
    parameters: Iterable[T], default: Mapping[str, T] | T
) -> Mapping[str, T] | T:
    """Merge parameters.

    If parameters contains exclusively of Mappings, this is the same as `merge_parameters`.
    It features special handling of non-dict elements.
    first occurrance wins:
    >>> boil_down_parameters([{'a': 1},{'a': 2, 'b': 3}], {})
    {'a': 1, 'b': 3}

    first non-Mapping wins:
    >>> boil_down_parameters([{'a': 1}, (23, 42), {'a': 2, 'b': 3}, (0, 42)], {})
    (23, 42)

    """
    merged: dict[str, T] = {}
    for par in parameters:
        if not isinstance(par, dict):
            return par
        merged |= (item for item in par.items() if item[0] not in merged)

    try:
        # TODO: We could get rid of the suppression if we used a "isinstance(default, Mapping)"
        # guard, but it's a bit unclear how this affects performance.
        return {**default, **merged}  # type: ignore[dict-item]
    except TypeError:
        return merged or default


def merge_parameters(
    parameters: Reversible[Mapping[str, T]], default: Mapping[str, T]
) -> Mapping[str, T]:
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
