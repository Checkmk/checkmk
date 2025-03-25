#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

from cmk.rulesets.v1 import form_specs, Label
from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class OptionalChoice(form_specs.FormSpec[object]):
    """Keep in mind that the parameter_form may not return None as parameter
    None is already reserved by the OptionalChoice itself to represent
    the absence of a choice.

    With the negate flag set to True, the meaning of the checkbox is inverted.
    So if the checkbox is checked, the parameter will be set to None, anything else
    means unchecked
    """

    parameter_form: FormSpec[Any]
    label: Label | None = None
    none_label: Label = Label("(unset)")
    negate: bool = False
