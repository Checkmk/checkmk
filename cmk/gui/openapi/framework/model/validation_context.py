#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import ValidationInfo

from cmk.gui.openapi.framework._context import ApiContext


class RequestValidationContext:
    """The pydantic validation context the framework validates a request with.

    A validator reads it from `ValidationInfo.context` by declaring a second parameter of type
    `pydantic.ValidationInfo`.

    The context carries the ApiContext and nothing else. A validator that needs a per-request
    application object, like the Setup folder tree, gets it through `ApiContext.shared()`, which
    shares it with the endpoint handler.
    """

    __slots__ = ("api_context",)

    def __init__(self, api_context: ApiContext) -> None:
        self.api_context = api_context


def validation_context_of(info: ValidationInfo[object]) -> RequestValidationContext:
    """The validation context of the request a value is validated for.

    The framework provides it with every request. A validator that needs it can only run inside
    a request validation; tests have to pass `RequestValidationContext(api_context)` as the
    `context` of their `validate_python` call.
    """
    if isinstance(info.context, RequestValidationContext):
        return info.context
    raise TypeError("This validator runs without the RequestValidationContext of the framework")
