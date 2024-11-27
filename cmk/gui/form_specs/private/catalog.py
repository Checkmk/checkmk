#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.rulesets.v1 import form_specs
from cmk.rulesets.v1.form_specs import Dictionary

from .dictionary_extended import DictionaryExtended


@dataclass(frozen=True, kw_only=True)
class Topic:
    name: str
    dictionary: Dictionary | DictionaryExtended


@dataclass(frozen=True, kw_only=True)
class Catalog(form_specs.FormSpec[Mapping[str, object]]):
    topics: list[Topic]
