#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.spec.spec_generator._doc_pydantic import _extract_body_example


def test_extract_body_example_with_examples() -> None:
    @api_model
    class SayHello:
        message: str = api_field(description="A greeting.", example="Hello world!")
        recipient: str = api_field(description="Who to greet.", example="Bob")

    assert _extract_body_example(SayHello) == {"message": "Hello world!", "recipient": "Bob"}


def test_extract_body_example_uses_serialization_alias() -> None:
    @api_model
    class WithAlias:
        my_field: str = api_field(
            description="A field with an alias.",
            serialization_alias="myField",
            example="some_value",
        )

    assert _extract_body_example(WithAlias) == {"myField": "some_value"}


def test_extract_body_example_no_examples_returns_none() -> None:
    @api_model
    class NoExamples:
        message: str = api_field(description="A field without an example.", default="fallback")

    assert _extract_body_example(NoExamples) is None


def test_extract_body_example_none_input_returns_none() -> None:
    assert _extract_body_example(None) is None


def test_extract_body_example_recurses_into_nested_dataclass() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="Inner value.", example="inner_example")

    @api_model
    class Outer:
        name: str = api_field(description="Name.", example="outer_name")
        nested: Inner = api_field(description="Nested model.")

    assert _extract_body_example(Outer) == {
        "name": "outer_name",
        "nested": {"value": "inner_example"},
    }


def test_extract_body_example_explicit_example_takes_priority_over_recursion() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="Inner value.", example="should_not_appear")

    @api_model
    class Outer:
        nested: Inner = api_field(
            description="Nested with explicit example.",
            example={"value": "explicit"},
        )

    assert _extract_body_example(Outer) == {"nested": {"value": "explicit"}}


def test_extract_body_example_skips_nested_without_examples() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="No example.", default="default")

    @api_model
    class Outer:
        nested: Inner = api_field(description="Nested model without examples.")

    assert _extract_body_example(Outer) is None


def test_extract_body_example_substitutes_the_type_argument() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="", example="nested")

    @api_model
    class Generic[T, D]:
        domainType: D = api_field(description="")
        payload: T = api_field(description="")

    assert _extract_body_example(Generic[Inner, Literal["thing"]]) == {
        "payload": {"value": "nested"}
    }


def test_extract_body_example_prefers_the_generic_field_example() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="", example="nested")

    @api_model
    class Generic[T]:
        payload: T = api_field(description="", example="explicit")

    assert _extract_body_example(Generic[Inner]) == {"payload": "explicit"}


def test_extract_body_example_generic_without_examples_returns_none() -> None:
    @api_model
    class Inner:
        value: str = api_field(description="")

    @api_model
    class Generic[T]:
        payload: T = api_field(description="")

    assert _extract_body_example(Generic[Inner]) is None
