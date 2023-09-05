#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.rulesets.v1._localize import Localizable


@dataclass
class TextInput:
    title: Localizable


@dataclass
class DropdownChoice:
    ...


@dataclass(frozen=True)
class DictElement:
    spec: "ValueSpec"


@dataclass
class Dictionary:
    elements: Mapping[str, DictElement]


ItemSpec = TextInput | DropdownChoice

ValueSpec = TextInput | DropdownChoice | Dictionary
