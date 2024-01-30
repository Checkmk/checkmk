#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from ._localize import Localizable


@dataclass(frozen=True, kw_only=True)
class FormSpec:
    """
    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
