#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from werkzeug.datastructures import ETags

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.framework import ApiContext, APIVersion
from cmk.gui.openapi.framework.model.validation_context import RequestValidationContext


def _api_context() -> ApiContext:
    return ApiContext.new(
        config=Config(),
        version=APIVersion.UNSTABLE,
        etag_if_match=ETags(),
        host_url="http://localhost/",
        user=LoggedInNobody(),
        token=None,
    )


def _build_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("value", api_context)


def _build_other_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("other", api_context)


def test_the_validators_of_a_request_share_one_value() -> None:
    context = RequestValidationContext(_api_context())

    assert context.shared(_build_value) is context.shared(_build_value)


def test_a_value_is_built_from_the_api_context_of_the_request() -> None:
    api_context = _api_context()

    assert RequestValidationContext(api_context).shared(_build_value)[1] is api_context


def test_each_build_function_gets_its_own_value() -> None:
    context = RequestValidationContext(_api_context())

    assert context.shared(_build_value) != context.shared(_build_other_value)
