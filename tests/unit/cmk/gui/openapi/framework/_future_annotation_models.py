#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Models of a module that stringifies its annotations, like the generated shared typing code."""

from __future__ import annotations

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted

type Kind = Literal["first", "second"]


@api_model
class StringAnnotationModel:
    kind: Kind = api_field(description="The kind.", example="first")
    optional: str | ApiOmitted = api_field(
        default_factory=ApiOmitted, description="Optional.", example="x"
    )


@api_model
class StringAnnotationWithDefault:
    value: str = api_field(description="Value.", example="x", default="bad")
