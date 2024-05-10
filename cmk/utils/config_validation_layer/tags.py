#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from pydantic import BaseModel, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError
from cmk.utils.tags import TagConfigSpec


class BaseTagModel(BaseModel):
    id: str
    title: str


class TagGroupTagsModel(BaseTagModel):
    aux_tags: list[str]


class TagGroupModel(BaseTagModel):
    tags: list[TagGroupTagsModel]


class AuxTagModel(BaseTagModel):
    topic: str | Omitted = OMITTED_FIELD
    help: str | Omitted = OMITTED_FIELD


class WatoTags(BaseModel):
    tag_groups: list[TagGroupModel]
    aux_tags: list[AuxTagModel]

    class Config:
        validate_assignment = True


def validate_tags(tags: TagConfigSpec) -> None:
    tags_dict = cast(dict, tags)

    try:
        WatoTags(**tags_dict)
    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="tags.mk",
            pydantic_error=exc,
            original_data=tags,
        )
