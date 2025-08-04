#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass, field, InitVar

from werkzeug.datastructures import ETags

from .._context import ETag
from ._api_field import api_field
from ._api_model import api_model
from .omitted import ApiOmitted

type TypedResponse[T] = T | ApiResponse[T]


@dataclass(slots=True)  # this isn't an api model, and we want positional arguments
class ApiResponse[T]:
    body: T
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    etag: InitVar[ETag | None] = None

    def __post_init__(self, etag: ETag | None) -> None:
        if etag is not None:
            if "ETag" in self.headers:
                raise ValueError("ETag header already set")
            self.headers["ETag"] = ETags(strong_etags=[etag.hash()]).to_header()


@api_model
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
    ext: dict[str, str] | object | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        title="Error extensions",
        description="Additional information about the error.",
        example={"key": "value"},
    )
