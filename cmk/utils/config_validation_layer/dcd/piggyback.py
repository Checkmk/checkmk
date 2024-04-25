#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import BaseModel, field_validator, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD


class PiggybackCreationRules(BaseModel):
    create_folder_path: str
    host_attributes: list[tuple[str, str]]
    delete_hosts: bool
    matching_hosts: str | Omitted = OMITTED_FIELD


class Piggyback(BaseModel):
    source_filters: list[str] | Omitted = OMITTED_FIELD
    interval: int
    creation_rules: list[PiggybackCreationRules]
    discover_on_creation: bool
    no_deletion_time_after_init: int
    max_cache_age: int
    validity_period: int

    @field_validator("creation_rules")
    def validate_creation_rules_attribute(cls, value):
        if len(value) == 0:
            raise ValidationError("creation_rules cannot be empty")

        return value
