#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Callable
from typing import Any

from cmk.gui.form_specs.unstable.legacy_converter import (
    resolve_help_text,
    resolve_title,
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import FormSpec, Integer


def _identity(value: object) -> object:
    return value


def _transform(
    wrapped_form_spec: FormSpec[Any] | Callable[[], FormSpec[Any]],
    title: Title | None = None,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=wrapped_form_spec,
        from_disk=_identity,
        to_disk=_identity,
        title=title,
    )


def test_resolve_returns_title_and_help_text_of_plain_form_spec() -> None:
    spec = Integer(title=Title("Plain"), help_text=Help("Plain help"))

    assert resolve_title(spec) == Title("Plain")
    assert resolve_help_text(spec) == Help("Plain help")


def test_resolve_looks_through_transform() -> None:
    spec = _transform(Integer(title=Title("Wrapped"), help_text=Help("Wrapped help")))

    assert resolve_title(spec) == Title("Wrapped")
    assert resolve_help_text(spec) == Help("Wrapped help")


def test_resolve_prefers_the_title_of_the_transform_itself() -> None:
    spec = _transform(
        Integer(title=Title("Wrapped"), help_text=Help("Wrapped help")),
        title=Title("Explicit"),
    )

    assert resolve_title(spec) == Title("Explicit")
    assert resolve_help_text(spec) == Help("Wrapped help")


def test_resolve_looks_through_nested_transforms() -> None:
    spec = _transform(_transform(Integer(title=Title("Innermost"))))

    assert resolve_title(spec) == Title("Innermost")


def test_resolve_returns_none_without_title_and_help_text() -> None:
    spec = _transform(Integer())

    assert resolve_title(spec) is None
    assert resolve_help_text(spec) is None


def test_resolve_evaluates_lazy_wrapped_form_spec_only_when_needed() -> None:
    evaluated: list[None] = []

    def wrapped_form_spec() -> Integer:
        evaluated.append(None)
        return Integer(title=Title("Wrapped"))

    assert resolve_title(_transform(wrapped_form_spec, title=Title("Explicit"))) == Title(
        "Explicit"
    )
    assert not evaluated, "the wrapped form spec must not be evaluated if the title is known"

    assert resolve_title(_transform(wrapped_form_spec)) == Title("Wrapped")
    assert len(evaluated) == 1
