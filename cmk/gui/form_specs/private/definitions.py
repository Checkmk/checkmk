#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    FormSpec,
    InputHint,
    InvalidElementValidator,
)
from cmk.rulesets.v1.form_specs._basic import MultilineText

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class UnknownFormSpec(FormSpec[Any]):
    pass


@dataclass(frozen=True, kw_only=True)
class SingleChoiceElementExtended(Generic[T]):
    name: T
    title: Title


@dataclass(frozen=True, kw_only=True)
class SingleChoiceExtended(Generic[T], FormSpec[T]):
    # SingleChoice:
    elements: Sequence[SingleChoiceElementExtended[T]]
    no_elements_text: Message | None = None
    frozen: bool = False
    label: Label | None = None
    prefill: DefaultValue[T] | InputHint[Title] = InputHint(Title("Please choose"))
    ignored_elements: tuple[str, ...] = ()
    invalid_element_validation: InvalidElementValidator | None = None


@dataclass(frozen=True, kw_only=True)
class CommentTextArea(MultilineText):
    pass
