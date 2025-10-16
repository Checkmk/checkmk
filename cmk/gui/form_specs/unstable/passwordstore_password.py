#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal

from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class PasswordStorePassword(
    FormSpec[
        tuple[
            Literal["cmk_postprocessed"],
            Literal["stored_password"],
            tuple[str, str],
        ]
    ]
):
    """Specifies a form for configuring passwords from password store"""
