#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Protocol, TypeVar

# We want to use
# if TYPE_CHECKING:
#     from _typeshed import SupportsRichComparison
# for 'sort_key' in '_node.py' but unfortunately sphinx does not accept that. Thus we simply copy
# 'SupportsRichComparison' from https://github.com/python/typeshed/blob/main/stdlib/_typeshed/__init__.pyi

_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsBool(Protocol):
    def __bool__(self) -> bool: ...


class SupportsDunderLT(Protocol[_T_contra]):
    def __lt__(self, other: _T_contra, /) -> SupportsBool: ...


class SupportsDunderGT(Protocol[_T_contra]):
    def __gt__(self, other: _T_contra, /) -> SupportsBool: ...


type SupportsRichComparison = SupportsDunderLT[Any] | SupportsDunderGT[Any]
