#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import types
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, cast, Literal, TypeVar

import pytest

from cmk.gui.openapi.framework._utils import (
    get_resolved_origin,
    resolve_type,
    substitute_type_vars,
)


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


type _TRecursiveAlias = list[_TRecursiveAlias] | str


@dataclass
class _Annotations[T, D]:
    """The annotations under test.

    They live on a dataclass because a type checker rejects a type variable inside a value
    expression, which is what an inline `list[T]` would be.
    """

    in_list: list[T]
    in_dict: dict[str, T]
    in_sequence: Sequence[T]
    nested: list[dict[str, T]]
    in_union: T | None
    annotated: Annotated[list[T], "meta"]
    two_type_vars: dict[D, list[T]]
    literal: Literal["a", "b"]
    plain_model: _A
    plain_container: list[str]
    alias: _TAliasOfListStr
    recursive_alias: _TRecursiveAlias
    recursive_alias_in_list: list[_TRecursiveAlias]


_T, _D = cast(tuple[TypeVar, TypeVar], _Annotations.__type_params__)
_ANNOTATION = {field.name: field.type for field in dataclasses.fields(_Annotations)}


class TestSubstituteTypeVars:
    def test_bare_type_var(self) -> None:
        assert substitute_type_vars(_T, {_T: _A}) is _A

    def test_unbound_type_var(self) -> None:
        with pytest.raises(ValueError, match="Unbound type variable"):
            substitute_type_vars(_T, {_D: _A})

    @pytest.mark.parametrize(
        "name, expected",
        [
            pytest.param("in_list", list[_A], id="list"),
            pytest.param("in_dict", dict[str, _A], id="dict-value"),
            pytest.param("in_sequence", Sequence[_A], id="abstract-sequence"),
            pytest.param("nested", list[dict[str, _A]], id="nested-container"),
        ],
    )
    def test_substitutes_inside_a_container(self, name: str, expected: object) -> None:
        assert substitute_type_vars(_ANNOTATION[name], {_T: _A}) == expected

    def test_union_stays_a_union_type(self) -> None:
        substituted = substitute_type_vars(_ANNOTATION["in_union"], {_T: _A})
        assert isinstance(substituted, types.UnionType)
        assert set(substituted.__args__) == {_A, type(None)}

    def test_annotated_keeps_its_metadata(self) -> None:
        substituted = substitute_type_vars(_ANNOTATION["annotated"], {_T: _A})
        assert substituted == Annotated[list[_A], "meta"]

    def test_multiple_type_vars(self) -> None:
        substituted = substitute_type_vars(_ANNOTATION["two_type_vars"], {_T: _A, _D: _B})
        assert substituted == dict[_B, list[_A]]

    @pytest.mark.parametrize(
        "name",
        ["literal", "plain_model", "plain_container", "alias", "recursive_alias"],
    )
    def test_annotation_without_type_vars_is_returned_unchanged(self, name: str) -> None:
        annotation = _ANNOTATION[name]
        assert substitute_type_vars(annotation, {_T: _A, _D: _B}) is annotation

    def test_recursive_type_alias_terminates(self) -> None:
        annotation = _ANNOTATION["recursive_alias_in_list"]
        assert substitute_type_vars(annotation, {_T: _A}) == annotation

    def test_empty_substitutions_leave_the_annotation_alone(self) -> None:
        annotation = _ANNOTATION["in_list"]
        assert substitute_type_vars(annotation, {}) is annotation
