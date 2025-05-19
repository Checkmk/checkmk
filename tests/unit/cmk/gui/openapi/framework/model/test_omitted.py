#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from dataclasses import dataclass

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.omitted import ApiOmitted, json_dump_without_omitted


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
    dumped = json.loads(json_dump_without_omitted(model.__class__, model))
    assert dumped == expected
