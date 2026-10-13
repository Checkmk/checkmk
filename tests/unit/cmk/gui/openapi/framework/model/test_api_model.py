#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping
from typing import Literal

import pytest

from cmk.gui.openapi.framework.model import api_field, api_model

_MESSAGE = "inherits from the generic model"


@api_model
class _Item:
    name: str = api_field(description="The item name.", example="item1")


@api_model
class _Collection[T, D]:
    domainType: D = api_field(description="The domain type.", example="item")
    value: list[T] = api_field(description="The items.")


@api_model
class _Defaulted[T = _Item, D = Literal["item"]]:
    domainType: D = api_field(description="The domain type.", example="item")
    value: list[T] = api_field(description="The items.")


def test_plain_inheritance_is_allowed() -> None:
    @api_model
    class Sub(_Item):
        extra: str = api_field(description="Extra.", example="e")

    assert {field.name for field in dataclasses.fields(Sub)} == {"name", "extra"}


def test_parameterized_non_model_base_is_allowed() -> None:
    @api_model
    class Sub(Mapping[str, int]):
        pass

    assert dataclasses.is_dataclass(Sub)


def test_parameterized_base_is_rejected() -> None:
    """Pydantic validates the inherited fields against `T`, not against the given argument."""
    with pytest.raises(TypeError, match=_MESSAGE):

        @api_model
        class Sub(_Collection[_Item, Literal["item"]]):
            pass


def test_identity_reparameterization_is_rejected() -> None:
    """The inherited fields keep the type variables of the base, not those of the subclass."""
    with pytest.raises(TypeError, match=_MESSAGE):

        @api_model
        class Sub[T, D](_Collection[T, D]):
            pass


def test_unparameterized_base_is_rejected() -> None:
    """Without arguments the type variables stay unbound, so the fields accept any value."""
    with pytest.raises(TypeError, match=_MESSAGE):

        @api_model
        class Sub(_Collection):  # type: ignore[type-arg]
            pass


def test_defaulted_base_is_rejected() -> None:
    """Pydantic resolves this one correctly, but we still want one way to parameterize a model."""
    with pytest.raises(TypeError, match=_MESSAGE):

        @api_model
        class Sub(_Defaulted):
            pass


def test_generic_base_is_rejected_through_an_undecorated_class() -> None:
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Intermediate(_Collection[_Item, Literal["item"]]):
        pass

    with pytest.raises(TypeError, match=_MESSAGE):

        @api_model
        class Sub(Intermediate):
            pass
