#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass, field, InitVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema, CoreSchema

from cmk.ccc.version import Edition, edition

from cmk.utils import paths

from cmk.gui.openapi.framework.model import ApiOmitted


@dataclass(kw_only=True, slots=True)
class RestrictEditions:
    """Validate that a field is only used in some versions.

    The fields description should contain this information as well, this must be done manually."""

    required_if_supported: bool = False
    supported_editions: InitVar[set[Edition] | None] = None
    excluded_editions: InitVar[set[Edition] | None] = None
    editions: set[Edition] = field(init=False)

    def __post_init__(
        self, supported_editions: set[Edition] | None, excluded_editions: set[Edition] | None
    ) -> None:
        if supported_editions and excluded_editions:
            raise ValueError("Cannot set supported and excluded editions")

        if supported_editions:
            self.editions = supported_editions
        elif excluded_editions:
            self.editions = {x for x in Edition.__members__.values() if x not in excluded_editions}
        else:
            raise ValueError("Must set either supported or excluded editions")

    def _validate_editions(self, value: object) -> object:
        if edition(paths.omd_root) in self.editions:
            if self.required_if_supported and isinstance(value, ApiOmitted):
                raise ValueError("Field is required in this edition")
        elif not isinstance(value, ApiOmitted):
            raise ValueError("Field is not supported by this edition")

        return value

    def __get_pydantic_core_schema__(
        self, source_type: CoreSchema, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            self._validate_editions, handler(source_type)
        )
