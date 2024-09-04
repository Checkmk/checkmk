#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.rulesets.v1.form_specs import MultipleChoiceElement


def edition_specific_global_services() -> Sequence[MultipleChoiceElement]:
    return []


def edition_specific_regional_services() -> Sequence[MultipleChoiceElement]:
    return []
