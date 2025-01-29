#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from cmk.rulesets.v1.form_specs import FormSpec

ModelT = TypeVar("ModelT")

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class World(Enum):
    CONFIG = "config"
    CORE = "core"


@dataclass(frozen=True, kw_only=True)
class Source(Enum):
    EXPLICIT = "explicit"
    RULESET = "ruleset"
    DISCOVERED = "discovered"


@dataclass(frozen=True, kw_only=True)
class Labels(FormSpec[Mapping[str, str]]):
    world: World
    label_source: Source | None = None
    max_labels: int | None = None
