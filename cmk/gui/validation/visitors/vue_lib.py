#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

from cmk.gui.i18n import _
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.rulesets.v1 import FormSpec


@dataclass(kw_only=True)
class VueFormSpecComponent:
    component_type: str
    title: str | None
    help: str | None
    validation_errors: list[str] | None
    config: dict[str, Any]

    def __init__(
        self,
        form_spec: FormSpec,
        component_type: str,
        config: dict[str, Any],
        validation_errors: list[str] | None = None,
    ):
        self.title = None if form_spec.title is None else form_spec.title.localize(_)
        self.help = None if form_spec.help_text is None else form_spec.help_text.localize(_)
        self.component_type = component_type
        self.validation_errors = validation_errors
        self.config = config


@dataclass
class ValidationError:
    message: str
    field_id: str | None = None

    def __hash__(self) -> int:
        return hash(f"{self.message}")

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)


# Experimental only registry (not an actual registry)
form_spec_registry: dict[str, LoadedRuleSpec] = {}


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    component: dict[str, Any]
