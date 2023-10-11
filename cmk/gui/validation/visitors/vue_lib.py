#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

from cmk.gui.validation.ir.elements import FormElement


@dataclass(kw_only=True)
class GenericComponent:
    component_type: str
    title: str | None
    help: str | None
    validation_errors: list[str]
    config: dict[str, Any]

    def __init__(
        self,
        node: FormElement,
        component_type: str,
        config: dict[str, Any],
        validation_errors: list[str] | None = None,
    ):
        self.title = node.details.label_text
        self.help = node.details.help
        self.component_type = component_type
        self.validation_errors = [] if validation_errors is None else validation_errors
        self.config = config
