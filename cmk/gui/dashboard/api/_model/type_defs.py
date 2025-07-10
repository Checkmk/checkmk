#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

import pydantic

from cmk.gui.openapi.framework.model.converter import RegistryConverter, TypedPlainValidator
from cmk.gui.type_defs import InfoName
from cmk.gui.visuals.info import visual_info_registry


def _validate_info_name(value: str) -> InfoName:
    """Validate that the info name is a valid identifier."""
    RegistryConverter(visual_info_registry).validate(value)
    return InfoName(value)


type AnnotatedInfoName = Annotated[InfoName, TypedPlainValidator(str, _validate_info_name)]


# without alpha channel, either 3 or 6 hex digits
type ColorHex = Annotated[str, pydantic.Field(pattern=r"^#(?:[0-9A-F]{3}){1,2}$")]
