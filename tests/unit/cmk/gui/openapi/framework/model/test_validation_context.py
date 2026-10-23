#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

import pytest
from pydantic import PlainValidator, TypeAdapter, ValidationInfo

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.framework.model.validation_context import (
    RequestValidationContext,
    validation_context_of,
)
from tests.testlib.unit.gui.validation_context import make_validation_context


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
