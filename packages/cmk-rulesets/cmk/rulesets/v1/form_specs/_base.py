#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from .._localize import Localizable

_T = TypeVar("_T")


@dataclass(frozen=True, kw_only=True)
class FormSpec:
    """
    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
    """

    title: Localizable | None = None
    help_text: Localizable | None = None


@dataclass(frozen=True)
class Migrate(Generic[_T]):
    """Creates a transformation that changes the value as a one-off event.

    You can add a ``Migrate`` instance to a form spec to update the value from an
    old version to be compatible with the current definition.

    Args:
        model_to_form: Transforms the present parameter value ("consumer model")
                       to a value compatible with the current form specification.
    """

    model_to_form: Callable[[object], _T]
