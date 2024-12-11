#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any, Mapping

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class TopicElement:
    parameter_form: FormSpec[Any]
    required: bool = False


@dataclass(frozen=True, kw_only=True)
class TopicGroup:
    title: Title
    elements: dict[str, TopicElement]


@dataclass(frozen=True, kw_only=True)
class Topic:
    title: Title
    elements: dict[str, TopicElement] | list[TopicGroup]

    def __post_init__(self) -> None:
        if isinstance(self.elements, list):
            seen_keys = set()
            for topic in self.elements:
                for key in topic.elements.keys():
                    if key in seen_keys:
                        raise ValueError(f"Duplicate key '{key}' in topic")
                    seen_keys.add(key)


@dataclass(frozen=True, kw_only=True)
class Catalog(FormSpec[Mapping[str, Mapping[str, object]]]):
    elements: dict[str, Topic]
