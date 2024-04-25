#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from pydantic import BaseModel, RootModel, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError

from .piggyback import Piggyback


class DCD(BaseModel):
    title: str
    comment: str | Omitted = OMITTED_FIELD
    docu_url: str | Omitted = OMITTED_FIELD
    disabled: bool
    site: str
    connector: tuple[Literal["piggyback"], Piggyback]


DCDMapModel = RootModel[dict[str, DCD]]


def validate_dcds(dcds: dict) -> None:
    try:
        DCDMapModel(dcds)
    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="connections.mk",
            pydantic_error=exc,
            original_data=dcds,
        )
