#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from dataclasses import dataclass

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.omitted import (
    _remove_omitted,
    ApiOmitted,
    json_dump_without_omitted,
    OMITTED_PLACEHOLDER,
)


@dataclass
class _TestModel:
    field: int | None | ApiOmitted = api_field(description="field", default_factory=ApiOmitted)


def test_validation_valid_type_works():
    model = TypeAdapter(_TestModel).validate_python(  # nosemgrep: type-adapter-detected
        {"field": 123}
    )
    assert model.field == 123


def test_validation_none_stays_none():
    model = TypeAdapter(_TestModel).validate_python(  # nosemgrep: type-adapter-detected
        {"field": None}
    )
    assert model.field is None


def test_validation_omitted_stays_omitted():
    model = TypeAdapter(_TestModel).validate_python(  # nosemgrep: type-adapter-detected
        {"field": ApiOmitted()}
    )
    assert isinstance(model.field, ApiOmitted)


def test_validation_invalid_type_raises():
    with pytest.raises(ValidationError):
        TypeAdapter(_TestModel).validate_python(  # nosemgrep: type-adapter-detected
            {"field": "string"}
        )


def test_validation_placeholder_raises():
    with pytest.raises(ValidationError):
        TypeAdapter(_TestModel).validate_python(  # nosemgrep: type-adapter-detected
            {"field": OMITTED_PLACEHOLDER}
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
def test_json_dump_without_omitted(model: _TestModel | _NestedModel, expected: dict) -> None:
    dumped = json_dump_without_omitted(model.__class__, model)
    assert dumped == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param(None, None, id="none"),
        pytest.param(True, True, id="bool_true"),
        pytest.param(False, False, id="bool_false"),
        pytest.param(123, 123, id="int"),
        pytest.param(1.23, 1.23, id="float"),
        pytest.param("test", "test", id="string"),
        pytest.param({}, {}, id="empty_dict"),
        pytest.param(
            {"field": 123, "other": "test"},
            {"field": 123, "other": "test"},
            id="dict_without_omitted",
        ),
        pytest.param(
            {"field": 123, "omit_me": OMITTED_PLACEHOLDER, "other": "test"},
            {"field": 123, "other": "test"},
            id="dict_with_omitted",
        ),
        pytest.param(
            {"field": 123, "other": {"omit_me": OMITTED_PLACEHOLDER}},
            {"field": 123, "other": {}},
            id="dist_with_nested_omitted",
        ),
        pytest.param([], [], id="empty_list"),
        pytest.param(
            [1, 2, 3, 0],
            [1, 2, 3, 0],
            id="list_without_omitted",
        ),
        pytest.param(
            [1, 2, OMITTED_PLACEHOLDER, 3, 0],
            [1, 2, 3, 0],
            id="list_with_omitted",
        ),
        pytest.param(
            [{"field": 123}, {"field": OMITTED_PLACEHOLDER}],
            [{"field": 123}, {}],
            id="list_of_dicts",
        ),
    ],
)
def test_remove_omitted(raw: object, expected: object) -> None:
    assert _remove_omitted(raw) == expected


def test_remove_omitted_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Cannot remove omitted value if it's the only value"):
        _remove_omitted(OMITTED_PLACEHOLDER)


def test_remove_omitted_raises_type_error() -> None:
    with pytest.raises(TypeError, match="Unsupported type for JSON serialization"):
        _remove_omitted(object())
