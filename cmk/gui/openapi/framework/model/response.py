#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass, field

from cmk.gui.openapi.framework.model.api_field import api_field
from cmk.gui.openapi.framework.model.omitted import ApiOmitted

type TypedResponse[T] = T | ApiResponse[T]


@dataclass(slots=True)
class ApiResponse[T]:
    body: T
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ApiErrorDataclass:
    status: int = api_field(
        title="HTTP status code", description="The HTTP status code.", example=404
    )
    title: str = api_field(
        title="Error title",
        description="A summary of the problem.",
        example="Not found",
    )
    detail: str = api_field(
        title="Error message",
        description="Detailed information on what exactly went wrong.",
        example="The resource could not be found.",
    )
    fields: dict[str, str] | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Validation errors",
        description="Detailed error messages on all fields failing validation.",
        example={"field": "error message"},
    )
    ext: dict[str, str] | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Error extensions",
        description="Additional information about the error.",
        example={"key": "value"},
    )
