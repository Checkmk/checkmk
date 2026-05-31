#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import types
from dataclasses import dataclass
from typing import Annotated, cast

import pytest

from cmk.gui.openapi.framework._utils import get_resolved_origin, resolve_type


@dataclass
class _A:
    pass


@dataclass
class _B:
    pass


type _TAliasOfA = _A
type _TAliasOfAnnotatedA = Annotated[_A, "meta"]
type _TAliasOfUnion = _A | _B
type _TAliasOfAnnotatedUnion = Annotated[_A | _B, "meta"]
type _TNestedAlias = Annotated[_TAliasOfUnion, "meta"]
type _TAliasOfListStr = list[str]


@pytest.mark.parametrize(
    "input_type",
    [
        _A,
        cast(type, Annotated[_A, "meta"]),
        cast(type, Annotated[Annotated[_A, "inner"], "outer"]),
        _TAliasOfA,
        _TAliasOfAnnotatedA,
        cast(type, Annotated[_TAliasOfA, "meta"]),
    ],
)
def test_resolve_type_resolves_to_a(input_type: type) -> None:
    assert resolve_type(input_type) is _A


@pytest.mark.parametrize(
    "input_type",
    [
        _A | _B,
        _TAliasOfUnion,
        _TAliasOfAnnotatedUnion,
        _TNestedAlias,
    ],
)
def test_resolve_type_resolves_to_union(input_type: type) -> None:
    assert resolve_type(input_type) == (_A | _B)


def test_resolve_type_preserves_inner_generic_annotated() -> None:
    # Only outermost wrapper stripped; inner Annotated inside dict value is preserved
    result = resolve_type(cast(type, Annotated[dict[str, Annotated[int, "foo"]], "bar"]))
    assert result == dict[str, Annotated[int, "foo"]]


@pytest.mark.parametrize(
    "input_type, expected",
    [
        (_A, _A),
        (cast(type, Annotated[list[str], "meta"]), list),
        (_TAliasOfListStr, list),
        (_A | _B, types.UnionType),
    ],
)
def test_get_resolved_origin(input_type: type, expected: type) -> None:
    assert get_resolved_origin(input_type) is expected
