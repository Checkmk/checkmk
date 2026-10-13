#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import datetime
import json
from dataclasses import dataclass

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.omitted import (
    ApiOmitted,
    drop_omitted_union_errors,
    json_dump_without_omitted,
)


@dataclass
class _TestModel:
    field: int | None | ApiOmitted = api_field(description="field", default_factory=ApiOmitted)


def test_validation_valid_type_works() -> None:
    model = TypeAdapter(_TestModel).validate_python(  # astrein: disable=pydantic-type-adapter
        {"field": 123}
    )
    assert model.field == 123


def test_validation_none_stays_none() -> None:
    model = TypeAdapter(_TestModel).validate_python(  # astrein: disable=pydantic-type-adapter
        {"field": None}
    )
    assert model.field is None


def test_validation_omitted_stays_omitted() -> None:
    model = TypeAdapter(_TestModel).validate_python(  # astrein: disable=pydantic-type-adapter
        {"field": ApiOmitted()}
    )
    assert isinstance(model.field, ApiOmitted)


def test_validation_invalid_type_raises() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(_TestModel).validate_python(  # astrein: disable=pydantic-type-adapter
            {"field": "string"}
        )


@dataclass
class _NestedModel:
    nested: _TestModel
    nested_list: list[_TestModel]


# chosen because json.dumps normally doesn't support datetime
@dataclass
class _DatetimeModel:
    field: datetime.datetime


@pytest.mark.parametrize(
    "model, expected",
    [
        (
            _TestModel(field=123),
            {"field": 123},
        ),
        (
            _TestModel(field=None),
            {"field": None},
        ),
        (
            _TestModel(field=ApiOmitted()),
            {},
        ),
        (
            _NestedModel(
                nested=_TestModel(field=ApiOmitted()),
                nested_list=[
                    _TestModel(field=123),
                    _TestModel(field=None),
                    _TestModel(field=ApiOmitted()),
                ],
            ),
            {"nested": {}, "nested_list": [{"field": 123}, {"field": None}, {}]},
        ),
        (
            _DatetimeModel(field=datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)),
            {"field": "2025-01-01T00:00:00Z"},
        ),
    ],
)
def test_json_dump_without_omitted(model: _TestModel | _NestedModel, expected: dict) -> None:  # type: ignore[misc]
    dumped = json.loads(json_dump_without_omitted(model.__class__, model))
    assert dumped == expected


def _error_locs(adapter: TypeAdapter, value: object) -> set[tuple[int | str, ...]]:
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_python(value)
    return {error["loc"] for error in drop_omitted_union_errors(exc_info.value.errors())}


def test_the_omitted_branch_error_and_label_are_dropped() -> None:
    @dataclass
    class Model:
        field: int | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    adapter = TypeAdapter(Model)  # astrein: disable=pydantic-type-adapter

    assert _error_locs(adapter, {"field": "abc"}) == {("field",)}


def test_the_label_is_stripped_from_locations_inside_the_branch() -> None:
    @dataclass
    class Inner:
        sub: int = api_field(description="")

    @dataclass
    class Model:
        field: list[Inner] | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    adapter = TypeAdapter(Model)  # astrein: disable=pydantic-type-adapter

    assert _error_locs(adapter, {"field": [{"sub": "abc"}]}) == {("field", 0, "sub")}


def test_labels_of_several_failing_branches_are_kept() -> None:
    @dataclass
    class Model:
        field: int | list[str] | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    adapter = TypeAdapter(Model)  # astrein: disable=pydantic-type-adapter

    assert _error_locs(adapter, {"field": {}}) == {("field", "int"), ("field", "list[str]")}


def test_a_nullable_omittable_field_errors_like_a_plain_nullable_one() -> None:
    @dataclass
    class Model:
        field: int | None | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    adapter = TypeAdapter(Model)  # astrein: disable=pydantic-type-adapter

    assert _error_locs(adapter, {"field": "abc"}) == {("field",)}


def test_nested_omittable_fields_lose_all_labels() -> None:
    @dataclass
    class Inner:
        sub: int | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    @dataclass
    class Model:
        field: Inner | ApiOmitted = api_field(description="", default_factory=ApiOmitted)

    adapter = TypeAdapter(Model)  # astrein: disable=pydantic-type-adapter

    assert _error_locs(adapter, {"field": {"sub": "abc"}}) == {("field", "sub")}


def test_errors_without_an_omittable_field_stay_unchanged() -> None:
    @dataclass
    class Model:
        field: int = api_field(description="")

    with pytest.raises(ValidationError) as exc_info:
        TypeAdapter(Model).validate_python(  # astrein: disable=pydantic-type-adapter
            {"field": "abc"}
        )
    errors = exc_info.value.errors()

    assert drop_omitted_union_errors(errors) == errors
