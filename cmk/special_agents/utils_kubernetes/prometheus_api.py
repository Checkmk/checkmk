#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-expr
# mypy: disallow-any-unimported
# mypy: disallow-any-expr
# mypy: disallow-any-decorated
# mypy: disallow-any-explicit
# mypy: disallow-any-generics
# mypy: disallow-subclassing-any
# mypy: warn-return-any

import datetime
import enum
from collections.abc import Mapping, Sequence
from json import JSONDecodeError
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

Labels = NewType("Labels", Mapping[str, str])


class Status(str, enum.Enum):
    success = "success"
    error = "error"


class ErrorType(str, enum.Enum):
    none = ""
    timeout = "timeout"
    canceled = "canceled"
    execution = "execution"
    bad_data = "bad_data"
    internal = "internal"
    unavailable = "unavailable"
    not_found = "not_found"


class ValueType(str, enum.Enum):
    vector = "vector"
    scalar = "scalar"
    matrix = "matrix"
    string = "string"


class ParseModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )


Point = tuple[datetime.datetime, float]


class Scalar(ParseModel):
    type_: Literal[ValueType.scalar] = Field(alias="resultType")
    result: Point


class String(ParseModel):
    type_: Literal[ValueType.string] = Field(alias="resultType")
    result: tuple[datetime.datetime, str]


class Sample(ParseModel):
    metric: Labels
    value: Point


class Vector(ParseModel):
    type_: Literal[ValueType.vector] = Field(alias="resultType")
    result: Sequence[Sample]


class Series(ParseModel):
    metric: Labels
    values: Sequence[Point]


class Matrix(ParseModel):
    type_: Literal[ValueType.matrix] = Field(alias="resultType")
    result: Sequence[Series]


class ResponseSuccess(ParseModel):
    status: Literal[Status.success]
    data: Scalar | String | Vector | Matrix = Field(discriminator="type_")
    warnings: Sequence[str] = []


class ResponseError(ParseModel):
    status: Literal[Status.error]
    error_type: ErrorType = Field(alias="errorType")
    error: str = ""
    data: Scalar | String | Vector | Matrix | None = Field(None, discriminator="type_")


Response = Annotated[ResponseSuccess | ResponseError, Field(discriminator="status")]


def parse_raw_response(
    response: bytes | str,
) -> Response | ValidationError | JSONDecodeError:
    try:
        adapter: TypeAdapter[Response] = TypeAdapter(Response)
        return adapter.validate_json(response)
    except (ValidationError, JSONDecodeError) as e:
        return e
