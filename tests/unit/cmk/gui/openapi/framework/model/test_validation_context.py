#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

import pytest
from pydantic import PlainValidator, TypeAdapter, ValidationInfo

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model.validation_context import (
    RequestValidationContext,
    validation_context_of,
)
from tests.testlib.unit.gui.validation_context import make_api_context, make_validation_context


def _build_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("value", api_context)


def _build_other_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("other", api_context)


def test_the_validators_of_a_request_share_one_value() -> None:
    context = make_validation_context(Config(), LoggedInNobody())

    assert context.shared(_build_value) is context.shared(_build_value)


def test_a_value_is_built_from_the_api_context_of_the_request() -> None:
    api_context = make_api_context(Config(), LoggedInNobody())

    assert RequestValidationContext(api_context).shared(_build_value)[1] is api_context


def test_each_build_function_gets_its_own_value() -> None:
    context = make_validation_context(Config(), LoggedInNobody())

    assert context.shared(_build_value) != context.shared(_build_other_value)


def _context_probe(value: str, info: ValidationInfo[object]) -> str:
    assert isinstance(validation_context_of(info), RequestValidationContext)
    return value


_PROBE_ADAPTER: TypeAdapter[str] = TypeAdapter(Annotated[str, PlainValidator(_context_probe)])


def test_the_request_context_reaches_the_validators() -> None:
    context = make_validation_context(Config(), LoggedInNobody())

    assert _PROBE_ADAPTER.validate_python("value", context=context) == "value"


def test_validation_without_the_request_context_is_refused() -> None:
    with pytest.raises(TypeError, match="without the RequestValidationContext"):
        _PROBE_ADAPTER.validate_python("value")
