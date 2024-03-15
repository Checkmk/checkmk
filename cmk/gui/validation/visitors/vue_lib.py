#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec


@dataclass(kw_only=True)
class VueDictionaryData:
    is_active: bool
    value: Any


@dataclass
class ValidationError:
    message: str
    field_id: str | None = None

    def __hash__(self) -> int:
        return hash(f"{self.message}")

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)


class ValueAndValidation(NamedTuple):
    value: Any
    validation: str | None


# Experimental only registry (not an actual registry)
form_spec_registry: dict[str, LoadedRuleSpec] = {}


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    vue_schema: dict[str, Any]
    data: Any
